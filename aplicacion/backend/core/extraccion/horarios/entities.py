"""
Estructuras (dataclasses) del sistema de horarios.
Usadas tanto por el extractor (Camelot) como por el parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal

# -----------------------------------------------------------------------------
# Tipos/metadatos compartidos (referencia suave a /common/entities.py)
# -----------------------------------------------------------------------------
from core.extraccion.common.entities import ExtractionMetadata, ParsingMetadata


# -----------------------------------------------------------------------------
# Aliases y literales
# -----------------------------------------------------------------------------
ModalidadLiteral = Literal["teoria", "prácticas de laboratorio", "prácticas de aula"]
PageNumber = int

# -----------------------------------------------------------------------------
# Estructura de avisos con severidad
# -----------------------------------------------------------------------------
@dataclass
class Warning:
    message: str
    severity: Literal["severe", "moderate", "minor"]


# -----------------------------------------------------------------------------
# Estructuras que devuelve el EXTRACTOR
# -----------------------------------------------------------------------------
@dataclass
class RawTable:
    """
    Representación cruda de una tabla extraída por Camelot.
    Es un eco para trazabilidad: lo que Camelot entregó (limpieza mínima de espacios).
    """
    page: PageNumber
    grid: List[List[str]]  # matriz filas x columnas, sin interpretar

@dataclass
class CleanTable:
    """
    Tabla limpia y normalizada, alineada para el parser.
    - header_days: días canónicos (L->V)
    - time_axis: marcas de tiempo HH:MM dentro de la ventana objetivo
    - cells: matriz [len(time_axis)] x [len(header_days)], strings normalizados
    """
    page: PageNumber
    header_days: List[str]
    time_axis: List[str]
    cells: List[List[str]]

@dataclass
class ExtractionResult:
    """
    Resultado completo del flujo extractor: agregado de tablas + trazabilidad.
    """
    titulacion: str
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
    aula: Optional[str]
    hora_inicio: str  # "HH:MM"
    hora_fin: str     # "HH:MM"
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