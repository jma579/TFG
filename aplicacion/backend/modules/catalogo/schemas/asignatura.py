"""
Schemas Pydantic para Asignatura.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re

from constants.enums import Periodo, ModalidadAsignatura, Idioma, TipoAsignatura
from modules.catalogo.schemas.programa import ProgramaOut
from modules.catalogo.schemas.mencion import MencionResumen


class AsignaturaBase(BaseModel):
    codigo_plan: str = Field(..., min_length=1, max_length=6)
    nombre: str = Field(..., min_length=1, max_length=250)
    periodo: Periodo = Field(...)
    ects: Optional[int] = Field(None, ge=1, le=12)
    modalidad: ModalidadAsignatura = Field(...)
    idioma: Idioma = Field(default=Idioma.ESPAÑOL)
    english_friendly: bool = Field(default=False)
    activo: bool = Field(default=True)
    
    
    @field_validator('codigo_plan', mode='before')
    @classmethod
    def normalize_codigo_plan(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            return v
        v = v.strip()
        v = v.upper()
        return v
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v


class AsignaturaCreate(AsignaturaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo_plan": "MAT101",
                "nombre": "Matemáticas I",
                "periodo": "cuatrimestral_1",
                "ects": 6,
                "modalidad": "presencial",
                "idioma": "español",
                "english_friendly": False,
                "activo": True
            }
        }
    )


class AsignaturaUpdate(BaseModel):
    codigo_plan: Optional[str] = Field(None, min_length=1, max_length=6)
    nombre: Optional[str] = Field(None, min_length=1, max_length=250)
    periodo: Optional[Periodo] = None
    ects: Optional[int] = Field(None, ge=1, le=12)
    modalidad: Optional[ModalidadAsignatura] = None
    idioma: Optional[Idioma] = None
    english_friendly: Optional[bool] = None
    activo: Optional[bool] = None
    
    
    @field_validator('codigo_plan', mode='before')
    @classmethod
    def normalize_codigo_plan(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = v.upper()
        return v
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v
    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Matemáticas Avanzadas I",
                "ects": 9
            }
        }
    )


class AsignaturaProgramaOut(BaseModel):
    programa: ProgramaOut = Field(...)
    curso: Optional[int] = Field(
        None,
        description="Curso dentro del programa (1..4, o None si no aplica)",
        examples=[1, 2, None],
    )
    tipo_asignatura: Optional[TipoAsignatura] = None
    mencion: Optional[MencionResumen] = None
    model_config = ConfigDict(from_attributes=True)


class AsignaturaOut(AsignaturaBase):
    id: int = Field(...)
    num_profesores: int = Field(
        default=0,
        description="Número de profesores asignados",
        examples=[0, 2]
    )
    num_titulaciones: int = Field(default=0)
    titulaciones: list[AsignaturaProgramaOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
            "example": {
                "id": 1,
                "codigo_plan": "MAT101",
                "nombre": "Matemáticas I",
                "periodo": "cuatrimestral_1",
                "ects": 6,
                "modalidad": "presencial",
                "idioma": "español",
                "english_friendly": False,
                "activo": True
            }
        }
    )


class AsignaturaList(BaseModel):
    total: int = Field(..., ge=0)
    items: list[AsignaturaOut]
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 45,
                "items": [
                    {
                        "id": 1,
                        "codigo_plan": "MAT101",
                        "nombre": "Matemáticas I",
                        "periodo": "cuatrimestral_1",
                        "ects": 6,
                        "modalidad": "presencial",
                        "idioma": "español",
                        "english_friendly": False,
                        "activo": True
                    }
                ],
                "page": 1,
                "size": 10
            }
        }
    )