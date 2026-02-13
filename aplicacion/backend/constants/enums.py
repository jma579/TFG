"""
Enumeraciones para el sistema de detección de conflictos en horarios académicos.

Este módulo define todos los enums utilizados en los modelos de SQLAlchemy
para garantizar consistencia y validación de datos.
"""

from enum import Enum
from datetime import time


# Horario Lectivo del Centro
HORA_APERTURA_CENTRO = time(8, 0)
HORA_CIERRE_CENTRO = time(21, 0)


# Catálogo Académico

class TipoPrograma(str, Enum):
    """Tipos de programas académicos."""
    GRADO = "grado"
    MASTER = "master"
    DOCTORADO = "doctorado"
    CURSO_ESPECIALIZATION = "curso_especializacion"


class Periodo(str, Enum):
    """Períodos académicos en los que se imparte una asignatura."""
    ANUAL = "anual"
    PRIMER_SEMESTRE = "primer_semestre"
    SEGUNDO_SEMESTRE = "segundo_semestre"
    PRIMER_CUATRIMESTRE = "primer_cuatrimestre"
    SEGUNDO_CUATRIMESTRE = "segundo_cuatrimestre"
    TERCER_CUATRIMESTRE = "tercer_cuatrimestre"
    CUARTO_CUATRIMESTRE = "cuarto_cuatrimestre"


class ModalidadAsignatura(str, Enum):
    """Modalidades de impartición de asignaturas."""
    PRESENCIAL = "presencial"
    ONLINE = "online"
    SEMIPRESENCIAL = "semipresencial"
    HIBRIDA = "hibrida"


class Idioma(str, Enum):
    """Idiomas en los que se puede impartir una asignatura."""
    ESPAÑOL = "español"
    INGLES = "ingles"
    FRANCES = "frances"
    ALEMAN = "aleman"
    ITALIANO = "italiano"
    PORTUGUES = "portugues"
    CATALAN = "catalan"
    EUSKERA = "euskera"
    GALLEGO = "gallego"


# Recursos e Infraestructura

class TipoAula(str, Enum):
    """Tipos de aulas disponibles."""
    TEORICA = "teorica"
    LABORATORIO = "laboratorio"
    INFORMATICA = "informatica"
    SEMINARIO = "seminario"
    TALLER = "taller"
    AUDITORIO = "auditorio"
    BIBLIOTECA = "biblioteca"
    GIMNASIO = "gimnasio"
    VIRTUAL = "virtual"


# Docencia y Planificación

class ModalidadSesion(str, Enum):
    """Modalidades de las sesiones de clase."""
    PRESENCIAL = "presencial"
    ONLINE = "online"
    HIBRIDA = "hibrida"


class TipoGrupoDocente(str, Enum):
    """Tipos de grupos docentes."""
    TEORIA = "teoria"
    PRACTICA = "practica"
    LABORATORIO = "laboratorio"
    SEMINARIO = "seminario"
    TALLER = "taller"
    TUTORIA = "tutoria"
    EXAMEN = "examen"


class TipoRecurrencia(str, Enum):
    """Tipos de recurrencia para las sesiones."""
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    PUNTUAL = "puntual"


class DiaSemana(str, Enum):
    """Días de la semana."""
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"


class TipoAsignatura(str, Enum):
    """Tipos de asignaturas."""
    OBLIGATORIA = "obligatoria"
    OPTATIVA = "optativa"
    BASICA = "basica"


# Conciliación Docente y Restricciones

class TipoConciliacion(str, Enum):
    """Tipos de conciliaciones docentes."""
    ENTRADA_TARDIA = "entrada_tardia"
    SALIDA_TEMPRANA = "salida_temprana"
    MIXTA = "mixta"


HORAS_CONCILIACION_NORMAL = 2
HORAS_CONCILIACION_MIXTA = 1


class TipoRestriccion(str, Enum):
    """Tipos de restricciones docentes."""
    pass


class DurezaRestriccion(str, Enum):
    """Niveles de dureza de las restricciones."""
    pass


# Detección de Conflictos

class TipoConflicto(str, Enum):
    """Tipos de conflictos detectados."""
    SOLAPAMIENTO_AULA = "solapamiento_aula"
    SOLAPAMIENTO_PROFESOR = "solapamiento_profesor"
    SOLAPAMIENTO_GRUPO = "solapamiento_grupo"
    INTERFERENCIA_CONCILIACION = "interferencia_conciliacion"


class SeveridadConflicto(str, Enum):
    """Niveles de severidad de los conflictos."""
    CRITICO = "critico"
    NO_BLOQUEANTE = "no_bloqueante"
    LEVE = "leve"


class EstadoConflicto(str, Enum):
    """Estados del ciclo de vida del conflicto."""
    POR_REVISAR = "por_revisar"
    SOLUCIONADO = "solucionado"


# Utilidades y Helpers

def get_enum_values(enum_class: type[Enum]) -> list[str]:
    """Obtiene todos los valores de un enum como lista."""
    return [item.value for item in enum_class]


def get_enum_choices(enum_class: type[Enum]) -> list[tuple[str, str]]:
    """Obtiene las opciones de un enum para formularios."""
    return [(item.value, item.value.replace('_', ' ').title()) for item in enum_class]


def validate_enum_value(enum_class: type[Enum], value: str) -> bool:
    """Valida si un valor pertenece a un enum específico."""
    return value in get_enum_values(enum_class)


# Constantes de mapeo

DIA_SEMANA_TO_NUMBER = {
    DiaSemana.LUNES: 1,
    DiaSemana.MARTES: 2,
    DiaSemana.MIERCOLES: 3,
    DiaSemana.JUEVES: 4,
    DiaSemana.VIERNES: 5,
    DiaSemana.SABADO: 6,
    DiaSemana.DOMINGO: 0,
}

NUMBER_TO_DIA_SEMANA = {v: k for k, v in DIA_SEMANA_TO_NUMBER.items()}

SEVERIDAD_COLORS = {
    SeveridadConflicto.CRITICO: "#dc3545",
    SeveridadConflicto.NO_BLOQUEANTE: "#fd7e14",
    SeveridadConflicto.LEVE: "#ffc107",
}