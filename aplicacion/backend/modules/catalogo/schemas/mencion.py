"""
Schemas Pydantic para la entidad Mencion.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re


class MencionBase(BaseModel):
    programa_id: int = Field(..., gt=0)
    nombre: str = Field(..., min_length=1, max_length=200)
    activo: bool = Field(default=True)
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v):
        if not v or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v


class MencionCreate(MencionBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "programa_id": 1,
                "nombre": "Ingeniería del Software",
                "activo": True
            }
        }
    )


class MencionUpdate(BaseModel):
    programa_id: Optional[int] = Field(None, gt=0)
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    activo: Optional[bool] = Field(None)
    
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
                "nombre": "Ingeniería del Software Avanzada"
            }
        }
    )


class MencionOut(MencionBase):
    id: int = Field(...)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "programa_id": 1,
                "nombre": "Ingeniería del Software",
                "activo": True
            }
        }
    )


class MencionList(BaseModel):
    total: int = Field(..., ge=0)
    items: list[MencionOut] = Field(
        ...,
        description="Lista de menciones en la página actual"
    )
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 25,
                "items": [
                    {
                        "id": 1,
                        "programa_id": 1,
                        "nombre": "Ingeniería del Software",
                        "activo": True
                    },
                    {
                        "id": 2,
                        "programa_id": 1,
                        "nombre": "Inteligencia Artificial",
                        "activo": True
                    }
                ],
                "page": 1,
                "size": 10
            }
        }
    )


class MencionResumen(BaseModel):
    id: int = Field(...)
    nombre: str = Field(...)

    model_config = ConfigDict(from_attributes=True)