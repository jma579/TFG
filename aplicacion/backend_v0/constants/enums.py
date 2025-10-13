from enum import Enum

# ---------- ENUMS PARA BASE DE DATOS (SQLAlchemy Models) ----------

class TipoPrograma(Enum):
    """Tipos de programas académicos"""
    GRADO = "GRADO"
    MASTER = "MASTER"

class Periodo(Enum):
    """Períodos académicos para asignaturas"""
    CUAT1 = "CUAT1"
    CUAT2 = "CUAT2"
    BIM1 = "BIM1"
    BIM2 = "BIM2"
    BIM3 = "BIM3"
    BIM4 = "BIM4"

class ModalidadAsignatura(Enum):
    """Modalidades de impartición de asignaturas"""
    PRESENCIAL = "PRESENCIAL"
    HIBRIDA = "HIBRIDA"
    ONLINE = "ONLINE"

class Idioma(Enum):
    """Idiomas disponibles para asignaturas"""
    ESPAÑOL = "ESPAÑOL"
    INGLÉS = "INGLÉS"
    FRANCÉS = "FRANCÉS"
    ALEMÁN = "ALEMÁN"
    ITALIANO = "ITALIANO"

class TipoAula(Enum):
    """Tipos de aulas para base de datos"""
    AULA = "AULA"
    LABORATORIO = "LABORATORIO"
    MAGNA = "MAGNA"
    SEMINARIO = "SEMINARIO"

class ModalidadSesion(Enum):
    """Modalidades de sesiones docentes"""
    TE = "TE"  # Teoría
    PA = "PA"  # Prácticas de Aula
    PL = "PL"  # Prácticas de Laboratorio
    CL = "CL"  # Clases

class TipoGrupoDocente(Enum):
    """Tipos de grupos docentes"""
    TEORIA = "TEORIA"
    PRACTICAS = "PRACTICAS"
    OTRO = "OTRO"

class TipoRecurrencia(Enum):
    """Tipos de recurrencia para sesiones"""
    SEMANAL = "SEMANAL"
    FECHADA = "FECHADA"

class DiaSemana(Enum):
    """Días de la semana para base de datos"""
    LUN = "LUN"
    MAR = "MAR"
    MIE = "MIE"
    JUE = "JUE"
    VIE = "VIE"
    SAB = "SAB"
    DOM = "DOM"

class TipoRestriccion(Enum):
    """Tipos de restricciones para base de datos"""
    NO_DISPONIBLE = "NO_DISPONIBLE"
    BLOQUEO_FECHAS = "BLOQUEO_FECHAS"
    CAPACIDAD_MAXIMA = "CAPACIDAD_MAXIMA"
    PREFERENCIA_FRANJA = "PREFERENCIA_FRANJA"
    REGLA_PERSONALIZADA = "REGLA_PERSONALIZADA"

class DurezaRestriccion(Enum):
    """Dureza de las restricciones"""
    DURA = "DURA"
    BLANDA = "BLANDA"

class SeveridadConflicto(Enum):
    """Niveles de severidad de conflictos"""
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"

class TipoConflicto(Enum):
    """Tipos de conflictos detectables"""
    SOLAPE_AULA = "SOLAPE_AULA"
    SOLAPE_PROFESOR = "SOLAPE_PROFESOR"
    FUERA_DISPONIBILIDAD = "FUERA_DISPONIBILIDAD"
    CAPACIDAD = "CAPACIDAD"
    REGLA_INFRINGIDA = "REGLA_INFRINGIDA"

class EstadoConflicto(Enum):
    """Estados de resolución de conflictos"""
    ABIERTO = "ABIERTO"
    EN_REVISION = "EN_REVISION"
    RESUELTO = "RESUELTO"
    IGNORADO = "IGNORADO"
