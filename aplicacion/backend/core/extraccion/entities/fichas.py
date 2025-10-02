from dataclasses import dataclass
from typing import List, Optional
from core.extraccion.entities.extractor import ExtractionMetadata
from core.extraccion.entities.common import ParsingMetadata

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