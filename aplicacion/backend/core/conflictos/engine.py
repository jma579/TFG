"""
Motor principal de detección de conflictos académicos.

Este módulo orquesta todos los componentes del sistema de detección:
- Conversión de modelos SQLAlchemy a referencias core
- Ejecución de reglas de detección básicas
- Aplicación de hashing y deduplicación 
- Filtrado por parámetros de configuración
- Generación de ResultadoDeteccion completos

Arquitectura:
- Motor agnóstico: lógica core independiente de SQLAlchemy
- Interfaz estable: 3 métodos principales para cubrir casos de uso
- Conversión explícita: ORM → SesionRef/RestriccionRef → primitivas → ResultadoDeteccion
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Set
from datetime import datetime, timezone

from sqlalchemy.orm import Session

# Core imports
from backend.core.conflictos.types import (
    SesionRef,
    RestriccionRef,
    ResultadoDeteccion,
    TipoConflicto,
    SeveridadConflicto,
    ParametrosDeteccion,
    SlotSemanal,
    Intervalo,
)
from backend.core.conflictos.basic_rules import (
    detectar_todos_los_conflictos_basicos,
    SolapamientoProfesor,
    SolapamientoAula,
    ViolacionRestriccion,
)
from backend.core.conflictos.hashing import generar_hash_conflicto

# Modelos ORM reales
from database.models import Sesion, Restriccion


class ConflictDetectionEngine:
    """
    Motor principal de detección de conflictos académicos.

    Proporciona una interfaz estable y agnóstica para detectar conflictos,
    orquestando todos los componentes del sistema core.
    """

    def __init__(self) -> None:
        """Inicializa el motor de detección."""
        self._initialized = True

    # ========================================================================
    # INTERFAZ PÚBLICA (3 métodos principales)
    # ========================================================================

    def detect_conflicts_for_session(
        self,
        sesion_id: int,
        db_session: Session,
        params: Optional[ParametrosDeteccion] = None,
    ) -> List[ResultadoDeteccion]:
        """
        Detecta conflictos que involucran a una sesión específica.

        Args:
            sesion_id: ID de la sesión a analizar
            db_session: Sesión de SQLAlchemy activa
            params: Parámetros de configuración (opcional)

        Returns:
            Lista de conflictos que involucran la sesión especificada

        Raises:
            ValueError: Si la sesión no existe (en futuras versiones, si se valida aquí)
        """
        if params is None:
            params = ParametrosDeteccion()

        # 1. Cargar datos y convertir a referencias core
        sesiones_ref, restricciones_ref = self._db_to_refs(
            db_session,
            sesion_id=sesion_id,
        )

        # 2. Ejecutar detección completa
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, params)

        # 3. Filtrar solo conflictos que involucran la sesión específica
        # (En Fase 4 se puede optimizar cargando solo sesiones candidatas)
        resultados_filtrados = [
            r for r in resultados if sesion_id in (r.sesion_id, r.sesion_2_id)
        ]

        return resultados_filtrados

    def detect_conflicts_for_range(
        self,
        db_session: Session,
        params: Optional[ParametrosDeteccion] = None,
    ) -> List[ResultadoDeteccion]:
        """
        Detecta conflictos en un rango completo (toda la BD o filtrado por parámetros).

        Args:
            db_session: Sesión de SQLAlchemy activa
            params: Parámetros de configuración (opcional)

        Returns:
            Lista completa de conflictos detectados
        """
        if params is None:
            params = ParametrosDeteccion()

        # 1. Cargar todos los datos y convertir a referencias core
        sesiones_ref, restricciones_ref = self._db_to_refs(
            db_session, rango=params.rango_fechas
        )

        # 2. Ejecutar detección completa
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, params)

        return resultados

    def validate_session_constraints(
        self,
        sesion_data: dict,
        db_session: Session,
    ) -> List[ResultadoDeteccion]:
        """
        Valida que una sesión (nueva o modificada) no genere conflictos.

        Útil para validación previa antes de crear/actualizar sesiones.

        Args:
            sesion_data: Diccionario con datos de la sesión a validar
            db_session: Sesión de SQLAlchemy activa

        Returns:
            Lista de conflictos potenciales que generaría la sesión
        """
        # 1. Convertir sesion_data a SesionRef temporal
        sesion_temporal = self._dict_to_sesion_ref(sesion_data)

        # 2. Cargar datos existentes
        sesiones_ref, restricciones_ref = self._db_to_refs(db_session)

        # 3. Añadir sesión temporal para detección
        sesiones_con_temporal = sesiones_ref + [sesion_temporal]

        # 4. Ejecutar detección
        params = ParametrosDeteccion()  # Parámetros por defecto
        resultados = self._execute_detection(
            sesiones_con_temporal, restricciones_ref, params
        )

        # 5. Filtrar solo conflictos que involucran la sesión temporal
        sesion_temporal_id = sesion_temporal.id
        resultados_filtrados = [
            r
            for r in resultados
            if sesion_temporal_id in (r.sesion_id, r.sesion_2_id)
        ]

        return resultados_filtrados

    # ========================================================================
    # CONVERSIÓN DE DATOS (ORM ↔ Core)
    # ========================================================================

    def _db_to_refs(
        self,
        db_session: Session,
        *,
        sesion_id: Optional[int] = None,
        rango: Optional[Tuple[datetime, datetime]] = None,
    ) -> Tuple[List[SesionRef], List[RestriccionRef]]:
        """
        Convierte modelos SQLAlchemy a referencias core.

        Args:
            db_session: Sesión de SQLAlchemy activa
            sesion_id: Si especificado, se usa para filtrar resultados al final
            rango: Si especificado, podría usarse para filtrar por rango de fechas
                   (no aplicado en Fase 3; la detección se hace sobre todas las sesiones)

        Returns:
            Tupla (sesiones_ref, restricciones_ref)
        """
        sesiones_ref = self._load_sesiones_ref(db_session, sesion_id, rango)
        restricciones_ref = self._load_restricciones_ref(db_session, rango)

        return sesiones_ref, restricciones_ref

    def _load_sesiones_ref(
        self,
        db_session: Session,
        sesion_id: Optional[int],
        rango: Optional[Tuple[datetime, datetime]],
    ) -> List[SesionRef]:
        """
        Carga sesiones de la BD y las convierte a SesionRef.

        Estrategia Fase 3:
        - Cargar todas las sesiones de la BD
        - Convertir cada una a SesionRef
        - La selección de qué sesiones participan en qué conflictos se deja a basic_rules

        En futuras fases se puede optimizar para cargar solo sesiones candidatas
        (mismo profesor, misma aula, mismo día, rango de fechas, etc.).
        """
        # Por simplicidad (y dado el tamaño de datos actual), cargamos todas las sesiones.
        db_sesiones: List[Sesion] = db_session.query(Sesion).all()

        refs: List[SesionRef] = []
        for ses in db_sesiones:
            try:
                ref = self._db_sesion_to_ref(ses)
                refs.append(ref)
            except Exception as exc:
                # Si una sesión no está bien formada, la omitimos
                # (en producción se debería usar logging en lugar de print)
                print(f"[conflict_engine] Sesión {getattr(ses, 'id', '?')} inválida: {exc}")
                continue

        return refs

    def _load_restricciones_ref(
        self,
        db_session: Session,
        rango: Optional[Tuple[datetime, datetime]],
    ) -> List[RestriccionRef]:
        """
        Carga restricciones de la BD y las convierte a RestriccionRef.

        Estrategia Fase 3:
        - Cargar todas las restricciones
        - Convertirlas a RestriccionRef
        - Dejar a basic_rules decidir qué restricciones aplican a qué sesiones

        Si aún no tienes lógica de restricciones en basic_rules,
        el motor simplemente ignorará esta lista (no romperá nada).
        """
        db_restricciones: List[Restriccion] = db_session.query(Restriccion).all()

        refs: List[RestriccionRef] = []
        for rest in db_restricciones:
            try:
                ref = self._db_restriccion_to_ref(rest)
                refs.append(ref)
            except Exception as exc:
                print(
                    f"[conflict_engine] Restricción {getattr(rest, 'id', '?')} inválida: {exc}"
                )
                continue

        return refs

    def _db_sesion_to_ref(self, db_sesion: Sesion) -> SesionRef:
        """
        Convierte modelo SQLAlchemy Sesion a SesionRef.

        Mapea:
        - id          → SesionRef.id
        - aula_id     → SesionRef.aula_id
        - profesores  → SesionRef.profesor_ids
        - tipo_recurrencia, dia_semana/hora_* o inicio/fin → slot / intervalo
        """
        # Extraer profesores asociados
        profesor_ids = [prof.id for prof in db_sesion.profesores] if db_sesion.profesores else []

        # Determinar tipo de recurrencia como string Literal["SEMANAL", "FECHADA"]
        # Usamos .name para garantizar los literales esperados, independientemente del .value
        tipo_recurrencia = db_sesion.tipo_recurrencia.name  # "SEMANAL" | "FECHADA"

        slot: Optional[SlotSemanal] = None
        intervalo: Optional[Intervalo] = None

        if tipo_recurrencia == "SEMANAL":
            if (
                db_sesion.dia_semana is None
                or db_sesion.hora_inicio is None
                or db_sesion.hora_fin is None
            ):
                raise ValueError(
                    f"Sesión {db_sesion.id} es SEMANAL pero faltan dia_semana/hora_inicio/hora_fin"
                )

            slot = SlotSemanal(
                dia_semana=db_sesion.dia_semana.value,  # DiaSemana enum → int 0..6
                hora_inicio=db_sesion.hora_inicio,
                hora_fin=db_sesion.hora_fin,
            )

        elif tipo_recurrencia == "FECHADA":
            if db_sesion.inicio is None or db_sesion.fin is None:
                raise ValueError(
                    f"Sesión {db_sesion.id} es FECHADA pero faltan inicio/fin"
                )

            intervalo = Intervalo(
                inicio=db_sesion.inicio,
                fin=db_sesion.fin,
            )
        else:
            raise ValueError(
                f"Tipo de recurrencia no soportado en Sesion {db_sesion.id}: {tipo_recurrencia}"
            )

        return SesionRef(
            id=db_sesion.id,
            aula_id=db_sesion.aula_id,
            profesor_ids=profesor_ids,
            tipo_recurrencia=tipo_recurrencia,
            slot=slot,
            intervalo=intervalo,
        )

    def _db_restriccion_to_ref(self, db_restriccion: Restriccion) -> RestriccionRef:
        """
        Convierte modelo SQLAlchemy Restriccion a RestriccionRef.

        Mapea:
        - id
        - ámbito: PROFESOR o AULA (según profesor_id / aula_id)
        - slot / intervalo según tenga ventana semanal o fechada
        - dureza → es_blanda
        """
        # Determinar ámbito
        profesor_id = db_restriccion.profesor_id
        aula_id = db_restriccion.aula_id

        if profesor_id is not None and aula_id is not None:
            raise ValueError(
                f"Restricción {db_restriccion.id} tiene profesor_id y aula_id simultáneamente"
            )
        if profesor_id is None and aula_id is None:
            raise ValueError(
                f"Restricción {db_restriccion.id} no tiene ni profesor_id ni aula_id"
            )

        if profesor_id is not None:
            ambito = "PROFESOR"
        else:
            ambito = "AULA"

        # Slot / intervalo
        slot: Optional[SlotSemanal] = None
        intervalo: Optional[Intervalo] = None

        if (
            db_restriccion.dia_semana is not None
            and db_restriccion.hora_inicio is not None
            and db_restriccion.hora_fin is not None
        ):
            slot = SlotSemanal(
                dia_semana=db_restriccion.dia_semana.value,
                hora_inicio=db_restriccion.hora_inicio,
                hora_fin=db_restriccion.hora_fin,
            )

        if db_restriccion.inicio is not None and db_restriccion.fin is not None:
            intervalo = Intervalo(
                inicio=db_restriccion.inicio,
                fin=db_restriccion.fin,
            )

        # Dureza → es_blanda (BLANDA vs DURA, etc.)
        dureza_name = getattr(db_restriccion.dureza, "name", "").upper()
        es_blanda = dureza_name == "BLANDA"

        return RestriccionRef(
            id=db_restriccion.id,
            ambito=ambito,
            profesor_id=profesor_id,
            aula_id=aula_id,
            slot=slot,
            intervalo=intervalo,
            es_blanda=es_blanda,
        )

    def _dict_to_sesion_ref(self, sesion_data: dict) -> SesionRef:
        """
        Convierte diccionario de datos a SesionRef temporal.

        Para uso en validate_session_constraints().

        Nota: implementación mínima. Se asume que el dict viene ya validado
        por la capa de schemas (FastAPI/Pydantic).
        """
        tipo_recurrencia = sesion_data["tipo_recurrencia"]

        slot: Optional[SlotSemanal] = None
        intervalo: Optional[Intervalo] = None

        if tipo_recurrencia == "SEMANAL":
            slot = SlotSemanal(
                dia_semana=sesion_data["dia_semana"],
                hora_inicio=sesion_data["hora_inicio"],
                hora_fin=sesion_data["hora_fin"],
            )
        elif tipo_recurrencia == "FECHADA":
            intervalo = Intervalo(
                inicio=sesion_data["inicio"],
                fin=sesion_data["fin"],
            )
        else:
            raise ValueError(
                f"tipo_recurrencia no soportado en sesion_data: {tipo_recurrencia}"
            )

        return SesionRef(
            id=sesion_data["id"],
            aula_id=sesion_data["aula_id"],
            profesor_ids=sesion_data.get("profesor_ids", []),
            tipo_recurrencia=tipo_recurrencia,
            slot=slot,
            intervalo=intervalo,
        )

    # ========================================================================
    # EJECUCIÓN DE DETECCIÓN (Core Logic)
    # ========================================================================

    def _execute_detection(
        self,
        sesiones_ref: List[SesionRef],
        restricciones_ref: List[RestriccionRef],
        params: ParametrosDeteccion,
    ) -> List[ResultadoDeteccion]:
        """
        Ejecuta detección completa y produce ResultadoDeteccion.

        Este es el núcleo agnóstico que orquesta:
        1. Detección con basic_rules
        2. Conversión de primitivas a ResultadoDeteccion
        3. Aplicación de hashing y deduplicación
        4. Filtrado por parámetros

        Args:
            sesiones_ref: Sesiones convertidas a referencias core
            restricciones_ref: Restricciones convertidas a referencias core
            params: Parámetros de configuración

        Returns:
            Lista de ResultadoDeteccion completos y deduplicados
        """
        # 1. Ejecutar detección con basic_rules
        solapamientos_prof, solapamientos_aula, violaciones = (
            detectar_todos_los_conflictos_basicos(sesiones_ref, restricciones_ref)
        )

        # 2. Convertir primitivas a ResultadoDeteccion (sin hash aún)
        resultados = self._primitives_to_results(
            solapamientos_prof,
            solapamientos_aula,
            violaciones,
            params,
        )

        # 3. Aplicar hashing centralizado
        resultados_con_hash = self._apply_hashing(resultados)

        # 4. Deduplicar por hash
        resultados_deduplicados = self._deduplicate_by_hash(resultados_con_hash)

        # 5. Aplicar filtros finales
        resultados_filtrados = self._apply_filters(resultados_deduplicados, params)

        return resultados_filtrados

    def _primitives_to_results(
        self,
        solapamientos_prof: List[SolapamientoProfesor],
        solapamientos_aula: List[SolapamientoAula],
        violaciones: List[ViolacionRestriccion],
        params: ParametrosDeteccion,
    ) -> List[ResultadoDeteccion]:
        """
        Convierte primitivas de basic_rules a ResultadoDeteccion completos.

        Inyecta severidad y descripción baseline por tipo de conflicto.
        """
        resultados: List[ResultadoDeteccion] = []

        # Convertir solapamientos de profesor
        if params.incluir_solapamientos_profesor:
            for sesion_id1, sesion_id2, profesor_id in solapamientos_prof:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.SOLAPAMIENTO_PROFESOR,
                    # TODO Fase 4: Ajustar severidad según contexto (duración solape, tipo sesión, etc.)
                    severidad=SeveridadConflicto.ALTA,  # Baseline severity v1
                    descripcion=(
                        f"Profesor {profesor_id} tiene sesiones simultáneas "
                        f"(sesiones {sesion_id1}, {sesion_id2})"
                    ),
                    sesion_id=sesion_id1,
                    sesion_2_id=sesion_id2,
                    profesor_id=profesor_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "solapamiento_profesor",
                    },
                )
                resultados.append(resultado)

        # Convertir solapamientos de aula
        if params.incluir_solapamientos_aula:
            for sesion_id1, sesion_id2, aula_id in solapamientos_aula:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.SOLAPAMIENTO_AULA,
                    # TODO Fase 4: Severidad según capacidad aula, tipo sesión, etc.
                    severidad=SeveridadConflicto.CRITICA,  # Baseline: aulas más críticas que profesores
                    descripcion=(
                        f"Aula {aula_id} tiene sesiones simultáneas "
                        f"(sesiones {sesion_id1}, {sesion_id2})"
                    ),
                    sesion_id=sesion_id1,
                    sesion_2_id=sesion_id2,
                    aula_id=aula_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "solapamiento_aula",
                    },
                )
                resultados.append(resultado)

        # Convertir violaciones de restricción
        if params.incluir_violaciones_restriccion:
            for sesion_id, restriccion_id in violaciones:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.VIOLACION_RESTRICCION,
                    # TODO Fase 4: Severidad según obligatoriedad restricción (dura vs blanda)
                    severidad=SeveridadConflicto.MEDIA,  # Baseline v1
                    descripcion=(
                        f"Sesión {sesion_id} viola restricción {restriccion_id}"
                    ),
                    sesion_id=sesion_id,
                    restriccion_id=restriccion_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "violacion_restriccion",
                    },
                )
                resultados.append(resultado)

        return resultados

    def _apply_hashing(
        self,
        resultados: List[ResultadoDeteccion],
    ) -> List[ResultadoDeteccion]:
        """
        Aplica hashing centralizado a todos los ResultadoDeteccion.

        Punto único para generación de hashes, usando hashing.py.
        """
        resultados_con_hash: List[ResultadoDeteccion] = []
        for r in resultados:
            h = generar_hash_conflicto(r)  # recibe ResultadoDeteccion completo
            r2 = r.model_copy(update={"hash_deteccion": h})
            resultados_con_hash.append(r2)
        return resultados_con_hash

    def _deduplicate_by_hash(
        self,
        resultados: List[ResultadoDeteccion],
    ) -> List[ResultadoDeteccion]:
        """
        Deduplicar ResultadoDeteccion por hash_deteccion.

        Garantiza que no hay conflictos duplicados en el resultado final.
        """
        seen_hashes: Set[str] = set()
        resultados_deduplicados: List[ResultadoDeteccion] = []

        for resultado in resultados:
            if resultado.hash_deteccion not in seen_hashes:
                seen_hashes.add(resultado.hash_deteccion)
                resultados_deduplicados.append(resultado)

        return resultados_deduplicados

    def _apply_filters(
        self,
        resultados: List[ResultadoDeteccion],
        params: ParametrosDeteccion,
    ) -> List[ResultadoDeteccion]:
        """
        Aplica filtros finales según ParametrosDeteccion.

        Por ahora:
        - Filtra por severidad mínima
        - (Futuro) podría filtrar por rango de fechas usando datos_contexto
        """
        resultados_filtrados = resultados

        # Filtro por severidad mínima
        severidades_orden = {
            SeveridadConflicto.BAJA: 1,
            SeveridadConflicto.MEDIA: 2,
            SeveridadConflicto.ALTA: 3,
            SeveridadConflicto.CRITICA: 4,
        }

        severidad_minima_valor = severidades_orden[params.severidad_minima]
        resultados_filtrados = [
            r
            for r in resultados_filtrados
            if severidades_orden[r.severidad] >= severidad_minima_valor
        ]

        # TODO Fase 4: Filtro por rango de fechas usando datos_contexto si se modela ahí
        # if params.rango_fechas:
        #     inicio_filtro, fin_filtro = params.rango_fechas
        #     resultados_filtrados = [
        #         r for r in resultados_filtrados
        #         if self._resultado_en_rango(r, inicio_filtro, fin_filtro)
        #     ]

        return resultados_filtrados


# ========================================================================
# INSTANCIA GLOBAL DEL MOTOR
# ========================================================================

# Instancia singleton para uso en toda la aplicación
conflict_engine = ConflictDetectionEngine()
