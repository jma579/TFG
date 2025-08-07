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
    """Tipos de restricciones posibles"""
    HORARIO_PROFESOR = "horario_profesor"
    DISPONIBILIDAD_AULA = "disponibilidad_aula"
    PREREQUISITO_ASIGNATURA = "prerequisito_asignatura"
    INCOMPATIBILIDAD = "incompatibilidad"
    CAPACIDAD_MAXIMA = "capacidad_maxima"
    EQUIPAMIENTO_ESPECIAL = "equipamiento_especial"
