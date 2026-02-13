"""
Schemas Pydantic para Profesor.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re

from constants.enums import TipoConciliacion


class ProfesorBase(BaseModel):
    
    nombre: str = Field(..., min_length=1, max_length=120, examples=["Juan", "María José"])
    
    apellidos: str = Field(..., min_length=1, max_length=200, examples=["García López", "Martínez"])
    
    email: Optional[str] = Field(None, max_length=200, examples=["juan.garcia@universidad.es"])
    
    telefono: Optional[str] = Field(None, max_length=20, examples=["+34 912 345 678"])
    
    departamento: Optional[str] = Field(None, max_length=200, examples=["Matemáticas"])
    
    activo: bool = Field(default=True)
    conciliacion: Optional[TipoConciliacion] = Field(
        None,
        description="Preferencia de conciliación familiar (entrada_tardia, salida_temprana, mixta)",
        examples=["entrada_tardia", "mixta"]
    )
    
    
    @field_validator('nombre', 'apellidos', 'departamento', mode='before')
    @classmethod
    def normalize_texto(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v
    
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = v.lower()
        return v
    
    @field_validator('telefono', mode='before')
    @classmethod
    def normalize_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str):
            return v
        return v.strip()


class ProfesorCreate(ProfesorBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Juan",
                "apellidos": "García López",
                "email": "juan.garcia@universidad.es",
                "telefono": "+34 912 345 678",
                "departamento": "Matemáticas",
                "activo": True,
                "conciliacion": "entrada_tardia"
            }
        }
    )


class ProfesorUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    apellidos: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=20)
    departamento: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = Field(None)
    conciliacion: Optional[TipoConciliacion] = Field(None)
    
    @field_validator('nombre', 'apellidos', 'departamento', mode='before')
    @classmethod
    def normalize_texto(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str): return v
        v = v.strip()
        return re.sub(r'\s+', ' ', v)
    
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str): return v
        return v.strip().lower()
    
    @field_validator('telefono', mode='before')
    @classmethod
    def normalize_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not isinstance(v, str): return v
        return v.strip()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "nuevo.email@universidad.es",
                "conciliacion": "salida_temprana"
            }
        }
    )


class ProfesorOut(ProfesorBase):
    id: int
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Juan",
                "apellidos": "García López",
                "email": "juan.garcia@universidad.es",
                "conciliacion": "mixta",
                "activo": True
            }
        }
    )


class ProfesorList(BaseModel):
    total: int = Field(..., ge=0)
    items: list[ProfesorOut] = Field(...) 
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 85,
                "items": [{"id": 1, "nombre": "Juan", "conciliacion": None}],
                "page": 1,
                "size": 20
            }
        }
    )