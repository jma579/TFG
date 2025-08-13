"""
Módulo para la detección de conflictos de capacidad en horarios académicos.

Este módulo valida que el número de estudiantes asignados a una sesión
no exceda la capacidad máxima del aula asignada.

Validaciones incluidas:
- Capacidad máxima del aula vs número de estudiantes matriculados
- Consideración de grupos de laboratorio y problemas con menor tamaño
- Validación de aforo para diferentes tipos de sesión

Nota: Solo valida capacidad numérica. Los conflictos de equipamiento
y compatibilidad van en otros módulos específicos.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

# SQLAlchemy imports
from sqlalchemy.orm import Session

# Imports de modelos
from models.sesion import Sesion
from models.aula import Aula
from models.asignatura import Asignatura

# Imports de schemas
from schemas.sesion import SesionCreate
from schemas.aula import AulaOut

# Configuración de logging
logger = logging.getLogger(__name__)


@dataclass
class ConflictoCapacidad:
    """Estructura para representar un conflicto de capacidad detectado"""
    tipo: str
    severidad: str
    mensaje: str
    aula_capacidad: Optional[int] = None
    estudiantes_requeridos: Optional[int] = None
    exceso_estudiantes: Optional[int] = None
    aula_info: Optional[AulaOut] = None
    detalles: Optional[Dict[str, Any]] = None


# ========================================
# FUNCIONES DE DETECCIÓN DE CONFLICTOS
# ========================================


def detectar_conflictos_capacidad_aula(db: Session, sesion: SesionCreate) -> List[ConflictoCapacidad]:
    """
    Detecta si el aula tiene capacidad suficiente para el número de estudiantes de la sesión.
    
    Valida que:
    - El número de estudiantes matriculados no exceda la capacidad del aula
    - Se considere el tipo de grupo (magistral, laboratorio, problemas)
    - Se proporcione información clara sobre el exceso de capacidad
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos de capacidad encontrados
    """
    conflictos = []
    
    try:
        # Obtener información del aula
        aula = db.query(Aula).filter(Aula.id == sesion.aula_id).first()
        if not aula:
            conflictos.append(ConflictoCapacidad(
                tipo="aula_no_encontrada",
                severidad="critico",
                mensaje=f"No se encontró el aula con ID {sesion.aula_id}",
                detalles={
                    "aula_id": sesion.aula_id,
                    "sesion_id": getattr(sesion, 'id', 'nueva')
                }
            ))
            return conflictos
        
        # Obtener información de la asignatura para determinar número de estudiantes
        asignatura = db.query(Asignatura).filter(Asignatura.id == sesion.asignatura_id).first()
        if not asignatura:
            conflictos.append(ConflictoCapacidad(
                tipo="asignatura_no_encontrada",
                severidad="critico",
                mensaje=f"No se encontró la asignatura con ID {sesion.asignatura_id}",
                detalles={
                    "asignatura_id": sesion.asignatura_id,
                    "aula_id": sesion.aula_id
                }
            ))
            return conflictos
        
        # Determinar número de estudiantes según tipo de sesión
        numero_estudiantes = _determinar_numero_estudiantes(asignatura, sesion)
        
        if numero_estudiantes is None:
            logger.warning(f"No se pudo determinar el número de estudiantes para "
                          f"asignatura {sesion.asignatura_id}, tipo {sesion.tipo}")
            return conflictos
        
        # Verificar capacidad del aula
        capacidad_aula = aula.capacidad
        if capacidad_aula is None:
            conflictos.append(ConflictoCapacidad(
                tipo="capacidad_aula_no_definida",
                severidad="alto",
                mensaje=f"El aula {aula.nombre} no tiene capacidad definida",
                aula_info=AulaOut.model_validate(aula),
                estudiantes_requeridos=numero_estudiantes,
                detalles={
                    "aula_id": aula.id,
                    "aula_nombre": aula.nombre,
                    "estudiantes_requeridos": numero_estudiantes,
                    "tipo_sesion": sesion.tipo
                }
            ))
            return conflictos
        
        # Validar si excede la capacidad
        if numero_estudiantes > capacidad_aula:
            exceso = numero_estudiantes - capacidad_aula
            
            conflicto = ConflictoCapacidad(
                tipo="capacidad_excedida",
                severidad="critico",
                mensaje=f"El aula {aula.nombre} no tiene capacidad suficiente. "
                       f"Requeridos: {numero_estudiantes} estudiantes, "
                       f"Capacidad: {capacidad_aula}. Exceso: {exceso} estudiantes.",
                aula_capacidad=capacidad_aula,
                estudiantes_requeridos=numero_estudiantes,
                exceso_estudiantes=exceso,
                aula_info=AulaOut.model_validate(aula),
                detalles={
                    "aula_id": aula.id,
                    "aula_nombre": aula.nombre,
                    "aula_tipo": aula.tipo.value if aula.tipo else "No definido",
                    "capacidad_maxima": capacidad_aula,
                    "estudiantes_requeridos": numero_estudiantes,
                    "exceso_estudiantes": exceso,
                    "porcentaje_exceso": round((exceso / capacidad_aula) * 100, 2),
                    "tipo_sesion": sesion.tipo,
                    "asignatura_id": sesion.asignatura_id,
                    "asignatura_nombre": asignatura.nombre
                }
            )
            conflictos.append(conflicto)
            
        logger.info(f"Validación de capacidad completada - Aula: {aula.nombre} "
                   f"(Capacidad: {capacidad_aula}), Estudiantes: {numero_estudiantes}, "
                   f"Conflictos: {len(conflictos)}")
                   
    except Exception as e:
        logger.error(f"Error al detectar conflictos de capacidad: {e}")
        conflictos.append(ConflictoCapacidad(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al validar capacidad del aula: {str(e)}",
            detalles={
                "aula_id": sesion.aula_id,
                "asignatura_id": sesion.asignatura_id,
                "error": str(e)
            }
        ))
    
    return conflictos


def detectar_todos_conflictos_capacidad(db: Session, sesion: SesionCreate) -> List[ConflictoCapacidad]:
    """
    Función principal que ejecuta todas las validaciones de conflictos de capacidad.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista completa de todos los conflictos de capacidad detectados
    """
    logger.info(f"Iniciando detección de conflictos de capacidad para sesión: "
               f"Asignatura {sesion.asignatura_id}, Aula {sesion.aula_id}, "
               f"Tipo: {sesion.tipo}")
    
    # Por ahora solo validamos capacidad del aula
    # En el futuro se pueden agregar más validaciones de capacidad
    conflictos = detectar_conflictos_capacidad_aula(db, sesion)
    
    logger.info(f"Detección de capacidad completada. {len(conflictos)} conflictos encontrados")
    
    return conflictos


# ========================================
# FUNCIONES AUXILIARES
# ========================================


def _determinar_numero_estudiantes(asignatura: Asignatura, sesion: SesionCreate) -> Optional[int]:
    """
    Determina el número de estudiantes para una sesión según su tipo.
    
    Args:
        asignatura: Objeto asignatura con la información de matriculados
        sesion: Datos de la sesión
    
    Returns:
        Número de estudiantes o None si no se puede determinar
    """
    try:
        # Para sesiones magistrales, usar todos los estudiantes matriculados
        if sesion.tipo.lower() in ['magistral', 'teoria', 'teorica']:
            return asignatura.estudiantes_matriculados
        
        # Para laboratorios y problemas, usar grupos más pequeños
        elif sesion.tipo.lower() in ['laboratorio', 'lab', 'practica', 'practicas']:
            # Usar el tamaño del grupo de laboratorio si está definido
            if hasattr(asignatura, 'tamano_grupo_laboratorio') and asignatura.tamano_grupo_laboratorio:
                return asignatura.tamano_grupo_laboratorio
            # Si no, asumir grupos de laboratorio más pequeños (ej: 1/3 del total)
            return max(1, asignatura.estudiantes_matriculados // 3)
        
        elif sesion.tipo.lower() in ['problemas', 'ejercicios', 'seminario']:
            # Usar el tamaño del grupo de problemas si está definido
            if hasattr(asignatura, 'tamano_grupo_problemas') and asignatura.tamano_grupo_problemas:
                return asignatura.tamano_grupo_problemas
            # Si no, asumir grupos medianos (ej: 1/2 del total)
            return max(1, asignatura.estudiantes_matriculados // 2)
        
        else:
            # Para tipos no reconocidos, usar el total como medida conservadora
            logger.warning(f"Tipo de sesión no reconocido: {sesion.tipo}. "
                          f"Usando total de estudiantes matriculados.")
            return asignatura.estudiantes_matriculados
            
    except Exception as e:
        logger.error(f"Error al determinar número de estudiantes: {e}")
        return None
