from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.extraccion.common.entities import ExtractionMetadata, ParsingMetadata
import time


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
    raw_json: dict