"""
Entidades específicas para el sistema de extracción y parsing de PDFs académicos.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List

__all__ = [
    "ExtractionQuality", "ProcessingStatus", "ErrorType",
    "ExtractionMetadata", "ExtractionResult",
    "SubjectCodeHit",
]

# Enums del proceso de extracción
class ExtractionQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"

class ProcessingStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    LOW_QUALITY = "low_quality"   # Extraído pero calidad insuficiente

class ErrorType(str, Enum):
    FILE_NOT_FOUND = "file_not_found"
    INVALID_PDF = "invalid_pdf"
    PROCESSING_TIMEOUT = "processing_timeout"
    NO_EMBEDDED_TEXT = "no_embedded_text"
    UNKNOWN_ERROR = "unknown_error"

# Metadatos emitidos por pdf_extractor
@dataclass()
class ExtractionMetadata:
    quality: ExtractionQuality
    confidence: float
    status: ProcessingStatus
    processing_time_seconds: float
    page_count: int
    file_size_mb: float
    has_embedded_text: bool
    char_count: int
    word_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # Diagnóstico útil
    pages_with_text: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



class ParserError(Exception):
    """Error de parsing (distinto a errores de extracción)."""
    pass


@dataclass
class ParsingMetadata:
    parser_name: str
    parser_version: str
    parse_timestamp: str
    parse_duration: float
    warnings: List[str]
    errors: List[str]