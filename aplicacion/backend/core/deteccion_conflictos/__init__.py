"""
Paquete de detección de conflictos en horarios académicos.

Este paquete proporciona un sistema modular y completo para la detección
de diferentes tipos de conflictos en la programación de horarios académicos.

Módulos disponibles:
- conflictos_temporales: Detecta solapamientos de horario (profesor, aula, asignatura)
- conflictos_restricciones: Valida restricciones de disponibilidad y mantenimiento
- conflictos_capacidad: Verifica límites de capacidad de aulas vs. estudiantes
- conflictos_compatibilidad: Analiza compatibilidad académica (curso, mención, grado)

Uso típico:
    from core.deteccion_conflictos import detectar_todos_los_conflictos
    
    conflictos = detectar_todos_los_conflictos(db, sesion_nueva)
"""

# Imports de estructuras de datos (dataclasses)
from .conflictos_temporales import ConflictoTemporal
from .conflictos_restricciones import ConflictoRestriccion
from .conflictos_capacidad import ConflictoCapacidad
from .conflictos_compatibilidad import ConflictoCompatibilidad

# Imports de funciones principales por módulo
from .conflictos_temporales import (
    detectar_todos_conflictos_temporales,
    detectar_solape_profesor,
    detectar_solape_aula, 
    detectar_solape_asignatura
)

from .conflictos_restricciones import (
    detectar_todos_conflictos_restricciones,
    detectar_conflictos_restriccion_profesor,
    detectar_conflictos_restriccion_aula,
    detectar_conflictos_bloqueo_temporal,
    detectar_conflictos_mantenimiento
)

from .conflictos_capacidad import (
    detectar_todos_conflictos_capacidad,
    detectar_conflictos_capacidad_aula
)

from .conflictos_compatibilidad import (
    detectar_todos_conflictos_compatibilidad,
    detectar_conflictos_curso_cuatrimestre,
    detectar_conflictos_mencion,
    detectar_conflictos_grado_compartido,
    detectar_conflictos_dependencias_curriculares
)

# Exponer todas las clases de conflictos para fácil acceso
__all__ = [
    # Dataclasses
    'ConflictoTemporal',
    'ConflictoRestriccion', 
    'ConflictoCapacidad',
    'ConflictoCompatibilidad',
    
    # Funciones principales (orquestadores)
    'detectar_todos_conflictos_temporales',
    'detectar_todos_conflictos_restriccion',
    'detectar_todos_conflictos_capacidad',
    'detectar_todos_conflictos_compatibilidad',
    
    # Funciones específicas temporales
    'detectar_solape_profesor',
    'detectar_solape_aula',
    'detectar_solape_asignatura',
    
    # Funciones específicas restricciones
    'detectar_conflictos_restriccion_profesor',
    'detectar_conflictos_restriccion_aula',
    'detectar_conflictos_bloqueo_temporal',
    'detectar_conflictos_mantenimiento',
    
    # Funciones específicas capacidad
    'detectar_conflictos_capacidad_aula',
    
    # Funciones específicas compatibilidad
    'detectar_conflictos_curso_cuatrimestre',
    'detectar_conflictos_mencion',
    'detectar_conflictos_grado_compartido',
    'detectar_conflictos_dependencias_curriculares'
]


# ========================================
# FUNCIÓN ORQUESTADORA PRINCIPAL
# ========================================

def detectar_todos_los_conflictos(db, sesion, sesion_id_ignorar=None):
    """
    Función orquestadora principal que ejecuta TODOS los tipos de detección de conflictos.
    
    Esta función centraliza la ejecución de todas las validaciones disponibles
    y devuelve una estructura unificada con todos los conflictos encontrados.
    
    Args:
        db: Sesión de base de datos SQLAlchemy
        sesion: Objeto SesionCreate con los datos de la sesión a validar
        sesion_id_ignorar: Optional[int] - ID de sesión a excluir (útil para updates)
    
    Returns:
        Dict[str, List] - Diccionario con los conflictos organizados por tipo:
        {
            'temporales': [...],
            'restricciones': [...], 
            'capacidad': [...],
            'compatibilidad': [...]
        }
    
    Example:
        >>> from core.deteccion_conflictos import detectar_todos_los_conflictos
        >>> conflictos = detectar_todos_los_conflictos(db, nueva_sesion)
        >>> print(f"Conflictos temporales: {len(conflictos['temporales'])}")
        >>> print(f"Conflictos de capacidad: {len(conflictos['capacidad'])}")
    """
    try:
        # Ejecutar todas las detecciones en paralelo
        conflictos_resultado = {
            'temporales': detectar_todos_conflictos_temporales(db, sesion, sesion_id_ignorar),
            'restricciones': detectar_todos_conflictos_restricciones(db, sesion, sesion_id_ignorar), 
            'capacidad': detectar_todos_conflictos_capacidad(db, sesion),
            'compatibilidad': detectar_todos_conflictos_compatibilidad(db, sesion, sesion_id_ignorar)
        }
        
        # Calcular estadísticas
        total_conflictos = sum(len(conflictos) for conflictos in conflictos_resultado.values())
        
        # Log de resumen
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Detección completa: {total_conflictos} conflictos totales encontrados")
        logger.debug(f"Detalle: {dict((k, len(v)) for k, v in conflictos_resultado.items())}")
        
        return conflictos_resultado
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en detección principal de conflictos: {e}")
        # Retornar estructura vacía en caso de error
        return {
            'temporales': [],
            'restricciones': [],
            'capacidad': [],
            'compatibilidad': []
        }
