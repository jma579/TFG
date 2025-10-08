from dataclasses import dataclass, asdict
from typing import List, Optional
from typing import Optional, Tuple, Dict, Any, List
from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ErrorType,
    ExtractionMetadata, ParsingMetadata
)

# Resultado principal de extracción
@dataclass(frozen=True)
class ExtractionResult:
    text: str
    metadata: ExtractionMetadata
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == ProcessingStatus.COMPLETED

    @property
    def is_usable(self) -> bool:
        return self.metadata.quality in {
            ExtractionQuality.EXCELLENT,
            ExtractionQuality.GOOD,
            ExtractionQuality.ACCEPTABLE,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quality"] = self.metadata.quality.value
        d["status"] = self.metadata.status.value
        d["error_type"] = self.error_type.value if self.error_type else None
        return d
    
'''
# Match técnico (opcional) si el extractor decide exponer hits de regex
@dataclass(frozen=True)
class SubjectCodeHit:
    code: str           # código normalizado detectado (e.g., "G264")
    full_match: str     # literal del match
    confidence: float   # 0..1
    position: Tuple[int, int]  # offset (start, end) en el texto
'''

# =============================================================================
# ENTIDADES ESPECÍFICAS PARA FICHAS ACADÉMICAS (SALIDA DEL PARSER)
# =============================================================================

@dataclass
class Teacher:
    nombre: str
    apellidos: str

@dataclass
class Titulacion:
    titulacion: str
    tipo_asignatura: str
    curso: str


@dataclass
class SubjectSheet:
    codigo_plan: str
    nombre: str
    titulaciones: List[Titulacion]
    periodo: str
    num_periodo: int
    ects: int
    profesores: List[Teacher]
    modalidad: Optional[str] = None
    idioma: Optional[str] = None
    english_friendly: Optional[bool] = None
    centro: Optional[str] = None
    departamento: Optional[str] = None
    raw_text: Optional[str] = None
    parsing_metadata: Optional[ParsingMetadata] = None
    extraction_metadata: Optional[ExtractionMetadata] = None