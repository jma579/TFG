"""
Schemas Pydantic para Programa.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re

from constants.enums import TipoPrograma


class ProgramaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: TipoPrograma = Field(...)
    activo: bool = Field(default=True)

    @field_validator('nombre')
    @classmethod
    def normalize_nombre(cls, v: str) -> str:
        if not v:
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v


class ProgramaCreate(ProgramaBase):
    pass


class ProgramaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    tipo: Optional[TipoPrograma] = None
    activo: Optional[bool] = None


class ProgramaOut(ProgramaBase):
    id: int = Field(...)
    
    model_config = ConfigDict(
        from_attributes=True, 
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Grado en Matemáticas",
                "tipo": "GRADO",
                "activo": True
            }
        }
    )


class ProgramaList(BaseModel):
    total: int = Field(..., ge=0)
    items: list[ProgramaOut]
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)