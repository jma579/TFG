"""
Motor de Orquestación de Conflictos.
"""

from typing import List, Tuple, Dict
from sqlalchemy.orm import Session as DbSession, joinedload

from core.conflictos.types import SesionRef, RestriccionRef, ResultadoDeteccion, SlotSemanal, Intervalo
from core.conflictos.basic_rules import detectar_todos_los_conflictos_basicos
from core.conflictos.hashing import generar_hash_conflicto

from database.models import Sesion, GrupoDocente, Asignatura, ProgramaAsignatura, ProfesorAsignatura, Restriccion
from constants.enums import TipoConflicto, SeveridadConflicto

DIAS_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}


class ConflictDetectionEngine:

    def __init__(self) -> None:
        self._initialized = True

    def detect_conflicts_for_session(
        self, sesion_id: int, db: DbSession
    ) -> List[ResultadoDeteccion]:
        """Detecta conflictos para una sesión específica."""
        sesiones_ref, restricciones_ref, lookups = self._db_to_refs(db) 
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, lookups)
        return [r for r in resultados if sesion_id in (r.sesion_id, r.sesion_2_id or -1)]

    def detect_conflicts_for_range(self, db: DbSession) -> List[ResultadoDeteccion]:
        """Detecta conflictos para todas las sesiones."""
        sesiones_ref, restricciones_ref, lookups = self._db_to_refs(db) 
        return self._execute_detection(sesiones_ref, restricciones_ref, lookups)

    def _db_to_refs(self, db: DbSession) -> Tuple[List[SesionRef], List[RestriccionRef], Dict[str, Dict]]:
        """Extrae datos de la base de datos y los convierte a referencias."""
        db_sesiones = db.query(Sesion).options(
            joinedload(Sesion.profesores),
            joinedload(Sesion.aula),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.programa_asignaturas)
                .joinedload(ProgramaAsignatura.mencion),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.programa_asignaturas)
                .joinedload(ProgramaAsignatura.programa),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.profesores_asignaturas)
                .joinedload(ProfesorAsignatura.profesor)
        ).all()
        
        sesiones_ref = []
        nombres_profesors = {}
        nombres_aulas = {}
        nombres_asignaturas = {}
        info_academica = {}

        for s in db_sesiones:
            try:
                sesiones_ref.append(self._convert_sesion(s))
                
                if s.aula:
                    nombres_aulas[s.aula.id] = s.aula.nombre
                
                for p in s.profesores:
                    nombres_profesors[p.id] = f"{p.nombre} {p.apellidos}"

                if s.grupo_docente and s.grupo_docente.asignatura:
                    asig = s.grupo_docente.asignatura
                    nombres_asignaturas[asig.id] = asig.nombre
                    
                    for pa in asig.profesores_asignaturas:
                        if pa.profesor:
                            nombres_profesors[pa.profesor.id] = f"{pa.profesor.nombre} {pa.profesor.apellidos}"
                    
                    grado = "Plan de Estudios"
                    mencion = ""
                    
                    if asig.programa_asignaturas:
                        pa_context = asig.programa_asignaturas[0]
                        grado = pa_context.programa.nombre if pa_context.programa else grado
                        if pa_context.mencion:
                            mencion = pa_context.mencion.nombre
                    
                    periodo = asig.periodo.value if asig.periodo else ""
                    periodo = periodo.replace("_", " ").title()
                    
                    info_academica[asig.id] = {
                        "grado": grado,
                        "periodo": periodo,
                        "mencion": mencion
                    }
            except ValueError:
                continue

        restricciones_ref = []
        db_restricciones = db.query(Restriccion).all()
        for r in db_restricciones:
            if r.dia_semana is not None and r.hora_inicio and r.hora_fin:
                dia_str = str(r.dia_semana).lower().split('.')[-1]
                dia_int = DIAS_MAP.get(dia_str)
                if dia_int is not None:
                    slot = SlotSemanal(
                        dia_semana=dia_int, 
                        hora_inicio=r.hora_inicio, 
                        hora_fin=r.hora_fin
                    )
                    restricciones_ref.append(RestriccionRef(
                        id=r.id,
                        profesor_id=r.profesor_id,
                        slot=slot
                    ))

        lookups = {
            "profesores": nombres_profesors,
            "aulas": nombres_aulas,
            "asignaturas": nombres_asignaturas,
            "info_academica": info_academica
        }

        return sesiones_ref, restricciones_ref, lookups

    def _convert_sesion(self, s: Sesion) -> SesionRef:
        """Convierte una sesión de SQLAlchemy a SesionRef."""
        if not s.grupo_docente:
            raise ValueError(f"Sesión {s.id} sin grupo.")
        
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

        pa_context = (s.grupo_docente.asignatura.programa_asignaturas[0] 
                     if s.grupo_docente.asignatura.programa_asignaturas else None)
        
        grado = pa_context.programa.nombre if (pa_context and pa_context.programa) else "Grado"
        mencion = pa_context.mencion.nombre if (pa_context and pa_context.mencion) else None
        periodo_txt = (s.grupo_docente.asignatura.periodo.value.replace("_", " ").title() 
                      if s.grupo_docente.asignatura.periodo else "")

        p_ids = [p.id for p in s.profesores]
        
        if not p_ids and s.grupo_docente and s.grupo_docente.asignatura:
            p_ids = [pa.profesor_id for pa in s.grupo_docente.asignatura.profesores_asignaturas]

        return SesionRef(
            id=s.id,
            aula_id=s.aula_id,
            profesor_ids=p_ids,
            asignatura_id=s.grupo_docente.asignatura_id,
            grupo_id=s.grupo_docente.id,
            curso=s.grupo_docente.curso or 0,
            periodo=str(s.grupo_docente.asignatura.periodo.value) if s.grupo_docente.asignatura.periodo else "",
            tipo_grupo=str(s.grupo_docente.tipo).upper(),
            grupo_codigo=str(s.grupo_docente.codigo).upper(),
            mencion_ids=[pa_context.mencion_id] if (pa_context and pa_context.mencion_id) else [],
            grado_nombre=grado,
            mencion_nombre=mencion,
            periodo_nombre=periodo_txt,
            tipo_recurrencia="SEMANAL" if slot else "FECHADA",
            slot=slot,
            intervalo=intervalo
        )

    def _execute_detection(
        self, 
        sesiones: List[SesionRef], 
        restricciones: List[RestriccionRef],
        lookups: Dict
    ) -> List[ResultadoDeteccion]:
        """Ejecuta la detección y construye los resultados."""
        resultados = []
        get_aula = lambda id: lookups["aulas"].get(id, f"Aula {id}")
        get_profe = lambda id: lookups["profesores"].get(id, f"Docente {id}")

        (sol_aula, sol_prof, sol_grupo, sol_restriccion) = detectar_todos_los_conflictos_basicos(sesiones, restricciones)

        for s1, s2, aid in sol_aula:
            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_AULA,
                severidad=SeveridadConflicto.CRITICO,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                aula_id=aid,
                descripcion=f"El aula '{get_aula(aid)}' está ocupada simultáneamente.",
                hash_deteccion="temp"
            ))

        for s1, s2, pid in sol_prof:
            es_bloqueante = (len(s1.profesor_ids) == 1 and len(s2.profesor_ids) == 1)
            desc = (f"{get_profe(pid)} tiene dos clases a la vez (único docente)." 
                   if es_bloqueante 
                   else f"{get_profe(pid)} tiene solapamiento (con apoyo).")
            
            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_PROFESOR,
                severidad=SeveridadConflicto.CRITICO if es_bloqueante else SeveridadConflicto.NO_BLOQUEANTE,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                profesor_id=pid,
                descripcion=desc,
                hash_deteccion="temp"
            ))

        for s1, s2, asig_comun, motivo in sol_grupo:
            if asig_comun:
                desc = f"Asignatura '{lookups['asignaturas'].get(asig_comun)}': {motivo}"
            else:
                mencion_txt = f" ({s1.mencion_nombre})" if s1.mencion_nombre else ""
                desc = f"Solape en {s1.grado_nombre}: Curso {s1.curso}º, {s1.periodo_nombre}{mencion_txt}"

            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.SOLAPAMIENTO_GRUPO,
                severidad=SeveridadConflicto.CRITICO,
                sesion_id=s1.id,
                sesion_2_id=s2.id,
                asignatura_id=s1.asignatura_id,
                descripcion=desc,
                hash_deteccion="temp"
            ))

        for s1, rest, pid in sol_restriccion:
            h_ini = rest.slot.hora_inicio.strftime("%H:%M")
            h_fin = rest.slot.hora_fin.strftime("%H:%M")
            desc = f"Restricción de {get_profe(pid)}: No disponible de {h_ini} a {h_fin}."

            resultados.append(ResultadoDeteccion(
                tipo=TipoConflicto.INCUMPLIMIENTO_RESTRICCION,
                severidad=SeveridadConflicto.NO_BLOQUEANTE,
                sesion_id=s1.id,
                sesion_2_id=None,
                profesor_id=pid,
                restriccion_id=rest.id,
                descripcion=desc,
                hash_deteccion="temp"
            ))

        unique = {}
        for r in resultados:
            r.hash_deteccion = generar_hash_conflicto(r)
            if r.hash_deteccion not in unique:
                unique[r.hash_deteccion] = r
        
        return list(unique.values())

conflict_engine = ConflictDetectionEngine()