"""
Entidades para fichas académicas: datos crudos y normalizados.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ErrorType,
    ExtractionMetadata, ParsingMetadata
)
from constants.enums import Periodo, TipoAsignatura, ModalidadAsignatura, Idioma


@dataclass(frozen=True)
class ExtractionResult:
    """Resultado de extracción de PDF."""
    text: str
    metadata: ExtractionMetadata
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.metadata.status == ProcessingStatus.COMPLETED

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


@dataclass
class Teacher:
    """Profesor extraído del PDF (datos crudos)."""
    nombre: str
    apellidos: str


@dataclass
class Titulacion:
    """Titulación extraída del PDF (datos crudos)."""
    programa_nombre: str
    tipo_asignatura: str
    curso: str


@dataclass
class SubjectSheet:
    """Ficha académica completa extraída del PDF (datos crudos)."""
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


class NormalizedAsignaturaData(BaseModel):
    """
    Datos normalizados de asignatura, listos para persistir en BD.
    """
    codigo_plan: str = Field(..., max_length=6)
    nombre: str = Field(..., max_length=250)
    periodo: Periodo
    ects: int = Field(..., ge=0, le=30)
    modalidad: ModalidadAsignatura
    idioma: Idioma
    english_friendly: bool

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class NormalizedTitulacionData(BaseModel):
    """
    Datos normalizados de titulación, listos para crear relación Programa-Asignatura.
    """
    programa_nombre: str = Field(..., max_length=200)
    tipo_asignatura: TipoAsignatura
    curso: int = Field(..., ge=1, le=6)

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class NormalizedProfesorData(BaseModel):
    """
    Datos normalizados de profesor, listos para persistir en BD.
    """
    nombre: str = Field(..., max_length=120)
    apellidos: str = Field(..., max_length=200)

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class NormalizedFichaData(BaseModel):
    """
    Resultado completo de normalización de una ficha académica.
    
    Contiene todos los datos normalizados y listos para persistir en BD.
    """
    asignatura: NormalizedAsignaturaData
    titulaciones: List[NormalizedTitulacionData]
    profesores: List[NormalizedProfesorData]

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class PipelineResult(BaseModel):
    """
    Resultado del procesamiento completo de una ficha académica.
    """
    success: bool
    asignatura_id: Optional[int] = None
    programas_asociados: List[int] = Field(default_factory=list)
    profesores_asociados: List[int] = Field(default_factory=list)
    created_entities: Dict[str, int] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "asignatura_id": 42,
                "programas_asociados": [1, 3],
                "profesores_asociados": [5, 8],
                "created_entities": {
                    "asignaturas": 1,
                    "programas": 1,
                    "profesores": 2,
                    "relaciones_programa_asignatura": 2,
                    "relaciones_profesor_asignatura": 2
                },
                "errors": [],
                "metadata": {
                    "extraction_quality": "excellent",
                    "parsing_confidence": 0.95,
                    "processing_time_ms": 1250
                }
            }
        }