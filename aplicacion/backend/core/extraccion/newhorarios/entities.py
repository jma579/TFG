from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from core.extraccion.common.entities import ExtractionMetadata, Warning


# =============================================================================
# RESULTADO DE EXTRACCIÓN (Output del extractor)
# =============================================================================

@dataclass(frozen=True)
class TablaHorario:
    """Representa una tabla individual de horario"""
    curso: str
    day_columns: List[str]  # ["Lunes", "Martes", ...]
    time_rows: List[str]    # ["08:00-09:00", "09:00-10:00", ...]
    celdas: List[List[Optional[str]]]  
    mencion: Optional[str] = None
    pagina : Optional[int] = None

@dataclass(frozen=True)
class HorarioExtractionResult:
    """Resultado de la extracción completa del PDF"""
    titulo: str  # Título del documento (grado/cuatrimestre)
    tablas: List[TablaHorario]
    metadata: ExtractionMetadata
