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

class ErrorType(str, Enum):
    FILE_NOT_FOUND = "file_not_found"
    INVALID_PDF = "invalid_pdf"
    PROCESSING_TIMEOUT = "processing_timeout"
    NO_EMBEDDED_TEXT = "no_embedded_text"
    UNKNOWN_ERROR = "unknown_error"

# Metadatos emitidos por pdf_extractor
@dataclass(frozen=True)
class ExtractionMetadata:
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

# Resultado principal de extracción
@dataclass(frozen=True)
class ExtractionResult:
    text: str
    quality: ExtractionQuality
    confidence: float
    status: ProcessingStatus
    metadata: ExtractionMetadata
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == ProcessingStatus.COMPLETED

    @property
    def is_usable(self) -> bool:
        return self.quality in {
            ExtractionQuality.EXCELLENT,
            ExtractionQuality.GOOD,
            ExtractionQuality.ACCEPTABLE,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quality"] = self.quality.value
        d["status"] = self.status.value
        d["error_type"] = self.error_type.value if self.error_type else None
        return d

# Match técnico (opcional) si el extractor decide exponer hits de regex
@dataclass(frozen=True)
class SubjectCodeHit:
    code: str           # código normalizado detectado (e.g., "G264")
    full_match: str     # literal del match
    confidence: float   # 0..1
    position: Tuple[int, int]  # offset (start, end) en el texto

