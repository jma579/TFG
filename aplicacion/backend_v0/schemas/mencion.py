from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class MencionBase(BaseModel):
    nombre: str = Field(
        min_length=3, 
        max_length=100, 
        description="Nombre de la mención",
        example="Computación"
    )
    grado_id: int = Field(gt=0, description="ID del grado al que pertenece la mención")
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('El nombre no puede estar vacío')
        if v.isdigit():
            raise ValueError('El nombre no puede ser solo números')
        return v.title()

class MencionCreate(MencionBase):
    pass

class MencionUpdate(BaseModel):
    nombre: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=100, 
        description="Nuevo nombre de la mención"
    )
    grado_id: Optional[int] = Field(None, gt=0, description="Nuevo ID del grado")
    
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

class MencionOut(MencionBase):
    id: int = Field(description="ID único de la mención")

    class Config:
        from_attributes = True

# Schema con relaciones anidadas
class MencionDetallada(MencionOut):
    grado_nombre: Optional[str] = Field(None, description="Nombre del grado asociado")
    total_asignaturas: Optional[int] = Field(default=0, description="Número de asignaturas específicas de la mención")

    class Config:
        from_attributes = True
