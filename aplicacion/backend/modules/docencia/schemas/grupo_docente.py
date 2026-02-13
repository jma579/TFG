"""
Esquemas Pydantic para la entidad GrupoDocente.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List

from constants.enums import TipoGrupoDocente


def normalize_texto(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    
    normalized = " ".join(value.strip().split())
    return normalized if normalized else None


class GrupoDocenteBase(BaseModel):
    asignatura_id: int = Field(..., gt=0)
    codigo: str = Field(..., min_length=1, max_length=50)
    tipo: TipoGrupoDocente = Field(...)
    curso: Optional[int] = Field( None, ge=1, le=6)
    turno: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Turno del grupo (mañana, tarde, noche, etc.)",
        examples=["mañana", "tarde", "noche", "M", "T"]
    )
    
    @field_validator("codigo", "turno", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El código no puede estar vacío")
        return value.upper()  

class GrupoDocenteCreate(GrupoDocenteBase):
    pass


class GrupoDocenteUpdate(BaseModel):
    asignatura_id: Optional[int] = Field(None, gt=0)
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)    
    tipo: Optional[TipoGrupoDocente] = Field(None)
    curso: Optional[int] = Field(None, ge=1, le=6)
    turno: Optional[str] = Field(None, min_length=1, max_length=30)
    
    @field_validator("codigo", "turno", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("El código no puede estar vacío")
        return value.upper()


class GrupoDocenteOut(GrupoDocenteBase):
    id: int = Field(...)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "asignatura_id": 42,
                "codigo": "T1",
                "tipo": "teoria",
                "curso": 3,
                "turno": "mañana"
            }
        }
    )


class GrupoDocenteList(BaseModel):
    total: int = Field(
        ...,
        ge=0,
        description="Total de grupos docentes que cumplen los filtros (sin paginar)"
    )
    items: List[GrupoDocenteOut] = Field(
        ...,
        description="Grupos docentes en la página actual"
    )
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 15,
                "items": [
                    {
                        "id": 1,
                        "asignatura_id": 42,
                        "codigo": "T1",
                        "tipo": "teoria",
                        "curso": 3,
                        "turno": "mañana"
                    },
                    {
                        "id": 2,
                        "asignatura_id": 42,
                        "codigo": "P1",
                        "tipo": "practica",
                        "curso": 3,
                        "turno": "tarde"
                    }
                ],
                "page": 1,
                "size": 20
            }
        }
    )