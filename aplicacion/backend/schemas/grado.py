from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class GradoBase(BaseModel):
    nombre: str = Field(
        min_length=3, 
        max_length=100, 
        description="Nombre del grado académico",
        example="Grado en Ingeniería Informática"
    )
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('El nombre no puede estar vacío')
        # Verificar que no contenga solo números
        if v.isdigit():
            raise ValueError('El nombre no puede ser solo números')
        return v.title()  # Capitalizar primera letra de cada palabra

class GradoCreate(GradoBase):
    pass

class GradoUpdate(BaseModel):
    nombre: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=100, 
        description="Nuevo nombre del grado"
    )
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('El nombre no puede estar vacío')
            if v.isdigit():
                raise ValueError('El nombre no puede ser solo números')
            return v.title()
        return v

class GradoOut(GradoBase):
    id: int = Field(description="ID único del grado")

    class Config:
        from_attributes = True

# Schema con relaciones anidadas (opcional para endpoints que necesiten más detalle)
class GradoDetallado(GradoOut):
    menciones: Optional[List['MencionOut']] = Field(default=[], description="Menciones asociadas al grado")
    total_asignaturas: Optional[int] = Field(default=0, description="Número total de asignaturas del grado")

    class Config:
        from_attributes = True

# Resolver referencias futuras
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .mencion import MencionOut
