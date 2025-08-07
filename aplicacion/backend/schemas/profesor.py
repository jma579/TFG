from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
import json

class ProfesorBase(BaseModel):
    nombre: str = Field(
        min_length=3, 
        max_length=100, 
        description="Nombre completo del profesor",
        example="Dr. Juan Pérez García"
    )
    disponibilidad: Dict[str, List[str]] = Field(
        description="Disponibilidad por días. Formato: {'lunes': ['08:00-10:00', '12:00-14:00']}",
        example={
            "lunes": ["08:00-10:00", "12:00-14:00"],
            "martes": ["10:00-12:00"],
            "miercoles": ["08:00-12:00"]
        }
    )
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('El nombre no puede estar vacío')
        if v.isdigit():
            raise ValueError('El nombre no puede ser solo números')
        # Verificar que tiene al menos nombre y apellido
        palabras = v.split()
        if len(palabras) < 2:
            raise ValueError('Debe incluir al menos nombre y apellido')
        return v.title()
    
    @field_validator('disponibilidad')
    def validar_disponibilidad(cls, v):
        dias_validos = {'lunes', 'martes', 'miercoles', 'jueves', 'viernes'}
        
        if not isinstance(v, dict):
            raise ValueError('La disponibilidad debe ser un diccionario')
        
        for dia, horarios in v.items():
            if dia not in dias_validos:
                raise ValueError(f'Día inválido: {dia}. Días válidos: {dias_validos}')
            
            if not isinstance(horarios, list):
                raise ValueError(f'Los horarios del {dia} deben ser una lista')
            
            for horario in horarios:
                if not isinstance(horario, str):
                    raise ValueError(f'Cada horario debe ser una cadena de texto')
                
                # Validar formato HH:MM-HH:MM
                if '-' not in horario:
                    raise ValueError(f'Formato de horario inválido: {horario}. Use HH:MM-HH:MM')
                
                try:
                    inicio, fin = horario.split('-')
                    # Validar formato de hora
                    for hora in [inicio, fin]:
                        if len(hora) != 5 or hora[2] != ':':
                            raise ValueError(f'Formato de hora inválido: {hora}. Use HH:MM')
                        
                        hh, mm = hora.split(':')
                        if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                            raise ValueError(f'Hora inválida: {hora}')
                    
                    # Verificar que hora inicio < hora fin
                    if inicio >= fin:
                        raise ValueError(f'La hora de inicio debe ser anterior a la de fin: {horario}')
                        
                except ValueError as e:
                    if 'invalid literal' in str(e):
                        raise ValueError(f'Formato de horario inválido: {horario}')
                    raise e
        
        return v

class ProfesorCreate(ProfesorBase):
    pass

class ProfesorUpdate(BaseModel):
    nombre: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=100, 
        description="Nuevo nombre del profesor"
    )
    disponibilidad: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Nueva disponibilidad del profesor"
    )
    
    @field_validator('nombre')
    def validar_nombre(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('El nombre no puede estar vacío')
            if v.isdigit():
                raise ValueError('El nombre no puede ser solo números')
            palabras = v.split()
            if len(palabras) < 2:
                raise ValueError('Debe incluir al menos nombre y apellido')
            return v.title()
        return v
    
    @field_validator('disponibilidad')
    def validar_disponibilidad(cls, v):
        if v is not None:
            # Usar la misma validación que en ProfesorBase
            return ProfesorBase.__validators__['disponibilidad'](v)
        return v

class ProfesorOut(ProfesorBase):
    id: int = Field(description="ID único del profesor")

    class Config:
        from_attributes = True

# Schema con información adicional
class ProfesorDetallado(ProfesorOut):
    total_asignaturas: Optional[int] = Field(default=0, description="Número de asignaturas que imparte")
    total_sesiones: Optional[int] = Field(default=0, description="Número total de sesiones programadas")
    carga_horaria_semanal: Optional[float] = Field(default=0.0, description="Horas de clase por semana")

    class Config:
        from_attributes = True

# Schemas para la relación many-to-many Profesor-Asignatura

class ProfesorAsignaturaBase(BaseModel):
    profesor_id: int = Field(gt=0, description="ID del profesor")
    asignatura_id: int = Field(gt=0, description="ID de la asignatura")

class ProfesorAsignaturaCreate(ProfesorAsignaturaBase):
    pass

class ProfesorAsignaturaUpdate(BaseModel):
    profesor_id: Optional[int] = Field(None, gt=0, description="Nuevo ID del profesor")
    asignatura_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de la asignatura")

class ProfesorAsignaturaOut(ProfesorAsignaturaBase):
    id: int = Field(description="ID único de la relación")

    class Config:
        from_attributes = True

# Schema para respuestas con información combinada
class ProfesorAsignaturaDetallado(ProfesorAsignaturaOut):
    profesor_nombre: Optional[str] = Field(None, description="Nombre del profesor")
    asignatura_nombre: Optional[str] = Field(None, description="Nombre de la asignatura")
    
    class Config:
        from_attributes = True
