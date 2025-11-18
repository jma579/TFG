from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import time

from backend.core.extraccion.common.entities import ExtractionMetadata, ParsingMetadata
from backend.constants.enums import (
    Periodo, DiaSemana, TipoGrupoDocente,
    ModalidadSesion, TipoRecurrencia, TipoAula
)


# =============================================================================
# RESULTADO DE EXTRACCIÓN (Output del extractor)
# =============================================================================

@dataclass(frozen=True)
class TablaHorario:
    """Representa una tabla individual de horario"""
    curso: str
    day_columns: List[str]  
    time_rows: List[str]   
    celdas: List[List[Optional[str]]]  
    mencion: Optional[str] = None
    pagina : Optional[int] = None

@dataclass(frozen=True)
class HorarioExtractionResult:
    """Resultado de la extracción completa del PDF"""
    titulo: str  # Título del documento (grado/cuatrimestre)
    tablas: List[TablaHorario]
    metadata: ExtractionMetadata


# =============================================================================
# RESULTADO DE PARSEO (Output del parser)
# =============================================================================

@dataclass
class Sesion:
    """Representa una sesión individual de clase."""
    asignatura: str
    aula: str
    dia: str 
    hora_inicio: time
    hora_fin: time
    tipo: Optional[str] = None 
    grupo: Optional[str] = None 

@dataclass
class Horario:
    """Representa un horario completo (una tabla)."""
    curso: str
    periodo: str
    sesiones: List[Sesion] = field(default_factory=list)
    mencion: Optional[str] = None
    pagina: Optional[int] = None

@dataclass
class ParsingResult:
    """Resultado del parseo de las tablas extraídas."""
    titulo: str
    horarios: List[Horario]
    extraction_metadata: ExtractionMetadata
    parsing_metadata: ParsingMetadata


# =============================================================================
# ENTIDADES NORMALIZADAS (Output del normalizador)
# =============================================================================

@dataclass
class NormalizedSesionHorarioData:
    """Sesión de horario normalizada, lista para persistir en BD.
    
    Esta entidad está pensada para mapearse 1:1 con una futura creación de:
    - GrupoDocente (a partir de asignatura + tipo_grupo + grupo_codigo + curso)
    - Aula (a partir de aula_nombre / aula_tipo)
    - Sesion (a partir de día, horas, modalidad, tipo_recurrencia)
    """
    asignatura_nombre: str
    grupo_codigo: str
    tipo_grupo: TipoGrupoDocente
    
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    
    aula_nombre: str
    aula_tipo: TipoAula
    
    modalidad: ModalidadSesion = ModalidadSesion.PRESENCIAL
    tipo_recurrencia: TipoRecurrencia = TipoRecurrencia.SEMANAL


@dataclass
class NormalizedHorarioTablaData:
    """Horario normalizado correspondiente a una tabla (curso/mención/página).
    
    Aglutina todas las sesiones normalizadas de una tabla de horario.
    """
    programa_nombre: str
    curso: int
    periodo: Periodo
    mencion: Optional[str]
    sesiones: List[NormalizedSesionHorarioData] = field(default_factory=list)
