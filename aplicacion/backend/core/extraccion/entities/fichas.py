from dataclasses import dataclass
from typing import List, Optional
from core.extraccion.entities.extractor import ExtractionMetadata

@dataclass
class Teacher:
    nombre: str
    apellidos: str

@dataclass
class SubjectSheet:
    codigo_plan: str
    nombre: str
    periodo: str
    ects: float
    modalidad: str
    idioma: str
    english_friendly: bool
    profesores: List[Teacher]
    centro: Optional[str] = None
    departamento: Optional[str] = None
    raw_text: Optional[str] = None
    metadata: Optional[ExtractionMetadata] = None