"""
Entidades para restricciones de profesorado: datos crudos, parseados y normalizados.
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import time

from core.extraccion.common.entities import (
    ExtractionMetadata, ErrorType, ProcessingStatus, ParsingMetadata
)
from constants.enums import DiaSemana


@dataclass
class RawRestriccionRow:
    """Fila literal extraída del Excel de restricciones."""
    fila_excel: int
    profesor: str
    dias: str
    franja: str


@dataclass(frozen=True)
class ExtractionResultRestricciones:
    """Resultado de la extracción en bruto del Excel."""
    filas_crudas: List[RawRestriccionRow]
    metadata: ExtractionMetadata
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.metadata.status == ProcessingStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.metadata.status.value
        d["error_type"] = self.error_type.value if self.error_type else None
        return d


@dataclass
class ParsedRestriccion:
    """
    Dato limpio y expandido por el parser.
    Nota: Si una fila de Excel tiene "L,M", se generarán DOS objetos ParsedRestriccion.
    """
    profesor: str
    dia: str
    hora_inicio_str: str
    hora_fin_str: str
    fila_origen: int


class NormalizedRestriccionData(BaseModel):
    """
    Dato normalizado listo para ser procesado por el Unit of Work e insertado en BD.
    """
    profesor_nombre_completo: str = Field(..., max_length=250)
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    fila_origen: int

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


@dataclass(frozen=True)
class PipelineRestriccionesResult:
    """Resultado del procesamiento completo de un Excel de restricciones."""
    success: bool
    restricciones_validas: List[NormalizedRestriccionData]
    errores: List[str]
    extraction_metadata: ExtractionMetadata
    parsing_metadata: ParsingMetadata