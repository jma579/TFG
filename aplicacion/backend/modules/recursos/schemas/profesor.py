"""
Schemas Pydantic para la entidad Profesor.

Estos modelos definen:
- Validación de entrada (tipos, rangos, formatos)
- Serialización de salida (respuestas API)
- Documentación automática (OpenAPI)
- Normalización de datos (strip, lowercase, etc.)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from typing import Optional
import re
from constants.enums import TipoConciliacion  # <--- IMPORTANTE: Importar el Enum


# ============================================================
#  BASE: Campos comunes compartidos por Create/Update/Out
# ============================================================

class ProfesorBase(BaseModel):
    """
    Schema base con campos comunes de Profesor.
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Nombre del profesor",
        examples=["Juan", "María José", "Pedro"]
    )
    
    apellidos: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Apellidos del profesor",
        examples=["García López", "Martínez", "Fernández García"]
    )
    
    email: Optional[str] = Field(
        None,
        max_length=200,
        description="Correo electrónico único del profesor",
        examples=["juan.garcia@universidad.es", "maria.martinez@uam.es"]
    )
    
    telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono de contacto del profesor",
        examples=["+34 912 345 678", "912345678", "+1-555-1234"]
    )
    
    departamento: Optional[str] = Field(
        None,
        max_length=200,
        description="Departamento al que pertenece el profesor",
        examples=["Matemáticas", "Ingeniería Informática", "Física Aplicada"]
    )
    
    activo: bool = Field(
        default=True,
        description="Indica si el profesor está activo (soft delete)"
    )

    # --- NUEVO CAMPO ---
    conciliacion: Optional[TipoConciliacion] = Field(
        None,
        description="Preferencia de conciliación familiar (entrada tardía, salida temprana, mixta)",
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


# ============================================================
#  CREATE: Schema para crear profesor (POST)
# ============================================================

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


# ============================================================
#  UPDATE: Schema para actualizar profesor (PUT/PATCH)
# ============================================================

class ProfesorUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=120)
    apellidos: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=20)
    departamento: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = Field(None)
    
    # --- NUEVO CAMPO ---
    conciliacion: Optional[TipoConciliacion] = Field(
        None,
        description="Actualizar preferencia de conciliación"
    )
    
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


# ============================================================
#  OUT: Schema de respuesta (GET)
# ============================================================

class ProfesorOut(ProfesorBase):
    id: int = Field(..., description="ID único autogenerado del profesor")
    
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


# ============================================================
#  LIST: Schema para listado paginado
# ============================================================

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