"""
Módulo para la detección de conflictos de compatibilidad académica en horarios.

Este módulo valida que las sesiones propuestas sean compatibles desde el punto
de vista académico, considerando la estructura curricular y las relaciones
entre asignaturas, grados y menciones.

Tipos de conflictos validados:
1. CURSO + CUATRIMESTRE: Asignaturas del mismo curso y cuatrimestre simultáneas
2. MENCIÓN: Asignaturas de la misma mención en horario simultáneo
3. GRADO COMPARTIDO: Asignaturas del mismo grado con solapamiento problemático
4. DEPENDENCIAS CURRICULARES: Conflictos en el flujo académico típico

Nota: Se centra en conflictos académicos de planificación curricular.
Los conflictos de recursos físicos van en otros módulos específicos.
"""

from datetime import time, datetime
from typing import List, Optional, Dict, Any, Set, Tuple, Union
from dataclasses import dataclass
import logging

# SQLAlchemy imports
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Imports de modelos
from models.sesion import Sesion
from models.asignatura import Asignatura, AsignaturaGrado, AsignaturaMencion
from models.grado import Grado
from models.mencion import Mencion

# Imports de schemas
from schemas.sesion import SesionCreate, SesionOut
from schemas.asignatura import AsignaturaOut

# Imports de enums
from constants.enums import DiaSemanaEnum

# Configuración de logging
logger = logging.getLogger(__name__)


@dataclass
class ConflictoCompatibilidad:
    """Estructura para representar un conflicto de compatibilidad académica detectado"""
    tipo: str
    severidad: str
    mensaje: str
    asignatura_conflictiva: Optional[AsignaturaOut] = None
    sesion_conflictiva: Optional[Dict[str, Any]] = None
    entidades_afectadas: Optional[List[str]] = None
    estudiantes_afectados: Optional[int] = None
    detalles: Optional[Dict[str, Any]] = None


# ========================================
# FUNCIONES DE DETECCIÓN DE CONFLICTOS
# ========================================


