from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from .enums import CuatrimestreEnum

class AsignaturaBase(BaseModel):
    nombre: str = Field(
        min_length=3, 
        max_length=150, 
        description="Nombre de la asignatura",
        example="Programación Orientada a Objetos"
    )
    creditos: int = Field(
        gt=0, 
        le=12, 
        description="Créditos ECTS de la asignatura (1-12)",
        example=6
    )
    horas_semanales: int = Field(
        gt=0, 
        le=20, 
        description="Horas semanales de clase (1-20)",
        example=4
    )
    curso: int = Field(
        ge=1, 
        le=6, 
        description="Curso académico (1-6)",
        example=2
    )
    cuatrimestre: CuatrimestreEnum = Field(
        description="Cuatrimestre en que se imparte",
        example="1"
    )

    @field_validator('nombre')
    def validar_nombre(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('El nombre no puede estar vacío')
        if v.isdigit():
            raise ValueError('El nombre no puede ser solo números')
        return v.title()
    
    @model_validator(mode='after')
    def validar_coherencia_horas_creditos(self):
        # Validar coherencia entre horas semanales y créditos
        if self.horas_semanales and self.creditos:
            if self.horas_semanales > self.creditos * 2.5:
                raise ValueError(f'Las horas semanales ({self.horas_semanales}) son excesivas para {self.creditos} créditos')
        return self

class AsignaturaCreate(AsignaturaBase):
    pass

class AsignaturaUpdate(BaseModel):
    nombre: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=150, 
        description="Nuevo nombre de la asignatura"
    )
    creditos: Optional[int] = Field(None, gt=0, le=12, description="Nuevos créditos ECTS")
    horas_semanales: Optional[int] = Field(None, gt=0, le=20, description="Nuevas horas semanales")
    curso: Optional[int] = Field(None, ge=1, le=6, description="Nuevo curso académico")
    cuatrimestre: Optional[CuatrimestreEnum] = Field(None, description="Nuevo cuatrimestre")

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

class AsignaturaOut(AsignaturaBase):
    id: int = Field(description="ID único de la asignatura")

    class Config:
        from_attributes = True

# Schema con información adicional
class AsignaturaDetallada(AsignaturaOut):
    total_sesiones: Optional[int] = Field(default=0, description="Número total de sesiones programadas")
    grados_asociados: Optional[List[str]] = Field(default=[], description="Nombres de grados que cursan esta asignatura")
    
    class Config:
        from_attributes = True

# Schemas para las relaciones many-to-many

class AsignaturaGradoBase(BaseModel):
    asignatura_id: int = Field(gt=0, description="ID de la asignatura")
    grado_id: int = Field(gt=0, description="ID del grado")

class AsignaturaGradoCreate(AsignaturaGradoBase):
    pass

class AsignaturaGradoUpdate(BaseModel):
    asignatura_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de asignatura")
    grado_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de grado")

class AsignaturaGradoOut(AsignaturaGradoBase):
    id: int = Field(description="ID único de la relación")

    class Config:
        from_attributes = True

class AsignaturaMencionBase(BaseModel):
    asignatura_id: int = Field(gt=0, description="ID de la asignatura")
    mencion_id: int = Field(gt=0, description="ID de la mención")

class AsignaturaMencionCreate(AsignaturaMencionBase):
    pass

class AsignaturaMencionUpdate(BaseModel):
    asignatura_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de asignatura")
    mencion_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de mención")

class AsignaturaMencionOut(AsignaturaMencionBase):
    id: int = Field(description="ID único de la relación")

    class Config:
        from_attributes = True
