"""
Módulo para la detección de conflictos contra restricciones activas en horarios académicos.

Este módulo valida sesiones propuestas contra las restricciones que están 
almacenadas en la base de datos y marcadas como activas.

Tipos de restricciones validadas (según TipoRestriccionEnum):
1. HORARIO_PROFESOR: días no disponibles, horario máximo de trabajo del profesor
2. DISPONIBILIDAD_AULA: aula no disponible por reservas, uso específico
3. BLOQUEO_TEMPORAL: bloqueos específicos de horarios (eventos, exámenes)
4. MANTENIMIENTO: mantenimiento programado de aulas o equipos

Nota: Solo valida contra restricciones de disponibilidad temporal existentes en BD.
Las validaciones de formato están cubiertas por los schemas de Pydantic.
Los conflictos de capacidad/equipamiento van en otros módulos específicos.
"""

from datetime import time, datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

# SQLAlchemy imports
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Imports de modelos
from models.sesion import Sesion
from models.restriccion import Restriccion
from models.asignatura import Asignatura
from models.profesor import Profesor
from models.aula import Aula

# Imports de schemas
from schemas.sesion import SesionCreate, SesionOut
from schemas.restriccion import RestriccionOut

# Imports de enums
from constants.enums import DiaSemanaEnum, TipoRestriccionEnum, TipoAulaEnum

# Configuración de logging
logger = logging.getLogger(__name__)


@dataclass
class ConflictoRestriccion:
    """Estructura para representar un conflicto de restricción detectado"""
    tipo: str
    severidad: str
    mensaje: str
    restriccion_violada: Optional[RestriccionOut] = None
    sesion_conflictiva: Optional[SesionOut] = None
    detalles: Optional[Dict[str, Any]] = None



# ========================================
# FUNCIONES DE DETECCIÓN DE CONFLICTOS
# ========================================


