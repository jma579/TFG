"""
Enumeraciones para el sistema de detección de conflictos en horarios académicos.

Este módulo define todos los enums utilizados en los modelos de SQLAlchemy
para garantizar consistencia y validación de datos.
"""

from enum import Enum

# ============================
# Catálogo Académico
# ============================

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


# ============================
# Recursos e Infraestructura
# ============================

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


# ============================
# Docencia y Planificación
# ============================

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
    PUNTUAL = "puntual"  # Sesión única en fecha específica


class DiaSemana(str, Enum):
    """Días de la semana."""
    LUNES = "lunes"
    MARTES = "martes"
    MIERCOLES = "miercoles"
    JUEVES = "jueves"
    VIERNES = "viernes"
    SABADO = "sabado"
    DOMINGO = "domingo"


# ============================
# Restricciones
# ============================

class TipoRestriccion(str, Enum):
    """Tipos de restricciones de horarios."""
    NO_DISPONIBLE = "no_disponible"
    PREFERENCIA_NO = "preferencia_no"
    PREFERENCIA_SI = "preferencia_si"
    MANTENIMIENTO = "mantenimiento"
    RESERVADO = "reservado"
    CAPACIDAD_REDUCIDA = "capacidad_reducida"


class DurezaRestriccion(str, Enum):
    """Niveles de dureza de las restricciones."""
    SUAVE = "suave"          # Preferencia, puede violarse si es necesario
    DURA = "dura"            # Restricción fuerte, difícil de violar
    CRITICA = "critica"      # No se puede violar bajo ninguna circunstancia


# ============================
# Detección de Conflictos
# ============================

class TipoConflicto(str, Enum):
    """Tipos de conflictos detectados."""
    SOLAPAMIENTO_PROFESOR = "solapamiento_profesor"
    SOLAPAMIENTO_AULA = "solapamiento_aula"
    VIOLACION_RESTRICCION = "violacion_restriccion"
    CAPACIDAD_INSUFICIENTE = "capacidad_insuficiente"
    MODALIDAD_INCOMPATIBLE = "modalidad_incompatible"
    RECURSOS_INSUFICIENTES = "recursos_insuficientes"
    HORARIO_INVALIDO = "horario_invalido"


class SeveridadConflicto(str, Enum):
    """Niveles de severidad de los conflictos."""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class EstadoConflicto(str, Enum):
    """Estados de los conflictos en el sistema."""
    ABIERTO = "abierto"
    EN_REVISION = "en_revision"
    RESUELTO = "resuelto"
    IGNORADO = "ignorado"
    FALSO_POSITIVO = "falso_positivo"


# ============================
# Utilidades y Helpers
# ============================

def get_enum_values(enum_class: type[Enum]) -> list[str]:
    """
    Obtiene todos los valores de un enum como lista.
    
    Args:
        enum_class: Clase del enum
        
    Returns:
        list[str]: Lista con todos los valores del enum
    """
    return [item.value for item in enum_class]


def get_enum_choices(enum_class: type[Enum]) -> list[tuple[str, str]]:
    """
    Obtiene las opciones de un enum para formularios.
    
    Args:
        enum_class: Clase del enum
        
    Returns:
        list[tuple[str, str]]: Lista de tuplas (value, label) para formularios
    """
    return [(item.value, item.value.replace('_', ' ').title()) for item in enum_class]


def validate_enum_value(enum_class: type[Enum], value: str) -> bool:
    """
    Valida si un valor pertenece a un enum específico.
    
    Args:
        enum_class: Clase del enum
        value: Valor a validar
        
    Returns:
        bool: True si el valor es válido, False en caso contrario
    """
    return value in get_enum_values(enum_class)


# ============================
# Constantes de mapeo
# ============================

# Mapeo de días de semana a números (útil para ordenación y cálculos)
DIA_SEMANA_TO_NUMBER = {
    DiaSemana.LUNES: 1,
    DiaSemana.MARTES: 2,
    DiaSemana.MIERCOLES: 3,
    DiaSemana.JUEVES: 4,
    DiaSemana.VIERNES: 5,
    DiaSemana.SABADO: 6,
    DiaSemana.DOMINGO: 0,  # Domingo = 0 (estándar ISO)
}

# Mapeo inverso: número a día de semana
NUMBER_TO_DIA_SEMANA = {v: k for k, v in DIA_SEMANA_TO_NUMBER.items()}

# Prioridades de severidad (para ordenación)
SEVERIDAD_PRIORITY = {
    SeveridadConflicto.BAJA: 1,
    SeveridadConflicto.MEDIA: 2,
    SeveridadConflicto.ALTA: 3,
    SeveridadConflicto.CRITICA: 4,
}

# Colores asociados a severidades (para UI)
SEVERIDAD_COLORS = {
    SeveridadConflicto.BAJA: "#28a745",      # Verde
    SeveridadConflicto.MEDIA: "#ffc107",     # Amarillo
    SeveridadConflicto.ALTA: "#fd7e14",      # Naranja
    SeveridadConflicto.CRITICA: "#dc3545",   # Rojo
}

# Estados que indican conflicto activo
ESTADOS_CONFLICTO_ACTIVOS = {
    EstadoConflicto.ABIERTO,
    EstadoConflicto.EN_REVISION,
}

# Estados que indican conflicto cerrado
ESTADOS_CONFLICTO_CERRADOS = {
    EstadoConflicto.RESUELTO,
    EstadoConflicto.IGNORADO,
    EstadoConflicto.FALSO_POSITIVO,
}