def detectar_conflictos_curso_cuatrimestre(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> List[ConflictoCompatibilidad]:
    """
    Detecta conflictos críticos entre asignaturas del mismo curso y cuatrimestre.
    
    Este es el conflicto MÁS CRÍTICO: si dos asignaturas son del mismo curso
    y cuatrimestre, los estudiantes no pueden asistir a ambas simultáneamente.
    """
    conflictos = []
    
    try:
        # Obtener información de la asignatura actual
        asignatura_actual = db.query(Asignatura).filter(
            Asignatura.id == sesion.asignatura_id
        ).first()
        
        if not asignatura_actual:
            logger.warning(f"No se encontró asignatura con ID {sesion.asignatura_id}")
            return conflictos
        
        # Buscar sesiones existentes del mismo día que se solapen
        sesiones_solapadas = _buscar_sesiones_solapadas(db, sesion, sesion_id_ignorar)
        
        for sesion_existente in sesiones_solapadas:
            asignatura_existente = sesion_existente.asignatura
            
            # Verificar si son del mismo curso Y cuatrimestre
            if (asignatura_actual.curso == asignatura_existente.curso and 
                asignatura_actual.cuatrimestre == asignatura_existente.cuatrimestre and
                asignatura_actual.id != asignatura_existente.id):
                
                # Obtener grados afectados (optimizado)
                grados_afectados = _obtener_grados_compartidos(db, asignatura_actual.id, asignatura_existente.id)
                
                if grados_afectados:
                    conflicto = ConflictoCompatibilidad(
                        tipo="conflicto_curso_cuatrimestre",
                        severidad="critico",
                        mensaje=f"Conflicto crítico: {asignatura_actual.nombre} (ID: {asignatura_actual.id}) y "
                               f"{asignatura_existente.nombre} (ID: {asignatura_existente.id}) "
                               f"son ambas de {asignatura_actual.curso}º curso, {asignatura_actual.cuatrimestre}º cuatrimestre. "
                               f"Los estudiantes no pueden asistir a ambas clases simultáneamente.",
                        asignatura_conflictiva=AsignaturaOut.model_validate(asignatura_existente),
                        sesion_conflictiva={
                            "id": sesion_existente.id,
                            "dia_semana": sesion_existente.dia_semana,
                            "inicio": str(sesion_existente.inicio),
                            "fin": str(sesion_existente.fin),
                            "aula_id": sesion_existente.aula_id
                        },
                        entidades_afectadas=[grado.nombre for grado in grados_afectados],
                        estudiantes_afectados=min(asignatura_actual.estudiantes_matriculados or 0,
                                                asignatura_existente.estudiantes_matriculados or 0),
                        detalles={
                            "curso": asignatura_actual.curso,
                            "cuatrimestre": asignatura_actual.cuatrimestre,
                            "asignatura_actual_id": asignatura_actual.id,
                            "asignatura_conflictiva_id": asignatura_existente.id,
                            "grados_afectados": len(grados_afectados),
                            "solapamiento_horario": _calcular_solapamiento(sesion, sesion_existente)
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de curso-cuatrimestre: {e}")
        conflictos.append(ConflictoCompatibilidad(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos de curso-cuatrimestre: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_mencion(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> List[ConflictoCompatibilidad]:
    """
    Detecta conflictos entre asignaturas de la misma mención.
    
    Los estudiantes de una mención específica no pueden estar en dos
    asignaturas de su mención al mismo tiempo.
    """
    conflictos = []
    
    try:
        # Obtener menciones de la asignatura actual
        menciones_actuales = db.query(AsignaturaMencion).filter(
            AsignaturaMencion.asignatura_id == sesion.asignatura_id
        ).all()
        
        if not menciones_actuales:
            # Si la asignatura no tiene menciones específicas, no hay conflictos de mención
            return conflictos
        
        menciones_ids = [am.mencion_id for am in menciones_actuales]
        
        # Buscar sesiones solapadas
        sesiones_solapadas = _buscar_sesiones_solapadas(db, sesion, sesion_id_ignorar)
        
        for sesion_existente in sesiones_solapadas:
            # Verificar si la asignatura existente comparte alguna mención
            menciones_existente = db.query(AsignaturaMencion).filter(
                AsignaturaMencion.asignatura_id == sesion_existente.asignatura_id,
                AsignaturaMencion.mencion_id.in_(menciones_ids)
            ).all()
            
            if menciones_existente and sesion_existente.asignatura_id != sesion.asignatura_id:
                # Obtener información de las menciones compartidas
                menciones_compartidas = db.query(Mencion).filter(
                    Mencion.id.in_([me.mencion_id for me in menciones_existente])
                ).all()
                
                for mencion in menciones_compartidas:
                    conflicto = ConflictoCompatibilidad(
                        tipo="conflicto_mencion",
                        severidad="alto",
                        mensaje=f"Conflicto de mención: {sesion_existente.asignatura.nombre} (ID: {sesion_existente.asignatura_id}) "
                               f"y la asignatura solicitada pertenecen ambas a la mención '{mencion.nombre}'. "
                               f"Los estudiantes de esta mención no pueden asistir a ambas clases simultáneamente.",
                        asignatura_conflictiva=AsignaturaOut.model_validate(sesion_existente.asignatura),
                        sesion_conflictiva={
                            "id": sesion_existente.id,
                            "dia_semana": sesion_existente.dia_semana,
                            "inicio": str(sesion_existente.inicio),
                            "fin": str(sesion_existente.fin),
                            "aula_id": sesion_existente.aula_id
                        },
                        entidades_afectadas=[f"Mención {mencion.nombre}"],
                        detalles={
                            "mencion_id": mencion.id,
                            "mencion_nombre": mencion.nombre,
                            "grado_mencion": mencion.grado.nombre if mencion.grado else "No definido",
                            "solapamiento_horario": _calcular_solapamiento(sesion, sesion_existente)
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de mención: {e}")
        conflictos.append(ConflictoCompatibilidad(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos de mención: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_grado_compartido(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> List[ConflictoCompatibilidad]:
    """
    Detecta conflictos entre asignaturas que comparten grados.
    
    Analiza si asignaturas del mismo grado tienen solapamientos problemáticos,
    especialmente si son asignaturas comunes o de formación básica.
    """
    conflictos = []
    
    try:
        # Obtener grados de la asignatura actual
        grados_actuales = db.query(AsignaturaGrado).filter(
            AsignaturaGrado.asignatura_id == sesion.asignatura_id
        ).all()
        
        if not grados_actuales:
            return conflictos
        
        grados_ids = [ag.grado_id for ag in grados_actuales]
        
        # Buscar sesiones solapadas
        sesiones_solapadas = _buscar_sesiones_solapadas(db, sesion, sesion_id_ignorar)
        
        for sesion_existente in sesiones_solapadas:
            if sesion_existente.asignatura_id == sesion.asignatura_id:
                continue
                
            # Verificar si comparten algún grado
            grados_compartidos = db.query(AsignaturaGrado).filter(
                AsignaturaGrado.asignatura_id == sesion_existente.asignatura_id,
                AsignaturaGrado.grado_id.in_(grados_ids)
            ).all()
            
            if grados_compartidos:
                # Determinar severidad avanzada considerando cuatrimestre
                severidad = _determinar_severidad_grado(
                    db, sesion.asignatura_id, sesion_existente.asignatura_id, grados_compartidos
                )
                
                if severidad != "bajo":  # Solo reportar conflictos significativos
                    # Optimización: usar función unificada para obtener nombres de grados
                    grados_afectados = _obtener_grados_compartidos(db, sesion.asignatura_id, sesion_existente.asignatura_id)
                    grados_nombres = [grado.nombre for grado in grados_afectados]
                    
                    conflicto = ConflictoCompatibilidad(
                        tipo="conflicto_grado_compartido",
                        severidad=severidad,
                        mensaje=f"Conflicto de grado: {sesion_existente.asignatura.nombre} (ID: {sesion_existente.asignatura_id}) "
                               f"y la asignatura solicitada comparten el/los grado(s): {', '.join(grados_nombres)}. "
                               f"Esto puede limitar las opciones de horario para los estudiantes.",
                        asignatura_conflictiva=AsignaturaOut.model_validate(sesion_existente.asignatura),
                        sesion_conflictiva={
                            "id": sesion_existente.id,
                            "dia_semana": sesion_existente.dia_semana,
                            "inicio": str(sesion_existente.inicio),
                            "fin": str(sesion_existente.fin),
                            "aula_id": sesion_existente.aula_id
                        },
                        entidades_afectadas=grados_nombres,
                        detalles={
                            "grados_compartidos": len(grados_compartidos),
                            "grados_nombres": grados_nombres,
                            "solapamiento_horario": _calcular_solapamiento(sesion, sesion_existente)
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de grado compartido: {e}")
        conflictos.append(ConflictoCompatibilidad(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos de grado compartido: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_dependencias_curriculares(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> List[ConflictoCompatibilidad]:
    """
    Detecta conflictos en el flujo curricular típico.
    
    Identifica patrones problemáticos como:
    - Muchas asignaturas básicas del mismo curso solapando
    - Asignaturas con alta carga horaria en el mismo horario
    - Patrones que dificultan la progresión académica normal
    """
    conflictos = []
    
    try:
        # Obtener información de la asignatura actual
        asignatura_actual = db.query(Asignatura).filter(
            Asignatura.id == sesion.asignatura_id
        ).first()
        
        if not asignatura_actual:
            return conflictos
        
        # Buscar sesiones solapadas del mismo día
        sesiones_solapadas = _buscar_sesiones_solapadas(db, sesion, sesion_id_ignorar)
        
        # Analizar patrones problemáticos
        asignaturas_mismo_curso = []
        asignaturas_alta_carga = []
        
        for sesion_existente in sesiones_solapadas:
            if sesion_existente.asignatura_id == sesion.asignatura_id:
                continue
                
            asignatura_existente = sesion_existente.asignatura
            
            # Asignaturas del mismo curso (posible sobrecarga)
            if asignatura_actual.curso == asignatura_existente.curso:
                asignaturas_mismo_curso.append((sesion_existente, asignatura_existente))
            
            # Asignaturas con alta carga horaria (>= 6 horas semanales)
            if (asignatura_existente.horas_semanales and asignatura_existente.horas_semanales >= 6):
                asignaturas_alta_carga.append((sesion_existente, asignatura_existente))
        
        # Generar conflictos si hay patrones problemáticos
        # Umbral: 2 asignaturas en la lista + la actual = 3 o más asignaturas del mismo curso simultáneas
        if len(asignaturas_mismo_curso) >= 2:
            conflicto = ConflictoCompatibilidad(
                tipo="sobrecarga_curso",
                severidad="medio",
                mensaje=f"Posible sobrecarga curricular: se detectaron múltiples asignaturas "
                       f"de {asignatura_actual.curso}º curso en el mismo horario. "
                       f"Esto puede dificultar la asistencia a clases para los estudiantes.",
                entidades_afectadas=[f"{asignatura_actual.curso}º curso"],
                detalles={
                    "curso": asignatura_actual.curso,
                    "asignaturas_simultaneas": len(asignaturas_mismo_curso) + 1,
                    "asignaturas_conflictivas": [f"{a[1].nombre} (ID: {a[1].id})" for a in asignaturas_mismo_curso]
                }
            )
            conflictos.append(conflicto)
        
        if asignaturas_alta_carga and asignatura_actual.horas_semanales and asignatura_actual.horas_semanales >= 6:
            conflicto = ConflictoCompatibilidad(
                tipo="sobrecarga_horaria",
                severidad="medio",
                mensaje=f"Posible sobrecarga horaria: asignaturas con alta carga de horas "
                       f"({asignatura_actual.horas_semanales}h semanales) programadas simultáneamente. "
                       f"Esto puede impactar en la calidad del aprendizaje.",
                detalles={
                    "horas_semanales_actual": asignatura_actual.horas_semanales,
                    "asignaturas_alta_carga": len(asignaturas_alta_carga),
                    "total_horas_solapadas": sum(a[1].horas_semanales or 0 for a in asignaturas_alta_carga) + asignatura_actual.horas_semanales,
                    "asignaturas_conflictivas": [f"{a[1].nombre} (ID: {a[1].id})" for a in asignaturas_alta_carga]
                }
            )
            conflictos.append(conflicto)
            
    except Exception as e:
        logger.error(f"Error al detectar conflictos de dependencias curriculares: {e}")
        conflictos.append(ConflictoCompatibilidad(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos curriculares: {str(e)}"
        ))
    
    return conflictos


def detectar_todos_conflictos_compatibilidad(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> List[ConflictoCompatibilidad]:
    """
    Función principal que ejecuta todas las validaciones de compatibilidad académica.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
        sesion_id_ignorar: ID de sesión a excluir (útil para updates)
    
    Returns:
        Lista completa de todos los conflictos de compatibilidad detectados
    """
    todos_conflictos = []
    
    logger.info(f"Iniciando detección de conflictos de compatibilidad para sesión: "
               f"Asignatura {sesion.asignatura_id}, {sesion.dia_semana} {sesion.inicio}-{sesion.fin}")
    
    # Ejecutar todas las validaciones de compatibilidad en orden de prioridad
    todos_conflictos.extend(detectar_conflictos_curso_cuatrimestre(db, sesion, sesion_id_ignorar))
    todos_conflictos.extend(detectar_conflictos_mencion(db, sesion, sesion_id_ignorar))
    todos_conflictos.extend(detectar_conflictos_grado_compartido(db, sesion, sesion_id_ignorar))
    todos_conflictos.extend(detectar_conflictos_dependencias_curriculares(db, sesion, sesion_id_ignorar))
    
    logger.info(f"Detección de compatibilidad completada. {len(todos_conflictos)} conflictos encontrados")
    
    return todos_conflictos


# ========================================
# FUNCIONES AUXILIARES (UNIFICADAS)
# ========================================


def _as_time(tiempo: Union[str, time]) -> time:
    """Convierte string de tiempo a objeto time de forma consistente."""
    if isinstance(tiempo, str):
        try:
            return datetime.strptime(tiempo, "%H:%M").time()
        except ValueError:
            try:
                return datetime.strptime(tiempo, "%H:%M:%S").time()
            except ValueError:
                logger.error(f"Formato de hora inválido: {tiempo}")
                raise ValueError(f"Formato de hora inválido: {tiempo}")
    return tiempo


def _buscar_sesiones_solapadas(
    db: Session, 
    sesion_crear: SesionCreate, 
    sesion_id_ignorar: Optional[int] = None
) -> List[SesionOut]:
    """
    Busca sesiones que se solapen temporalmente con la nueva sesión, 
    excluyendo opcionalmente una sesión específica por ID.
    """
    try:
        inicio_nueva = _as_time(sesion_crear.inicio)
        fin_nueva = _as_time(sesion_crear.fin)
        
        logger.info(f"Buscando solapamiento para el día {sesion_crear.dia_semana}")
        
        query = db.query(Sesion).filter(
            Sesion.dia_semana == sesion_crear.dia_semana,
            Sesion.inicio < sesion_crear.fin,
            Sesion.fin > sesion_crear.inicio
        )
        
        if sesion_id_ignorar:
            query = query.filter(Sesion.id != sesion_id_ignorar)
        
        return [SesionOut.model_validate(sesion) for sesion in query.all()]
        
    except Exception as e:
        logger.error(f"Error al buscar sesiones solapadas: {e}")
        return []


def _obtener_grados_compartidos(db: Session, asignatura_id1: int, asignatura_id2: int) -> List[Grado]:
    """
    Obtiene los grados que comparten dos asignaturas de forma optimizada.
    """
    try:
        # Obtener grados compartidos en una sola query optimizada
        grados_compartidos = db.query(Grado).join(
            AsignaturaGrado, Grado.id == AsignaturaGrado.grado_id
        ).filter(
            AsignaturaGrado.asignatura_id == asignatura_id2,
            AsignaturaGrado.grado_id.in_(
                db.query(AsignaturaGrado.grado_id).filter(
                    AsignaturaGrado.asignatura_id == asignatura_id1
                )
            )
        ).all()
        
        return grados_compartidos
        
    except Exception as e:
        logger.error(f"Error al obtener grados compartidos: {e}")
        return []


def _determinar_severidad_grado(db: Session, asignatura_id1: int, asignatura_id2: int, 
                               grados_compartidos: List[AsignaturaGrado]) -> str:
    """
    Determina la severidad de un conflicto considerando curso y cuatrimestre de forma avanzada.
    """
    try:
        asignatura1 = db.query(Asignatura).filter(Asignatura.id == asignatura_id1).first()
        asignatura2 = db.query(Asignatura).filter(Asignatura.id == asignatura_id2).first()
        
        if not asignatura1 or not asignatura2:
            return "bajo"
        
        # Severidad avanzada considerando cuatrimestre
        # 1. Mismo curso Y mismo cuatrimestre = crítico
        if (asignatura1.curso == asignatura2.curso and 
            asignatura1.cuatrimestre == asignatura2.cuatrimestre):
            return "critico"

        # 2. Mismo curso pero distinto cuatrimestre = alto
        if asignatura1.curso == asignatura2.curso:
            return "alto"

        # 3. Mismo cuatrimestre pero distinto curso (1 curso de diferencia) = medio-alto
        if (asignatura1.cuatrimestre == asignatura2.cuatrimestre and 
            abs(asignatura1.curso - asignatura2.curso) == 1):
            return "medio"
        
        # 4. Diferencia de 1 curso (distinto cuatrimestre) = medio
        if abs(asignatura1.curso - asignatura2.curso) == 1:
            return "medio"
        
        # 5. Muchos grados compartidos = incrementa severidad
        if len(grados_compartidos) >= 3:
            return "medio"
        
        # 6. Por defecto = bajo
        return "bajo"
        
    except Exception as e:
        logger.error(f"Error al determinar severidad: {e}")
        return "bajo"


def _calcular_solapamiento(sesion_nueva: SesionCreate, sesion_existente: SesionOut) -> Dict[str, Any]:
    """
    Calcula información detallada sobre el solapamiento entre dos sesiones.
    Protegido contra errores de división por cero.
    """
    try:
        inicio_nueva = _as_time(sesion_nueva.inicio)
        fin_nueva = _as_time(sesion_nueva.fin)
        
        inicio_existente = _as_time(sesion_existente.inicio)
        fin_existente = _as_time(sesion_existente.fin)
        
        # Calcular inicio y fin del solapamiento
        inicio_solape = max(inicio_nueva, inicio_existente)
        fin_solape = min(fin_nueva, fin_existente)
        
        # Calcular duración del solapamiento en minutos
        duracion_solape = (fin_solape.hour * 60 + fin_solape.minute) - (inicio_solape.hour * 60 + inicio_solape.minute)
        
        # Calcular duración total de la sesión nueva (proteger contra división por cero)
        duracion_total_nueva = (fin_nueva.hour * 60 + fin_nueva.minute) - (inicio_nueva.hour * 60 + inicio_nueva.minute)
        duracion_total_nueva = max(duracion_total_nueva, 1)  # Protección divide-by-zero
        
        # Calcular porcentaje de solapamiento
        porcentaje_solapamiento = round((duracion_solape / duracion_total_nueva) * 100, 2)
        
        return {
            "inicio_solapamiento": str(inicio_solape),
            "fin_solapamiento": str(fin_solape),
            "duracion_minutos": duracion_solape,
            "duracion_total_nueva": duracion_total_nueva,
            "porcentaje_solapamiento": porcentaje_solapamiento
        }
        
    except Exception as e:
        logger.error(f"Error al calcular solapamiento: {e}")
        return {"error": str(e)}
