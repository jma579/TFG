"""
Motor de Orquestación de Conflictos.
Versión Mejorada: Mensajes human-readable (Nombres en lugar de IDs).
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session as DbSession, joinedload

# --- Core Imports ---
from core.conflictos.types import (
    SesionRef, 
    ResultadoDeteccion, 
    SlotSemanal, 
    Intervalo
)
from core.conflictos.basic_rules import detectar_todos_los_conflictos_basicos
from core.conflictos.hashing import generar_hash_conflicto

# --- Database & Constants ---
from database.models import Sesion, GrupoDocente, Asignatura, Profesor
from constants.enums import (
    TipoConflicto, 
    SeveridadConflicto, 
    HORA_APERTURA_CENTRO, 
    HORA_CIERRE_CENTRO, 
    HORAS_CONCILIACION_NORMAL, 
    HORAS_CONCILIACION_MIXTA
)

DIAS_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

class ConflictDetectionEngine:

    def __init__(self) -> None:
        self._initialized = True

    # -------------------------------------------------------------------------
    # API PÚBLICA
    # -------------------------------------------------------------------------

    def detect_conflicts_for_session(
        self, sesion_id: int, db: DbSession
    ) -> List[ResultadoDeteccion]:
        # Desempaquetamos los 4 elementos devueltos
        sesiones_ref, mapa_conciliacion, lookups = self._db_to_refs(db)
        
        resultados = self._execute_detection(sesiones_ref, mapa_conciliacion, lookups)
        
        return [r for r in resultados if sesion_id in (r.sesion_id, r.sesion_2_id or -1)]

    def detect_conflicts_for_range(self, db: DbSession) -> List[ResultadoDeteccion]:
        sesiones_ref, mapa_conciliacion, lookups = self._db_to_refs(db)
        return self._execute_detection(sesiones_ref, mapa_conciliacion, lookups)

    # -------------------------------------------------------------------------
    # CAPA DE DATOS (Data Fetching)
    # -------------------------------------------------------------------------

    def _db_to_refs(self, db: DbSession) -> Tuple[List[SesionRef], Dict[int, str], Dict[str, Dict[int, str]]]:
        """
        Carga datos y crea mapas de nombres para enriquecer los mensajes.
        """
        db_sesiones = db.query(Sesion).options(
            joinedload(Sesion.profesores),
            joinedload(Sesion.aula),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.asignatura_menciones)
        ).all()
        
        db_profes_conciliacion = db.query(Profesor).filter(
            Profesor.conciliacion.isnot(None)
        ).all()

        sesiones_ref = []
        
        # --- NUEVO: Diccionarios de Búsqueda (Lookups) ---
        # Usamos esto para evitar consultas N+1 al generar los mensajes
        nombres_profesors = {}
        nombres_aulas = {}
        nombres_asignaturas = {}

        for s in db_sesiones:
            try:
                # 1. Convertir a Ref
                sesiones_ref.append(self._convert_sesion(s))
                
                # 2. Rellenar Lookups (Caché de nombres)
                if s.aula:
                    nombres_aulas[s.aula.id] = f"{s.aula.nombre} ({s.aula.codigo})"
                
                for p in s.profesores:
                    # Guardamos "Nombre Apellido"
                    nombres_profesors[p.id] = f"{p.nombre} {p.apellidos}"

                if s.grupo_docente and s.grupo_docente.asignatura:
                    nombres_asignaturas[s.grupo_docente.asignatura.id] = s.grupo_docente.asignatura.nombre

            except ValueError:
                continue 

        # Mapa de conciliación (lógica)
        mapa_conciliacion = {
            p.id: p.conciliacion.value 
            for p in db_profes_conciliacion
        }
        
        # Aseguramos tener los nombres de los profes con conciliación aunque no tengan sesión
        for p in db_profes_conciliacion:
            nombres_profesors[p.id] = f"{p.nombre} {p.apellidos}"

        # Empaquetamos todo en un objeto de contexto
        lookups = {
            "profesores": nombres_profesors,
            "aulas": nombres_aulas,
            "asignaturas": nombres_asignaturas
        }

        return sesiones_ref, mapa_conciliacion, lookups

    def _convert_sesion(self, s: Sesion) -> SesionRef:
        # ... (Este método se mantiene IDÉNTICO al anterior) ...
        if not s.grupo_docente:
            raise ValueError(f"Sesión {s.id} sin grupo docente.")

        slot = None
        if s.dia_semana:
            dia_str = str(s.dia_semana).lower().split('.')[-1]
            dia_int = DIAS_MAP.get(dia_str)
            if dia_int is not None and s.hora_inicio and s.hora_fin:
                slot = SlotSemanal(
                    dia_semana=dia_int, 
                    hora_inicio=s.hora_inicio, 
                    hora_fin=s.hora_fin
                )
        
        intervalo = None
        if s.inicio and s.fin:
            intervalo = Intervalo(inicio=s.inicio, fin=s.fin)

        mencion_ids = [
            am.mencion_id 
            for am in s.grupo_docente.asignatura.asignatura_menciones
        ]

        return SesionRef(
            id=s.id,
            aula_id=s.aula_id,
            profesor_ids=[p.id for p in s.profesores],
            asignatura_id=s.grupo_docente.asignatura_id,
            grupo_id=s.grupo_docente.id,
            curso=s.grupo_docente.curso or 0,
            tipo_grupo=str(s.grupo_docente.tipo).upper() if s.grupo_docente.tipo else "TEORIA",
            grupo_codigo=str(s.grupo_docente.codigo).upper() if s.grupo_docente.codigo else "UNICO",
            mencion_ids=mencion_ids,
            tipo_recurrencia="SEMANAL" if slot else "FECHADA",
            slot=slot,
            intervalo=intervalo
        )

    # -------------------------------------------------------------------------
    # LÓGICA DE NEGOCIO (Ejecución)
    # -------------------------------------------------------------------------

    def _execute_detection(
        self, 
        sesiones: List[SesionRef], 
        mapa_conciliacion: Dict[int, str],
        lookups: Dict[str, Dict[int, str]] # <--- Recibimos los nombres
    ) -> List[ResultadoDeteccion]:
        
        resultados = []
        
        # Helpers para obtener nombres con fallback a ID si no existe
        def get_aula(id): return lookups["aulas"].get(id, f"Aula {id}")
        def get_profe(id): return lookups["profesores"].get(id, f"Docente {id}")
        def get_asig(id): return lookups["asignaturas"].get(id, f"Asignatura {id}")

        # 1. Llamada al Núcleo Matemático
        (sol_aula, sol_prof, sol_grupo, sol_conciliacion) = detectar_todos_los_conflictos_basicos(
            sesiones,
            mapa_conciliacion,
            HORA_APERTURA_CENTRO,
            HORA_CIERRE_CENTRO,
            HORAS_CONCILIACION_NORMAL,
            HORAS_CONCILIACION_MIXTA
        )

        # --- A. SOLAPAMIENTO DE AULAS ---
        for s1, s2, aid in sol_aula:
            nombre_aula = get_aula(aid)
            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_AULA,
                severidad=SeveridadConflicto.CRITICO,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                aula_id=aid,
                # NUEVO MENSAJE
                descripcion=f"El aula '{nombre_aula}' está ocupada simultáneamente por dos sesiones.",
                hash_deteccion="temp"
            ))

        # --- B. SOLAPAMIENTO DE PROFESORES ---
        for s1, s2, pid in sol_prof:
            nombre_profe = get_profe(pid)
            
            n_p1 = len(s1.profesor_ids)
            n_p2 = len(s2.profesor_ids)
            es_bloqueante = (n_p1 == 1 and n_p2 == 1)
            
            if es_bloqueante:
                sev = SeveridadConflicto.CRITICO
                # NUEVO MENSAJE
                desc = f"{nombre_profe} tiene dos clases a la vez y es el único docente asignado."
            else:
                sev = SeveridadConflicto.NO_BLOQUEANTE
                # NUEVO MENSAJE
                desc = f"{nombre_profe} tiene solapamiento horario, pero cuenta con apoyo de otros docentes."

            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_PROFESOR,
                severidad=sev,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                profesor_id=pid,
                descripcion=desc,
                hash_deteccion="temp"
            ))

        # --- C. SOLAPAMIENTO DE GRUPOS ---
        for s1, s2, asig_comun, motivo in sol_grupo:
            # Si hay asignatura común, mostramos su nombre
            if asig_comun:
                nombre_asig = get_asig(asig_comun)
                prefijo = f"Asignatura {nombre_asig}: "
            else:
                prefijo = "Plan de Estudios: "

            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_GRUPO,
                severidad=SeveridadConflicto.CRITICO,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                asignatura_id=s1.asignatura_id,
                # NUEVO MENSAJE
                descripcion=f"{prefijo}{motivo}",
                hash_deteccion="temp"
            ))

        # --- D. INTERFERENCIA CONCILIACIÓN ---
        for sesion, pid, motivo in sol_conciliacion:
            nombre_profe = get_profe(pid)
            
            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.INTERFERENCIA_CONCILIACION,
                severidad=SeveridadConflicto.NO_BLOQUEANTE,
                sesion_id=sesion.id,
                profesor_id=pid,
                # NUEVO MENSAJE: Incluye el nombre del profesor
                descripcion=f"{nombre_profe}: {motivo}",
                hash_deteccion="temp",
                datos_contexto={"tipo_conciliacion": mapa_conciliacion.get(pid)}
            ))

        # 2. Deduplicación y Hashing
        unique_results = {}
        for r in resultados:
            r.hash_deteccion = generar_hash_conflicto(r)
            if r.hash_deteccion not in unique_results:
                unique_results[r.hash_deteccion] = r
                
        return list(unique_results.values())

# Instancia Singleton
conflict_engine = ConflictDetectionEngine()