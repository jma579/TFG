from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import time, datetime, date
from typing import Optional
from .enums import DiaSemanaEnum

class SesionBase(BaseModel):
    asignatura_id: int = Field(gt=0, description="ID de la asignatura")
    profesor_id: int = Field(gt=0, description="ID del profesor")
    aula_id: int = Field(gt=0, description="ID del aula")
    dia: DiaSemanaEnum = Field(description="Día de la semana")
    hora_inicio: time = Field(
        description="Hora de inicio de la sesión (formato HH:MM)",
        example="08:00"
    )
    hora_fin: time = Field(
        description="Hora de fin de la sesión (formato HH:MM)",
        example="10:00"
    )
    
    @field_validator('hora_inicio')
    def validar_hora_inicio(cls, v):
        # Las clases solo pueden empezar entre 8:00 y 20:00
        if not (time(8, 0) <= v <= time(20, 0)):
            raise ValueError('Las clases solo pueden empezar entre 08:00 y 20:00')
        
        # Las clases deben empezar en punto o en media
        if v.minute not in [0, 30]:
            raise ValueError('Las clases solo pueden empezar en punto (:00) o en media (:30)')
        
        return v
    
    @model_validator(mode='after')
    def validar_horas_sesion(self):
        # Verificar que hora_fin > hora_inicio
        if self.hora_fin <= self.hora_inicio:
            raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        
        # Calcular duración
        datetime_inicio = datetime.combine(date.today(), self.hora_inicio)
        datetime_fin = datetime.combine(date.today(), self.hora_fin)
        duracion = datetime_fin - datetime_inicio
        duracion_minutos = duracion.total_seconds() / 60
        
        # Validar duración mínima (50 minutos) y máxima (4 horas)
        if duracion_minutos < 50:
            raise ValueError('Las sesiones deben durar mínimo 50 minutos')
        
        if duracion_minutos > 240:  # 4 horas
            raise ValueError('Las sesiones no pueden durar más de 4 horas')
        
        # Verificar que la duración sea en incrementos de 30 minutos
        if duracion_minutos % 30 != 0:
            raise ValueError('La duración debe ser en incrementos de 30 minutos')
        
        return self
    
    @field_validator('dia')
    def validar_dia_laborable(cls, v):
        # Verificación adicional aunque el enum ya limita los valores
        dias_validos = [DiaSemanaEnum.LUNES, DiaSemanaEnum.MARTES, 
                       DiaSemanaEnum.MIERCOLES, DiaSemanaEnum.JUEVES, DiaSemanaEnum.VIERNES]
        if v not in dias_validos:
            raise ValueError(f'Las clases solo pueden ser en días laborables: {[d.value for d in dias_validos]}')
        return v

class SesionCreate(SesionBase):
    pass

class SesionUpdate(BaseModel):
    asignatura_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de asignatura")
    profesor_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de profesor")
    aula_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de aula")
    dia: Optional[DiaSemanaEnum] = Field(None, description="Nuevo día de la semana")
    hora_inicio: Optional[time] = Field(None, description="Nueva hora de inicio")
    hora_fin: Optional[time] = Field(None, description="Nueva hora de fin")
    
    @field_validator('hora_inicio')
    @classmethod
    def validar_hora_inicio(cls, v):
        if v is not None:
            # Validar que esté en horario laboral (8:00 - 20:00)
            if v < time(8, 0) or v > time(20, 0):
                raise ValueError('Las clases solo pueden empezar entre las 8:00 y las 20:00')
            
            # Las clases deben empezar en punto o en media
            if v.minute not in [0, 30]:
                raise ValueError('Las clases solo pueden empezar en punto (:00) o en media (:30)')
        return v
    
    @field_validator('hora_fin', mode='before')
    @classmethod
    def validar_hora_fin(cls, v, info):
        if v is not None:
            # Validación básica de rango
            if v > time(22, 0):
                raise ValueError('Las clases no pueden terminar después de las 22:00')
        return v

class SesionOut(SesionBase):
    id: int = Field(description="ID único de la sesión")

    class Config:
        from_attributes = True

# Schema con información detallada
class SesionDetallada(SesionOut):
    asignatura_nombre: Optional[str] = Field(None, description="Nombre de la asignatura")
    profesor_nombre: Optional[str] = Field(None, description="Nombre del profesor")
    aula_nombre: Optional[str] = Field(None, description="Nombre del aula")
    duracion_minutos: Optional[int] = Field(None, description="Duración de la sesión en minutos")
    
    class Config:
        from_attributes = True

# Schema para consultas de horarios
class ConsultaHorario(BaseModel):
    dia: Optional[DiaSemanaEnum] = Field(None, description="Filtrar por día")
    hora_inicio_desde: Optional[time] = Field(None, description="Hora mínima de inicio")
    hora_inicio_hasta: Optional[time] = Field(None, description="Hora máxima de inicio")
    asignatura_id: Optional[int] = Field(None, gt=0, description="Filtrar por asignatura")
    profesor_id: Optional[int] = Field(None, gt=0, description="Filtrar por profesor")
    aula_id: Optional[int] = Field(None, gt=0, description="Filtrar por aula")

# Schema para detectar conflictos
class ConflictoHorario(BaseModel):
    tipo_conflicto: str = Field(description="Tipo de conflicto detectado")
    sesion_1: SesionDetallada = Field(description="Primera sesión en conflicto")
    sesion_2: SesionDetallada = Field(description="Segunda sesión en conflicto")
    descripcion: str = Field(description="Descripción detallada del conflicto")
    gravedad: str = Field(description="Gravedad del conflicto: baja, media, alta")

    class Config:
        from_attributes = True
