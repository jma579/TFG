"""Schemas Pydantic para Aula."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List

from constants.enums import TipoAula


def normalize_texto(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized if normalized else None


class AulaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    codigo: str = Field(..., min_length=1, max_length=50)
    tipo: TipoAula = Field(...)
    capacidad: Optional[int] = Field(None, gt=0)
    activo: bool = Field(default=True)
    
    @field_validator("nombre", "codigo", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: str) -> str:
        if not value:
            raise ValueError("El código no puede estar vacío")
        return value.upper()


class AulaCreate(AulaBase):
    pass


class AulaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    tipo: Optional[TipoAula] = Field(None)
    capacidad: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = Field(None)
    
    @field_validator("nombre", "codigo", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        return value.upper()


class AulaOut(AulaBase):
    id: int
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Aula Magna",
                "codigo": "MAGNA",
                "tipo": "TEORIA",
                "capacidad": 200,
                "activo": True
            }
        }
    )


class AulaList(BaseModel):
    total: int = Field(..., ge=0)
    items: List[AulaOut]
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)