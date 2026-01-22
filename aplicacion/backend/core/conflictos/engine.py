from __future__ import annotations
from typing import List, Optional, Tuple, Set, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DbSession, joinedload

# Core imports
from core.conflictos.types import (
    SesionRef, RestriccionRef, ResultadoDeteccion, 
    TipoConflicto, SeveridadConflicto, ParametrosDeteccion, 
    SlotSemanal, Intervalo
)
from core.conflictos.basic_rules import detectar_todos_los_conflictos_basicos
from core.conflictos.hashing import generar_hash_conflicto
from database.models import Sesion, Restriccion

# Mapeo de días string a int (0=Lunes)
DIAS_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

class ConflictDetectionEngine:
    def __init__(self) -> None:
        self._initialized = True

    def detect_conflicts_for_session(
        self, sesion_id: int, db_session: DbSession, params: Optional[ParametrosDeteccion] = None
    ) -> List[ResultadoDeteccion]:
        if params is None: params = ParametrosDeteccion()
        
        # Cargar referencias. Nota: cargamos TODO para comparar. 
        # En Fase 4 optimizaremos con queries filtradas.
        sesiones_ref, restricciones_ref = self._db_to_refs(db_session)
        
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, params)
        
        # Filtrar solo los conflictos de la sesión solicitada
        return [r for r in resultados if sesion_id in (r.sesion_id, r.sesion_2_id)]

    def detect_conflicts_for_range(
        self, db_session: DbSession, params: Optional[ParametrosDeteccion] = None
    ) -> List[ResultadoDeteccion]:
        if params is None: params = ParametrosDeteccion()
        sesiones_ref, restricciones_ref = self._db_to_refs(db_session)
        return self._execute_detection(sesiones_ref, restricciones_ref, params)

    # --- Conversión y Adaptación ---

    def _db_to_refs(self, db_session: DbSession) -> Tuple[List[SesionRef], List[RestriccionRef]]:
        # Eager loading sugerido para produccion: .options(joinedload(Sesion.grupo_docente))
        db_sesiones = db_session.query(Sesion).options(
            joinedload(Sesion.grupo_docente),
            joinedload(Sesion.profesores),
            joinedload(Sesion.aula)
        ).all()
        db_restricciones = db_session.query(Restriccion).all()

        sesiones_ref = []
        for s in db_sesiones:
            try:
                if not s.grupo_docente:
                    continue 
                ref = self._db_sesion_to_ref(s)
                sesiones_ref.append(ref)
            except ValueError as e:
                # Loggear error y continuar para no detener el sistema por un dato corrupto
                print(f"Error parseando sesion {s.id}: {e}") 
                continue

        restricciones_ref = []
        for r in db_restricciones:
            try:
                ref = self._db_restriccion_to_ref(r)
                restricciones_ref.append(ref)
            except ValueError as e:
                print(f"Error parseando restriccion {r.id}: {e}")
                continue

        return sesiones_ref, restricciones_ref

    def _db_sesion_to_ref(self, db_sesion: Sesion) -> SesionRef:
        # 1. Normalizar Tipo Recurrencia
        tipo_raw = str(db_sesion.tipo_recurrencia).upper()
        # Manejo de variantes "semanal" o "TipoRecurrencia.SEMANAL"
        if "SEMANAL" in tipo_raw:
            tipo_rec = "SEMANAL"
        elif "FECHADA" in tipo_raw:
            tipo_rec = "FECHADA"
        else:
            raise ValueError(f"Recurrencia desconocida: {tipo_raw}")

        slot = None
        intervalo = None

        # 2. Construir Slot o Intervalo
        if tipo_rec == "SEMANAL":
            dia_str = str(db_sesion.dia_semana).lower().replace("diasemana.", "")
            dia_int = DIAS_MAP.get(dia_str)
            if dia_int is None:
                raise ValueError(f"Día inválido: {db_sesion.dia_semana}")
            
            slot = SlotSemanal(
                dia_semana=dia_int,
                hora_inicio=db_sesion.hora_inicio,
                hora_fin=db_sesion.hora_fin
            )
        else:
            if not db_sesion.inicio or not db_sesion.fin:
                raise ValueError("Sesión fechada sin inicio/fin")
            intervalo = Intervalo(inicio=db_sesion.inicio, fin=db_sesion.fin)

        # 3. Obtener IDs relacionados (Navegando relaciones)
        if not db_sesion.grupo_docente:
             raise ValueError("Sesión huérfana de grupo docente")
             
        asignatura_id = db_sesion.grupo_docente.asignatura_id
        grupo_id = db_sesion.grupo_docente.id
        
        profesor_ids = [p.id for p in db_sesion.profesores]

        return SesionRef(
            id=db_sesion.id,
            aula_id=db_sesion.aula_id, # Puede ser None
            profesor_ids=profesor_ids,
            asignatura_id=asignatura_id,
            grupo_id=grupo_id,
            tipo_recurrencia=tipo_rec,
            slot=slot,
            intervalo=intervalo
        )

    def _db_restriccion_to_ref(self, db_res: Restriccion) -> RestriccionRef:
        # Lógica similar para restricciones...
        ambito = "PROFESOR" if db_res.profesor_id else "AULA"
        
        slot = None
        intervalo = None
        
        # Detectar si es basada en slot (si tiene dia_semana)
        if db_res.dia_semana:
            dia_str = str(db_res.dia_semana).lower().replace("diasemana.", "")
            dia_int = DIAS_MAP.get(dia_str)
            if dia_int is not None and db_res.hora_inicio and db_res.hora_fin:
                slot = SlotSemanal(
                    dia_semana=dia_int,
                    hora_inicio=db_res.hora_inicio,
                    hora_fin=db_res.hora_fin
                )

        if db_res.inicio and db_res.fin:
            intervalo = Intervalo(inicio=db_res.inicio, fin=db_res.fin)

        # Dureza
        dureza_str = str(db_res.dureza).upper()
        es_blanda = "BLANDA" in dureza_str

        return RestriccionRef(
            id=db_res.id,
            ambito=ambito,
            profesor_id=db_res.profesor_id,
            aula_id=db_res.aula_id,
            slot=slot,
            intervalo=intervalo,
            es_blanda=es_blanda
        )

    # --- Ejecución ---

    def _execute_detection(
        self, sesiones: List[SesionRef], restricciones: List[RestriccionRef], params: ParametrosDeteccion
    ) -> List[ResultadoDeteccion]:
        
        # 1. Ejecutar reglas puras
        (sol_prof, sol_aula, sol_grupo, violaciones) = detectar_todos_los_conflictos_basicos(
            sesiones, restricciones
        )

        resultados = []

        # 2. Convertir primitivas a Objetos Resultado
        if params.incluir_solapamientos_profesor:
            for s1, s2, pid in sol_prof:
                resultados.append(self._create_result(
                    TipoConflicto.SOLAPAMIENTO_PROFESOR, s1, s2, 
                    descripcion=f"Profesor {pid} tiene solapamiento.",
                    profesor_id=pid
                ))

        if params.incluir_solapamientos_aula:
            for s1, s2, aid in sol_aula:
                resultados.append(self._create_result(
                    TipoConflicto.SOLAPAMIENTO_AULA, s1, s2,
                    descripcion=f"Aula {aid} tiene solapamiento.",
                    aula_id=aid
                ))
                
        if params.incluir_solapamientos_grupo:
            for s1, s2, asig_id in sol_grupo:
                 resultados.append(self._create_result(
                    TipoConflicto.SOLAPAMIENTO_AULA, s1, s2, # Reusamos tipo o creamos uno nuevo
                    descripcion=f"Asignatura {asig_id} tiene grupos solapados.",
                    asignatura_id=asig_id,
                    severidad=SeveridadConflicto.CRITICA
                ))

        if params.incluir_violaciones_restriccion:
            for sid, rid in violaciones:
                # Aquí necesitaríamos más info para description, por ahora genérico
                resultados.append(ResultadoDeteccion(
                    tipo=TipoConflicto.VIOLACION_RESTRICCION,
                    severidad=SeveridadConflicto.MEDIA,
                    sesion_id=sid,
                    restriccion_id=rid,
                    descripcion=f"Sesión {sid} viola restricción {rid}",
                    hash_deteccion=f"RSTR-{sid}-{rid}" # Hash temporal simple
                ))

        # 3. Hashing real y deduplicación
        for r in resultados:
            if not r.hash_deteccion or "temp" in r.hash_deteccion:
                r.hash_deteccion = generar_hash_conflicto(r)
        
        # TODO: Deduplicar aquí
        return resultados

    def _create_result(self, tipo, s1, s2, descripcion, severidad=SeveridadConflicto.ALTA, **kwargs):
        return ResultadoDeteccion(
            tipo=tipo,
            severidad=severidad,
            sesion_id=s1,
            sesion_2_id=s2,
            descripcion=descripcion,
            hash_deteccion="temp", # Se calculará después
            **kwargs
        )

# Instancia Global
conflict_engine = ConflictDetectionEngine()