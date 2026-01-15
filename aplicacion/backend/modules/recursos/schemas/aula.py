"""
Esquemas Pydantic para la entidad Aula.

Define los contratos de datos para:
- Entrada: AulaCreate, AulaUpdate
- Salida: AulaOut, AulaList
- Validaciones: unicidad de nombre/código, normalización de texto, capacidad > 0
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List

from constants.enums import TipoAula


# ============================================================
#  HELPERS: Validadores reutilizables
# ============================================================

def normalize_texto(value: Optional[str]) -> Optional[str]:
    """
    Normalizar texto: trim + colapsar múltiples espacios.
    Ej: "  LAB   1  " -> "LAB 1"
    """
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized if normalized else None


# ============================================================
#  SCHEMAS: Base y derivados
# ============================================================

class AulaBase(BaseModel):
    """
    Schema base para Aula con campos comunes.
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo del aula",
        examples=["Aula Magna", "Laboratorio de Física"]
    )
    
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código único del aula (alfanumérico)",
        examples=["A101", "LAB-2"]
    )
    
    tipo: TipoAula = Field(
        ...,
        description="Tipo de aula según clasificación (TEORIA, LABORATORIO, etc.)"
    )
    
    capacidad: Optional[int] = Field(
        None,
        gt=0,
        description="Aforo máximo del aula (número de plazas)",
        examples=[30, 50, 100]
    )

    activo: bool = Field(
        default=True,
        description="Estado del aula (activo/inactivo)"
    )
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @field_validator("nombre", "codigo", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: str) -> str:
        if not value:
            raise ValueError("El código no puede estar vacío")
        # Forzar mayúsculas para consistencia
        return value.upper()


class AulaCreate(AulaBase):
    """Schema para crear un aula."""
    pass


class AulaUpdate(BaseModel):
    """Schema para actualizar un aula (todos los campos opcionales)."""
    
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    codigo: Optional[str] = Field(None, min_length=1, max_length=50)
    tipo: Optional[TipoAula] = Field(None)
    capacidad: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = Field(None, description="Actualizar estado activo/inactivo")
    
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
    """Schema para respuestas de Aula (incluye ID)."""
    
    id: int = Field(..., description="ID único del aula")
    
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
    """Schema para respuestas de listado paginado."""
    
    total: int = Field(..., ge=0)
    items: List[AulaOut] = Field(...)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)