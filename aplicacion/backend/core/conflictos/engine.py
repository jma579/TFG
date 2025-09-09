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
from .types import (
    SesionRef, RestriccionRef, ResultadoDeteccion,
    TipoConflicto, SeveridadConflicto, ParametrosDeteccion
)
from .basic_rules import (
    detectar_todos_los_conflictos_basicos,
    SolapamientoProfesor, SolapamientoAula, ViolacionRestriccion
)
from .hashing import generar_hash_conflicto

#TODO: Database imports -> ajustar según estructura real de modelos
# from ...db.models import Sesion as DBSesion, Restriccion as DBRestriccion


class ConflictDetectionEngine:
    """
    Motor principal de detección de conflictos académicos.
    
    Proporciona una interfaz estable y agnóstica para detectar conflictos,
    orquestando todos los componentes del sistema core.
    """
    
    def __init__(self):
        """Inicializa el motor de detección."""
        self._initialized = True
    
    # ========================================================================
    # INTERFAZ PÚBLICA (3 métodos principales)
    # ========================================================================
    
    def detect_conflicts_for_session(
        self, 
        sesion_id: int, 
        db_session: Session, 
        params: Optional[ParametrosDeteccion] = None
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
            ValueError: Si la sesión no existe
        """
        if params is None:
            params = ParametrosDeteccion()
        
        # 1. Cargar datos y convertir a referencias core
        sesiones_ref, restricciones_ref = self._db_to_refs(
            db_session, 
            sesion_id=sesion_id
        )
        
        # 2. Ejecutar detección completa
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, params)
        
        # 3. Filtrar solo conflictos que involucran la sesión específica
        # TODO Fase 4 (rendimiento): cargar solo sesiones candidatas en lugar de filtrar post-detección
        resultados_filtrados = [
            r for r in resultados 
            if sesion_id in [r.sesion_id, r.sesion_2_id]
        ]
        
        return resultados_filtrados
    
    def detect_conflicts_for_range(
        self, 
        db_session: Session, 
        params: Optional[ParametrosDeteccion] = None
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
        sesiones_ref, restricciones_ref = self._db_to_refs(db_session, rango=params.rango_fechas)
        
        # 2. Ejecutar detección completa
        resultados = self._execute_detection(sesiones_ref, restricciones_ref, params)
        
        return resultados
    
    def validate_session_constraints(
        self, 
        sesion_data: dict, 
        db_session: Session
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
        resultados = self._execute_detection(sesiones_con_temporal, restricciones_ref, params)
        
        # 5. Filtrar solo conflictos que involucran la sesión temporal
        sesion_temporal_id = sesion_temporal.id
        resultados_filtrados = [
            r for r in resultados 
            if sesion_temporal_id in [r.sesion_id, r.sesion_2_id]
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
        rango: Optional[Tuple[datetime, datetime]] = None
    ) -> Tuple[List[SesionRef], List[RestriccionRef]]:
        """
        Convierte modelos SQLAlchemy a referencias core.
        
        Args:
            db_session: Sesión de SQLAlchemy activa
            sesion_id: Si especificado, carga datos relacionados con esta sesión
            rango: Si especificado, filtra por rango de fechas
            
        Returns:
            Tupla (sesiones_ref, restricciones_ref)
        """
        # TODO: Implementar queries SQLAlchemy reales
        # Por ahora, implementación stub que simula datos
        
        sesiones_ref = self._load_sesiones_ref(db_session, sesion_id, rango)
        restricciones_ref = self._load_restricciones_ref(db_session, rango)
        
        return sesiones_ref, restricciones_ref
    
    def _load_sesiones_ref(
        self, 
        db_session: Session, 
        sesion_id: Optional[int], 
        rango: Optional[Tuple[datetime, datetime]]
    ) -> List[SesionRef]:
        """
        Carga sesiones de la BD y las convierte a SesionRef.
        
        TODO: Implementar queries SQLAlchemy reales cuando existan los modelos.
        """
        # Stub implementation - devolver lista vacía por ahora
        # En implementación real:
        # if sesion_id:
        #     db_sesiones = db_session.query(DBSesion).filter(DBSesion.id == sesion_id).all()
        # else:
        #     query = db_session.query(DBSesion)
        #     if rango:
        #         # Aplicar filtro de rango de fechas
        #         pass
        #     db_sesiones = query.all()
        #
        # return [self._db_sesion_to_ref(sesion) for sesion in db_sesiones]
        
        return []  # Stub
    
    def _load_restricciones_ref(
        self, 
        db_session: Session, 
        rango: Optional[Tuple[datetime, datetime]]
    ) -> List[RestriccionRef]:
        """
        Carga restricciones de la BD y las convierte a RestriccionRef.
        
        TODO: Implementar queries SQLAlchemy reales cuando existan los modelos.
        """
        # Stub implementation - devolver lista vacía por ahora
        # En implementación real:
        # query = db_session.query(DBRestriccion)
        # if rango:
        #     # Aplicar filtro de rango si es relevante
        #     pass
        # db_restricciones = query.all()
        #
        # return [self._db_restriccion_to_ref(rest) for rest in db_restricciones]
        
        return []  # Stub
    
    def _db_sesion_to_ref(self, db_sesion) -> SesionRef:
        """
        Convierte modelo SQLAlchemy Sesion a SesionRef.
        
        TODO: Implementar conversión real cuando existan los modelos.
        """
        # Stub implementation
        # En implementación real:
        # return SesionRef(
        #     id=db_sesion.id,
        #     profesor_ids=[p.id for p in db_sesion.profesores],
        #     aula_id=db_sesion.aula_id,
        #     slot=self._convert_slot_to_ref(db_sesion.slot_semanal) if db_sesion.slot_semanal else None,
        #     intervalo=self._convert_intervalo_to_ref(db_sesion.intervalo_fechado) if db_sesion.intervalo_fechado else None
        # )
        
        raise NotImplementedError("_db_sesion_to_ref pendiente de implementar con modelos reales")
    
    def _db_restriccion_to_ref(self, db_restriccion) -> RestriccionRef:
        """
        Convierte modelo SQLAlchemy Restriccion a RestriccionRef.
        
        TODO: Implementar conversión real cuando existan los modelos.
        """
        # Stub implementation
        raise NotImplementedError("_db_restriccion_to_ref pendiente de implementar con modelos reales")
    
    def _dict_to_sesion_ref(self, sesion_data: dict) -> SesionRef:
        """
        Convierte diccionario de datos a SesionRef temporal.
        
        Para uso en validate_session_constraints().
        """
        # TODO: Implementar conversión de dict a SesionRef
        # sesion_data debería contener: profesor_ids, aula_id, datos temporales, etc.
        
        raise NotImplementedError("_dict_to_sesion_ref pendiente de implementar")
    
    # ========================================================================
    # EJECUCIÓN DE DETECCIÓN (Core Logic)
    # ========================================================================
    
    def _execute_detection(
        self, 
        sesiones_ref: List[SesionRef], 
        restricciones_ref: List[RestriccionRef], 
        params: ParametrosDeteccion
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
        solapamientos_prof, solapamientos_aula, violaciones = \
            detectar_todos_los_conflictos_basicos(sesiones_ref, restricciones_ref)
        
        # 2. Convertir primitivas a ResultadoDeteccion (sin hash aún)
        resultados = self._primitives_to_results(
            solapamientos_prof, 
            solapamientos_aula, 
            violaciones, 
            params
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
        params: ParametrosDeteccion
    ) -> List[ResultadoDeteccion]:
        """
        Convierte primitivas de basic_rules a ResultadoDeteccion completos.
        
        Inyecta severidad y descripción baseline por tipo de conflicto.
        """
        resultados = []
        
        # Convertir solapamientos de profesor
        if params.incluir_solapamientos_profesor:
            for sesion_id1, sesion_id2, profesor_id in solapamientos_prof:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.SOLAPAMIENTO_PROFESOR,
                    # TODO Fase 4: Ajustar severidad según contexto (duración solape, tipo sesión, etc.)
                    severidad=SeveridadConflicto.ALTA,  # Baseline severity v1
                    descripcion=f"Profesor {profesor_id} tiene sesiones simultáneas (sesiones {sesion_id1}, {sesion_id2})",
                    sesion_id=sesion_id1,
                    sesion_2_id=sesion_id2,
                    profesor_id=profesor_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "solapamiento_profesor"
                    }
                )
                resultados.append(resultado)
        
        # Convertir solapamientos de aula
        if params.incluir_solapamientos_aula:
            for sesion_id1, sesion_id2, aula_id in solapamientos_aula:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.SOLAPAMIENTO_AULA,
                    # TODO Fase 4: Severidad según capacidad aula, tipo sesión, etc.
                    severidad=SeveridadConflicto.CRITICA,  # Baseline: aulas más críticas que profesores
                    descripcion=f"Aula {aula_id} tiene sesiones simultáneas (sesiones {sesion_id1}, {sesion_id2})",
                    sesion_id=sesion_id1,
                    sesion_2_id=sesion_id2,
                    aula_id=aula_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "solapamiento_aula"
                    }
                )
                resultados.append(resultado)
        
        # Convertir violaciones de restricción
        if params.incluir_violaciones_restriccion:
            for sesion_id, restriccion_id in violaciones:
                resultado = ResultadoDeteccion(
                    tipo=TipoConflicto.VIOLACION_RESTRICCION,
                    # TODO Fase 4: Severidad según obligatoriedad restricción (dura vs blanda)
                    severidad=SeveridadConflicto.MEDIA,  # Baseline v1, puede variar según tipo
                    descripcion=f"Sesión {sesion_id} viola restricción {restriccion_id}",
                    sesion_id=sesion_id,
                    restriccion_id=restriccion_id,
                    hash_deteccion="",  # Se rellena en _apply_hashing
                    datos_contexto={
                        "algoritmo": "basic_rules_v1",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tipo_primitiva": "violacion_restriccion"
                    }
                )
                resultados.append(resultado)
        
        return resultados
    
    def _apply_hashing(self, resultados: List[ResultadoDeteccion]) -> List[ResultadoDeteccion]:
        """
        Aplica hashing centralizado a todos los ResultadoDeteccion.
        
        Punto único para generación de hashes, usando hashing.py.
        Corregido: llama directamente generar_hash_conflicto(resultado).
        """
        resultados_con_hash: List[ResultadoDeteccion] = []
        for r in resultados:
            h = generar_hash_conflicto(r)  # recibe ResultadoDeteccion completo (ya corregido)
            r2 = r.model_copy(update={"hash_deteccion": h})
            resultados_con_hash.append(r2)
        return resultados_con_hash
    
    def _deduplicate_by_hash(self, resultados: List[ResultadoDeteccion]) -> List[ResultadoDeteccion]:
        """
        Deduplicar ResultadoDeteccion por hash_deteccion.
        
        Garantiza que no hay conflictos duplicados en el resultado final.
        """
        seen_hashes: Set[str] = set()
        resultados_deduplicados = []
        
        for resultado in resultados:
            if resultado.hash_deteccion not in seen_hashes:
                seen_hashes.add(resultado.hash_deteccion)
                resultados_deduplicados.append(resultado)
        
        return resultados_deduplicados
    
    def _apply_filters(
        self, 
        resultados: List[ResultadoDeteccion], 
        params: ParametrosDeteccion
    ) -> List[ResultadoDeteccion]:
        """
        Aplica filtros finales según ParametrosDeteccion.
        
        Filtra por severidad mínima y rango de fechas si están especificados.
        """
        resultados_filtrados = resultados
        
        # Filtro por severidad mínima
        severidades_orden = {
            SeveridadConflicto.BAJA: 1,
            SeveridadConflicto.MEDIA: 2,
            SeveridadConflicto.ALTA: 3,
            SeveridadConflicto.CRITICA: 4
        }
        
        severidad_minima_valor = severidades_orden[params.severidad_minima]
        resultados_filtrados = [
            r for r in resultados_filtrados 
            if severidades_orden[r.severidad] >= severidad_minima_valor
        ]
        
        # TODO: Filtro por rango de fechas
        # Requiere que datos_contexto contengan información temporal
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
