"""
Entidades específicas para el sistema de extracción y parsing de PDFs académicos.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List, Literal

__all__ = [
    "ExtractionQuality", "ProcessingStatus", "ErrorType",
    "ExtractionMetadata", "ExtractionResult",
    "SubjectCodeHit", "Warning", "ParsingMetadata", "ParserError"
]


class ExtractionQuality(str, Enum):
    """Niveles de calidad de la extracción de texto."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


class ProcessingStatus(str, Enum):
    """Estados del proceso de extracción."""
    COMPLETED = "completed"
    FAILED = "failed"
    LOW_QUALITY = "low_quality"


class ErrorType(str, Enum):
    """Tipos de errores en el proceso de extracción."""
    FILE_NOT_FOUND = "file_not_found"
    INVALID_PDF = "invalid_pdf"
    PROCESSING_TIMEOUT = "processing_timeout"
    NO_EMBEDDED_TEXT = "no_embedded_text"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class Warning:
    """Aviso con nivel de severidad."""
    message: str
    severity: Literal["severe", "moderate", "minor"]


@dataclass
class ExtractionMetadata:
    """Metadatos emitidos por el extractor de PDF."""
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
    warnings: List[Warning] = field(default_factory=list)
    pages_with_text: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte los metadatos a diccionario."""
        return asdict(self)


@dataclass
class ExtractionResult:
    """Resultado completo de la extracción de un PDF."""
    text: str
    metadata: ExtractionMetadata


@dataclass
class SubjectCodeHit:
    """Código de asignatura detectado en el texto."""
    code: str
    confidence: float
    position: int


class ParserError(Exception):
    """Error de parsing (distinto a errores de extracción)."""
    pass


@dataclass
class ParsingMetadata:
    """Metadatos del proceso de parsing."""
    parser_name: str
    parser_version: str
    parse_timestamp: str
    parse_duration: float
    warnings: List[Warning]
    errors: List[str]