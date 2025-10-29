"""
Estructuras (dataclasses) del sistema de horarios.
Usadas tanto por el extractor (Camelot) como por el parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal, Tuple

# -----------------------------------------------------------------------------
# Tipos/metadatos compartidos (referencia suave a /common/entities.py)
# -----------------------------------------------------------------------------
from core.extraccion.common.entities import ExtractionMetadata, ParsingMetadata


# -----------------------------------------------------------------------------
# Aliases y literales
# -----------------------------------------------------------------------------
ModalidadLiteral = Literal["teoria", "prácticas de laboratorio", "prácticas de aula"]
PageNumber = int


SourceLiteral = Literal["pdf", "excel"]


# -----------------------------------------------------------------------------
# Estructuras que devuelve el EXTRACTOR
# -----------------------------------------------------------------------------
@dataclass
class RawTable:
    """
    Eco de la tabla original del bloque (6 columnas: HORA + L..V) para trazabilidad.
    Es formato neutral (sirve tanto para Excel como para PDF).
    """
    data: List[List[str]]                      # matriz con cabecera y filas crudas
    source: SourceLiteral                      # "excel" | "pdf"

    # Trazabilidad (uno u otro según origen)
    sheet: Optional[str] = None                # Excel
    page: Optional[int] = None                 # PDF

    # Info del bloque detectado (útil para depurar)
    lane_index: Optional[int] = None
    block_id: Optional[str] = None
    header_row: Optional[int] = None
    data_start_row: Optional[int] = None
    data_end_row: Optional[int] = None
    time_col: Optional[int] = None
    day_cols: Optional[List[int]] = None

    # Precalculos para la fase clean
    row_hour_ranges: Optional[List[Optional[Tuple[str, str]]]] = None
    merge_span_matrix: Optional[List[List[int]]] = None

    # Contexto
    titulacion: Optional[str] = None
    curso: Optional[str] = None
    mencion: Optional[str] = None

    # Cualquier cosa adicional del extractor
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CleanTable:
    """
    Tabla normalizada para el parser:
    - days = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES"]
    - time_axis = nodos HH:MM cada 30' desde 08:00 a 20:30
    - cells = matriz de intervalos (len(time_axis)-1) × 5 con texto crudo
    """
    time_axis: List[str]
    days: List[str]
    cells: List[List[str]]

    source: SourceLiteral                      # "excel" | "pdf"
    sheet: Optional[str] = None
    page: Optional[int] = None

    lane_index: Optional[int] = None
    block_id: Optional[str] = None

    # Enriquecimiento contextual (si lo tienes en el bloque)
    titulacion: Optional[str] = None
    curso: Optional[str] = None
    mencion: Optional[str] = None

    # Marcadores de continuidad por intervalo (2=inicio,1=normal,0=continuación)
    row_spans: Optional[List[int]] = None

@dataclass
class ExtractionResult:
    """
    Resultado completo del flujo extractor: agregado de tablas + trazabilidad.
    """
    #titulacion: str
    clean_tables: List[CleanTable]  # lo que consume el parser (limpio)
    raw_tables: List[RawTable]      # lo que llegó del extractor (crudo)
    extraccion_metadata: ExtractionMetadata


# -----------------------------------------------------------------------------
# Estructuras que produce el PARSER (salida final)
# -----------------------------------------------------------------------------
@dataclass
class Session:
    """
    Sesión académica consolidada (una asignatura en un bloque horariodía).
    """
    asignatura: str
    aula: str
    hora_inicio: str  # "HH:MM"
    hora_fin: str     # "HH:MM"
    dia: str          # día canónico ("LUNES", ...)
    modalidad: ModalidadLiteral
    grupo: Optional[str] = None  # p. ej., "PL1", "PA2"; en teoría suele ser None

@dataclass
class Schedule:
    """
    Resultado completo del flujo horarios: agregado de sesiones + trazabilidad.
    """
    titulacion: str
    sesiones: List[Session]

    # Trazabilidad y depuración
    raw_tables: List[RawTable]     # lo que llegó del extractor (crudo)
    clean_tables: List[CleanTable] # lo que consume el parser (limpio)

    # Metadatos
    extraccion_metadata: ExtractionMetadata
    parse_metadata: ParsingMetadata