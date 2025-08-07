from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from .enums import TipoAulaEnum

class AulaBase(BaseModel):
    nombre: str = Field(
        min_length=1, 
        max_length=50, 
        description="Nombre/código del aula",
        example="A1.01"
    )
    capacidad: int = Field(
        gt=0, 
        le=500, 
        description="Capacidad máxima de estudiantes (1-500)",
        example=30
    )
    tipo: TipoAulaEnum = Field(
        description="Tipo de aula según su equipamiento",
        example="teoria"
    )
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        v = v.strip().upper()  # Normalizar a mayúsculas
        if not v:
            raise ValueError('El nombre del aula no puede estar vacío')
        
        # Verificar formato básico (letras/números y algunos caracteres especiales)
        import re
        if not re.match(r'^[A-Z0-9._-]+$', v):
            raise ValueError('El nombre del aula solo puede contener letras, números, puntos, guiones y guiones bajos')
        
        return v
    
    @model_validator(mode='after')
    def validar_capacidad_por_tipo(self):
        # Validaciones específicas por tipo de aula
        if self.tipo == TipoAulaEnum.LABORATORIO and self.capacidad > 25:
            raise ValueError('Los laboratorios no pueden tener más de 25 plazas por seguridad')
        elif self.tipo == TipoAulaEnum.INFORMATICA and self.capacidad > 30:
            raise ValueError('Las aulas de informática no pueden tener más de 30 equipos')
        elif self.tipo == TipoAulaEnum.SEMINARIO and self.capacidad > 20:
            raise ValueError('Los seminarios no pueden tener más de 20 plazas')
        elif self.tipo == TipoAulaEnum.MAGNA and self.capacidad < 50:
            raise ValueError('Las aulas magnas deben tener al menos 50 plazas')
        
        return self

class AulaCreate(AulaBase):
    pass

class AulaUpdate(BaseModel):
    nombre: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=50, 
        description="Nuevo nombre del aula"
    )
    capacidad: Optional[int] = Field(
        None, 
        gt=0, 
        le=500, 
        description="Nueva capacidad del aula"
    )
    tipo: Optional[TipoAulaEnum] = Field(None, description="Nuevo tipo de aula")
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError('El nombre del aula no puede estar vacío')
            
            import re
            if not re.match(r'^[A-Z0-9._-]+$', v):
                raise ValueError('El nombre del aula solo puede contener letras, números, puntos, guiones y guiones bajos')
            return v
        return v

class AulaOut(AulaBase):
    id: int = Field(description="ID único del aula")

    class Config:
        from_attributes = True

# Schema con información adicional
class AulaDetallada(AulaOut):
    ocupacion_actual: Optional[float] = Field(
        default=0.0, 
        description="Porcentaje de ocupación semanal (0-100)",
        ge=0, 
        le=100
    )
    total_sesiones: Optional[int] = Field(default=0, description="Número total de sesiones programadas")
    horas_uso_semanal: Optional[float] = Field(default=0.0, description="Horas de uso por semana")

    class Config:
        from_attributes = True
