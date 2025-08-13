from enum import Enum

class DiaSemanaEnum(str, Enum):
    """Días de la semana para las sesiones"""
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"

class CuatrimestreEnum(str, Enum):
    """Cuatrimestres académicos"""
    PRIMERO = "1"
    SEGUNDO = "2"
    ANUAL = "anual"

class TipoAulaEnum(str, Enum):
    """Tipos de aulas disponibles"""
    TEORIA = "teoria"
    LABORATORIO = "laboratorio"
    INFORMATICA = "informatica"
    SEMINARIO = "seminario"
    MAGNA = "magna"

class TipoRestriccionEnum(str, Enum):
    """Tipos de restricciones de disponibilidad temporal"""
    HORARIO_PROFESOR = "horario_profesor"           # Días/horas no disponibles del profesor
    DISPONIBILIDAD_AULA = "disponibilidad_aula"     # Aula no disponible por reservas/uso específico
    BLOQUEO_TEMPORAL = "bloqueo_temporal"           # Bloqueos específicos de horarios
    MANTENIMIENTO = "mantenimiento"                 # Mantenimiento programado de aulas/equipos