def detectar_conflictos_restriccion_profesor(db: Session, sesion: SesionCreate) -> List[ConflictoRestriccion]:
    """
    Valida si una sesión viola restricciones activas de horario de profesor.
    
    Verifica restricciones del tipo HORARIO_PROFESOR que incluyen:
    - Días no disponibles (profesor no trabaja ciertos días)
    - Horario mínimo de trabajo (profesor no puede trabajar antes de cierta hora)
    - Horario máximo de trabajo (profesor no puede trabajar después de cierta hora)
    - Razones específicas (tiempo parcial, compromisos externos, etc.)
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados por violación de restricciones
    """
    conflictos = []
    
    try:
        # Buscar restricciones activas de horario para este profesor
        restricciones_profesor = db.query(Restriccion).filter(
            Restriccion.tipo == TipoRestriccionEnum.HORARIO_PROFESOR,
            Restriccion.profesor_id == sesion.profesor_id,
            Restriccion.activa == True
        ).all()
        
        logger.info(f"Validando {len(restricciones_profesor)} restricciones de horario "
                   f"para profesor {sesion.profesor_id}")
        
        for restriccion in restricciones_profesor:
            valor = restriccion.valor  # Dict ya validado por schema
            
            # Validar día no disponible
            dias_no_disponibles = valor.get('dias_no_disponible', [])
            if sesion.dia.value in dias_no_disponibles:
                # Obtener información del profesor para el mensaje
                profesor = db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first()
                profesor_nombre = profesor.nombre if profesor else f"ID {sesion.profesor_id}"
                
                razon = valor.get('razon', 'Restricción de horario')
                
                conflicto = ConflictoRestriccion(
                    tipo="restriccion_dia_no_disponible",
                    severidad="critico",
                    mensaje=f"El profesor {profesor_nombre} no está disponible los {sesion.dia.value}. "
                           f"Razón: {razon}",
                    restriccion_violada=RestriccionOut.model_validate(restriccion),
                    detalles={
                        "profesor_id": sesion.profesor_id,
                        "profesor_nombre": profesor_nombre,
                        "dia_solicitado": sesion.dia.value,
                        "dias_no_disponibles": dias_no_disponibles,
                        "razon": razon,
                        "prioridad_restriccion": restriccion.prioridad
                    }
                )
                conflictos.append(conflicto)
            
            # Validar horario mínimo de trabajo (desde qué hora puede empezar)
            horario_minimo_str = valor.get('horario_minimo')
            if horario_minimo_str:
                try:
                    horario_minimo = time.fromisoformat(horario_minimo_str)
                    
                    # Verificar si la sesión empieza antes del horario mínimo
                    if sesion.hora_inicio < horario_minimo:
                        profesor = db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first()
                        profesor_nombre = profesor.nombre if profesor else f"ID {sesion.profesor_id}"
                        razon = valor.get('razon', 'Restricción de horario')
                        
                        conflicto = ConflictoRestriccion(
                            tipo="restriccion_horario_minimo",
                            severidad="critico",
                            mensaje=f"El profesor {profesor_nombre} no puede trabajar antes de las {horario_minimo}. "
                                   f"Sesión programada: {sesion.hora_inicio}-{sesion.hora_fin}. Razón: {razon}",
                            restriccion_violada=RestriccionOut.model_validate(restriccion),
                            detalles={
                                "profesor_id": sesion.profesor_id,
                                "profesor_nombre": profesor_nombre,
                                "horario_minimo_permitido": horario_minimo_str,
                                "hora_inicio_solicitada": str(sesion.hora_inicio),
                                "hora_fin_solicitada": str(sesion.hora_fin),
                                "razon": razon,
                                "prioridad_restriccion": restriccion.prioridad
                            }
                        )
                        conflictos.append(conflicto)
                        
                except ValueError:
                    logger.warning(f"Formato de horario_minimo inválido en restricción {restriccion.id}: {horario_minimo_str}")
            
            # Validar horario máximo de trabajo
            horario_maximo_str = valor.get('horario_maximo')
            if horario_maximo_str:
                try:
                    horario_maximo = time.fromisoformat(horario_maximo_str)
                    
                    # Verificar si la sesión empieza después del horario máximo
                    if sesion.hora_inicio > horario_maximo:
                        profesor = db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first()
                        profesor_nombre = profesor.nombre if profesor else f"ID {sesion.profesor_id}"
                        razon = valor.get('razon', 'Restricción de horario')
                        
                        conflicto = ConflictoRestriccion(
                            tipo="restriccion_horario_maximo",
                            severidad="critico",
                            mensaje=f"El profesor {profesor_nombre} no puede trabajar después de las {horario_maximo}. "
                                   f"Sesión programada: {sesion.hora_inicio}. Razón: {razon}",
                            restriccion_violada=RestriccionOut.model_validate(restriccion),
                            detalles={
                                "profesor_id": sesion.profesor_id,
                                "profesor_nombre": profesor_nombre,
                                "horario_maximo_permitido": horario_maximo_str,
                                "hora_inicio_solicitada": str(sesion.hora_inicio),
                                "razon": razon,
                                "prioridad_restriccion": restriccion.prioridad
                            }
                        )
                        conflictos.append(conflicto)
                        
                    # Verificar si la sesión termina después del horario máximo
                    elif sesion.hora_fin > horario_maximo:
                        profesor = db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first()
                        profesor_nombre = profesor.nombre if profesor else f"ID {sesion.profesor_id}"
                        razon = valor.get('razon', 'Restricción de horario')
                        
                        conflicto = ConflictoRestriccion(
                            tipo="restriccion_horario_maximo_fin",
                            severidad="alto",
                            mensaje=f"La sesión del profesor {profesor_nombre} termina después de su horario máximo "
                                   f"({horario_maximo}). Sesión: {sesion.hora_inicio}-{sesion.hora_fin}. Razón: {razon}",
                            restriccion_violada=RestriccionOut.model_validate(restriccion),
                            detalles={
                                "profesor_id": sesion.profesor_id,
                                "profesor_nombre": profesor_nombre,
                                "horario_maximo_permitido": horario_maximo_str,
                                "hora_fin_solicitada": str(sesion.hora_fin),
                                "razon": razon,
                                "prioridad_restriccion": restriccion.prioridad
                            }
                        )
                        conflictos.append(conflicto)
                        
                except ValueError:
                    logger.warning(f"Formato de horario_maximo inválido en restricción {restriccion.id}: {horario_maximo_str}")
                    
    except Exception as e:
        logger.error(f"Error al validar restricciones de profesor: {e}")
        conflictos.append(ConflictoRestriccion(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al validar restricciones de profesor: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_restriccion_aula(db: Session, sesion: SesionCreate) -> List[ConflictoRestriccion]:
    """
    Detecta si una sesión viola restricciones activas de disponibilidad de aula.
    
    Verifica restricciones del tipo DISPONIBILIDAD_AULA que incluyen:
    - Horarios no disponibles (aula reservada para otros usos)
    - Reservas especiales (eventos, reuniones, uso específico)
    - Períodos de no disponibilidad programados
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados por violación de restricciones de aula
    """
    conflictos = []
    
    try:
        # Buscar restricciones activas de disponibilidad para esta aula
        restricciones_aula = db.query(Restriccion).filter(
            Restriccion.tipo == TipoRestriccionEnum.DISPONIBILIDAD_AULA,
            Restriccion.aula_id == sesion.aula_id,
            Restriccion.activa == True
        ).all()
        
        logger.info(f"Validando {len(restricciones_aula)} restricciones de disponibilidad "
                   f"para aula {sesion.aula_id}")
        
        for restriccion in restricciones_aula:
            valor = restriccion.valor  # Dict ya validado por schema
            
            # Validar horarios no disponibles
            horarios_no_disponible = valor.get('horarios_no_disponible', [])
            
            for horario_bloqueado in horarios_no_disponible:
                if _sesion_en_horario_bloqueado(sesion, horario_bloqueado):
                    # Obtener información del aula para el mensaje
                    aula = db.query(Aula).filter(Aula.id == sesion.aula_id).first()
                    aula_nombre = aula.nombre if aula else f"ID {sesion.aula_id}"
                    
                    razon = valor.get('razon', 'Aula no disponible')
                    horario_str = f"{horario_bloqueado.get('dia', 'N/A')} {horario_bloqueado.get('inicio', 'N/A')}-{horario_bloqueado.get('fin', 'N/A')}"
                    
                    conflicto = ConflictoRestriccion(
                        tipo="restriccion_aula_no_disponible",
                        severidad="critico",
                        mensaje=f"El aula {aula_nombre} no está disponible el {horario_str}. "
                               f"Razón: {razon}",
                        restriccion_violada=RestriccionOut.model_validate(restriccion),
                        detalles={
                            "aula_id": sesion.aula_id,
                            "aula_nombre": aula_nombre,
                            "dia_solicitado": sesion.dia.value,
                            "horario_solicitado": f"{sesion.hora_inicio}-{sesion.hora_fin}",
                            "horario_bloqueado": horario_str,
                            "razon": razon,
                            "prioridad_restriccion": restriccion.prioridad
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de restricción de aula: {e}")
        conflictos.append(ConflictoRestriccion(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos de aula: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_bloqueo_temporal(db: Session, sesion: SesionCreate) -> List[ConflictoRestriccion]:
    """
    Detecta si una sesión viola restricciones de bloqueo temporal.
    
    Verifica restricciones del tipo BLOQUEO_TEMPORAL que incluyen:
    - Bloqueos específicos de horarios (eventos especiales, exámenes)
    - Períodos temporales donde no se pueden programar clases
    - Restricciones por fechas específicas
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados por bloqueos temporales
    """
    conflictos = []
    
    try:
        # Buscar restricciones activas de bloqueo temporal
        # Pueden afectar a toda la institución (sin IDs específicos) o entidades específicas
        restricciones_bloqueo = db.query(Restriccion).filter(
            Restriccion.tipo == TipoRestriccionEnum.BLOQUEO_TEMPORAL,
            Restriccion.activa == True,
            or_(
                # Bloqueos globales (sin entidad específica)
                and_(
                    Restriccion.profesor_id.is_(None),
                    Restriccion.aula_id.is_(None),
                    Restriccion.asignatura_id.is_(None)
                ),
                # Bloqueos específicos para las entidades de esta sesión
                Restriccion.profesor_id == sesion.profesor_id,
                Restriccion.aula_id == sesion.aula_id,
                Restriccion.asignatura_id == sesion.asignatura_id
            )
        ).all()
        
        logger.info(f"Validando {len(restricciones_bloqueo)} restricciones de bloqueo temporal")
        
        for restriccion in restricciones_bloqueo:
            valor = restriccion.valor  # Dict ya validado por schema
            
            # Validar bloqueos por horarios específicos
            horarios_bloqueados = valor.get('horarios_bloqueados', [])
            
            for bloqueo in horarios_bloqueados:
                if _sesion_en_horario_bloqueado(sesion, bloqueo):
                    razon = valor.get('razon', 'Bloqueo temporal activo')
                    evento = valor.get('evento', 'Evento especial')
                    
                    conflicto = ConflictoRestriccion(
                        tipo="bloqueo_temporal",
                        severidad="alto",
                        mensaje=f"Horario bloqueado por {evento}. "
                               f"Sesión solicitada: {sesion.dia.value} {sesion.hora_inicio}-{sesion.hora_fin}. "
                               f"Razón: {razon}",
                        restriccion_violada=RestriccionOut.model_validate(restriccion),
                        detalles={
                            "dia_solicitado": sesion.dia.value,
                            "horario_solicitado": f"{sesion.hora_inicio}-{sesion.hora_fin}",
                            "evento": evento,
                            "razon": razon,
                            "prioridad_restriccion": restriccion.prioridad,
                            "alcance": "global" if not any([restriccion.profesor_id, restriccion.aula_id, restriccion.asignatura_id]) else "específico"
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de bloqueo temporal: {e}")
        conflictos.append(ConflictoRestriccion(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar bloqueos temporales: {str(e)}"
        ))
    
    return conflictos


def detectar_conflictos_mantenimiento(db: Session, sesion: SesionCreate) -> List[ConflictoRestriccion]:
    """
    Detecta si una sesión viola restricciones de mantenimiento programado.
    
    Verifica restricciones del tipo MANTENIMIENTO que incluyen:
    - Mantenimiento programado de aulas
    - Mantenimiento de equipos específicos
    - Períodos de no disponibilidad por trabajos de mantenimiento
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados por mantenimiento programado
    """
    conflictos = []
    
    try:
        # Buscar restricciones activas de mantenimiento que afecten al aula
        restricciones_mantenimiento = db.query(Restriccion).filter(
            Restriccion.tipo == TipoRestriccionEnum.MANTENIMIENTO,
            Restriccion.activa == True,
            or_(
                # Mantenimiento específico del aula
                Restriccion.aula_id == sesion.aula_id,
                # Mantenimiento general (sin aula específica)
                Restriccion.aula_id.is_(None)
            )
        ).all()
        
        logger.info(f"Validando {len(restricciones_mantenimiento)} restricciones de mantenimiento")
        
        for restriccion in restricciones_mantenimiento:
            valor = restriccion.valor  # Dict ya validado por schema
            
            # Validar horarios de mantenimiento
            horarios_mantenimiento = valor.get('horarios_mantenimiento', [])
            
            for mantenimiento in horarios_mantenimiento:
                if _sesion_en_horario_bloqueado(sesion, mantenimiento):
                    # Obtener información del aula si está especificada
                    aula_nombre = "Instalaciones generales"
                    if restriccion.aula_id:
                        aula = db.query(Aula).filter(Aula.id == restriccion.aula_id).first()
                        aula_nombre = aula.nombre if aula else f"Aula ID {restriccion.aula_id}"
                    
                    tipo_mantenimiento = valor.get('tipo', 'Mantenimiento programado')
                    descripcion = valor.get('descripcion', 'Trabajos de mantenimiento')
                    
                    conflicto = ConflictoRestriccion(
                        tipo="mantenimiento_programado",
                        severidad="alto",
                        mensaje=f"Mantenimiento programado en {aula_nombre}. "
                               f"Tipo: {tipo_mantenimiento}. {descripcion}",
                        restriccion_violada=RestriccionOut.model_validate(restriccion),
                        detalles={
                            "aula_id": sesion.aula_id,
                            "aula_afectada": aula_nombre,
                            "dia_solicitado": sesion.dia.value,
                            "horario_solicitado": f"{sesion.hora_inicio}-{sesion.hora_fin}",
                            "tipo_mantenimiento": tipo_mantenimiento,
                            "descripcion": descripcion,
                            "prioridad_restriccion": restriccion.prioridad
                        }
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar conflictos de mantenimiento: {e}")
        conflictos.append(ConflictoRestriccion(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al detectar conflictos de mantenimiento: {str(e)}"
        ))
    
    return conflictos


def detectar_todos_conflictos_restricciones(db: Session, sesion: SesionCreate) -> List[ConflictoRestriccion]:
    """
    Función principal que ejecuta todas las validaciones de conflictos de restricciones.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista completa de todos los conflictos de restricción detectados
    """
    todos_conflictos = []
    
    logger.info(f"Iniciando detección de conflictos de restricciones para sesión: "
               f"Asignatura {sesion.asignatura_id}, Profesor {sesion.profesor_id}, "
               f"Aula {sesion.aula_id}, {sesion.dia} {sesion.hora_inicio}-{sesion.hora_fin}")
    
    # Ejecutar todas las validaciones de restricciones
    todos_conflictos.extend(detectar_conflictos_restriccion_profesor(db, sesion))
    todos_conflictos.extend(detectar_conflictos_restriccion_aula(db, sesion))
    todos_conflictos.extend(detectar_conflictos_bloqueo_temporal(db, sesion))
    todos_conflictos.extend(detectar_conflictos_mantenimiento(db, sesion))
    
    logger.info(f"Detección de restricciones completada. {len(todos_conflictos)} conflictos encontrados")
    
    return todos_conflictos


# ========================================
# FUNCIONES AUXILIARES
# ========================================

# Nota: Funciones auxiliares para validación específica de restricciones
# Se agregan según se implementen más tipos de validación

def _sesion_en_horario_bloqueado(sesion: SesionCreate, horario_restriccion: dict) -> bool:
    """
    Función helper que verifica si una sesión solapa con un horario restringido.
    
    Args:
        sesion: Datos de la sesión a verificar
        horario_restriccion: Diccionario con los datos del horario restringido
                            Debe contener: dia, inicio, fin
    
    Returns:
        True si la sesión solapa con la restricción
    """
    try:
        # Verificar que el horario de restricción tenga los campos necesarios
        if not all(key in horario_restriccion for key in ['dia', 'inicio', 'fin']):
            logger.warning(f"Horario de restricción incompleto: {horario_restriccion}")
            return False
        
        # Verificar si es el mismo día
        dia_restriccion = horario_restriccion['dia']
        if isinstance(dia_restriccion, str):
            # Convertir string a enum si es necesario
            try:
                dia_enum = DiaSemanaEnum(dia_restriccion.upper())
            except ValueError:
                logger.warning(f"Día inválido en restricción: {dia_restriccion}")
                return False
        else:
            dia_enum = dia_restriccion
            
        if sesion.dia != dia_enum:
            return False
        
        # Convertir horarios a objetos time para comparación
        hora_inicio_sesion = time.fromisoformat(sesion.hora_inicio)
        hora_fin_sesion = time.fromisoformat(sesion.hora_fin)
        
        hora_inicio_restriccion = time.fromisoformat(horario_restriccion['inicio'])
        hora_fin_restriccion = time.fromisoformat(horario_restriccion['fin'])
        
        # Verificar solape: dos intervalos se solapan si uno empieza antes de que termine el otro
        # y viceversa
        solapa = (hora_inicio_sesion < hora_fin_restriccion and 
                 hora_fin_sesion > hora_inicio_restriccion)
        
        return solapa
        
    except ValueError as e:
        logger.error(f"Error al procesar horarios - Sesión: {sesion.hora_inicio}-{sesion.hora_fin}, "
                    f"Restricción: {horario_restriccion.get('inicio', 'N/A')}-{horario_restriccion.get('fin', 'N/A')}. "
                    f"Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al verificar solape de horarios: {e}")
        return False