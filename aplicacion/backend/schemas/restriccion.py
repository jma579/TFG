from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, Union
from .enums import TipoRestriccionEnum
import json

class RestriccionBase(BaseModel):
    tipo: TipoRestriccionEnum = Field(description="Tipo de restricción")
    valor: Dict[str, Any] = Field(
        description="Parámetros de la restricción en formato JSON",
        example={
            "dias_no_disponible": ["viernes"],
            "horario_maximo": "18:00",
            "razon": "Profesor de tiempo parcial"
        }
    )
    asignatura_id: Optional[int] = Field(None, gt=0, description="ID de asignatura afectada (opcional)")
    profesor_id: Optional[int] = Field(None, gt=0, description="ID de profesor afectado (opcional)")
    aula_id: Optional[int] = Field(None, gt=0, description="ID de aula afectada (opcional)")
    activa: bool = Field(default=True, description="Si la restricción está activa")
    prioridad: int = Field(
        default=1, 
        ge=1, 
        le=5, 
        description="Prioridad de la restricción (1=baja, 5=crítica)"
    )
    
    @field_validator('valor', mode='before')
    @classmethod
    def validar_valor_restriccion(cls, v, info):
        if not isinstance(v, dict):
            raise ValueError('El valor debe ser un diccionario')
        
        # En Pydantic v2, usar info.data para acceder a otros campos
        data = info.data if hasattr(info, 'data') else {}
        tipo = data.get('tipo') if data else None
        
        if tipo:
            # Validaciones específicas por tipo de restricción
            if tipo == TipoRestriccionEnum.HORARIO_PROFESOR:
                required_fields = ['dias_no_disponible', 'horario_maximo']
                for field in required_fields:
                    if field not in v:
                        raise ValueError(f'Para restricción de horario de profesor se requiere el campo: {field}')
                
                # Validar días
                if not isinstance(v['dias_no_disponible'], list):
                    raise ValueError('dias_no_disponible debe ser una lista')
                
                dias_validos = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
                for dia in v['dias_no_disponible']:
                    if dia not in dias_validos:
                        raise ValueError(f'Día inválido: {dia}')
                
                # Validar horario máximo
                horario = v['horario_maximo']
                if not isinstance(horario, str) or len(horario) != 5 or horario[2] != ':':
                    raise ValueError('horario_maximo debe tener formato HH:MM')
            
            elif tipo == TipoRestriccionEnum.DISPONIBILIDAD_AULA:
                if 'horarios_no_disponible' not in v:
                    raise ValueError('Para restricción de aula se requiere horarios_no_disponible')
            
            elif tipo == TipoRestriccionEnum.CAPACIDAD_MAXIMA:
                if 'capacidad_requerida' not in v:
                    raise ValueError('Para restricción de capacidad se requiere capacidad_requerida')
                
                if not isinstance(v['capacidad_requerida'], int) or v['capacidad_requerida'] <= 0:
                    raise ValueError('capacidad_requerida debe ser un entero positivo')
            
            elif tipo == TipoRestriccionEnum.INCOMPATIBILIDAD:
                if 'asignaturas_incompatibles' not in v:
                    raise ValueError('Para restricción de incompatibilidad se requiere asignaturas_incompatibles')
                
                if not isinstance(v['asignaturas_incompatibles'], list):
                    raise ValueError('asignaturas_incompatibles debe ser una lista')
        
        return v
    
    @model_validator(mode='after')
    def validar_al_menos_una_entidad(self):
        # Al menos una entidad debe estar especificada
        entidades = [
            self.asignatura_id,
            self.profesor_id, 
            self.aula_id
        ]
        
        # Contar entidades no None
        entidades_definidas = [e for e in entidades if e is not None]
        
        # Verificar que hay al menos una entidad
        if len(entidades_definidas) == 0:
            raise ValueError('Debe especificar al menos una entidad (asignatura, profesor o aula)')
        
        return self

class RestriccionCreate(RestriccionBase):
    pass

class RestriccionUpdate(BaseModel):
    tipo: Optional[TipoRestriccionEnum] = Field(None, description="Nuevo tipo de restricción")
    valor: Optional[Dict[str, Any]] = Field(None, description="Nuevos parámetros de la restricción")
    asignatura_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de asignatura")
    profesor_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de profesor")
    aula_id: Optional[int] = Field(None, gt=0, description="Nuevo ID de aula")
    activa: Optional[bool] = Field(None, description="Nuevo estado de la restricción")
    prioridad: Optional[int] = Field(None, ge=1, le=5, description="Nueva prioridad")
    
    @field_validator('valor', mode='before')
    @classmethod
    def validar_valor_restriccion(cls, v, info):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('El valor debe ser un diccionario')
        return v

class RestriccionOut(RestriccionBase):
    id: int = Field(description="ID único de la restricción")

    class Config:
        from_attributes = True

# Schema con información detallada
class RestriccionDetallada(RestriccionOut):
    asignatura_nombre: Optional[str] = Field(None, description="Nombre de la asignatura afectada")
    profesor_nombre: Optional[str] = Field(None, description="Nombre del profesor afectado")
    aula_nombre: Optional[str] = Field(None, description="Nombre del aula afectada")
    descripcion_legible: Optional[str] = Field(None, description="Descripción en lenguaje natural")
    
    class Config:
        from_attributes = True

# Schemas para consultas específicas
class ConsultaRestricciones(BaseModel):
    tipo: Optional[TipoRestriccionEnum] = Field(None, description="Filtrar por tipo")
    activa: Optional[bool] = Field(None, description="Filtrar por estado")
    prioridad_minima: Optional[int] = Field(None, ge=1, le=5, description="Prioridad mínima")
    asignatura_id: Optional[int] = Field(None, gt=0, description="Filtrar por asignatura")
    profesor_id: Optional[int] = Field(None, gt=0, description="Filtrar por profesor")
    aula_id: Optional[int] = Field(None, gt=0, description="Filtrar por aula")

# Schema para validación de restricciones
class ValidacionRestriccion(BaseModel):
    restriccion_id: int = Field(gt=0, description="ID de la restricción a validar")
    sesion_propuesta: Dict[str, Any] = Field(description="Datos de la sesión a validar")
    
class ResultadoValidacion(BaseModel):
    es_valida: bool = Field(description="Si la sesión cumple la restricción")
    restriccion_violada: Optional[RestriccionDetallada] = Field(None, description="Restricción que se viola")
    mensaje_error: Optional[str] = Field(None, description="Mensaje de error si no es válida")
    sugerencias: Optional[list] = Field(default=[], description="Sugerencias para resolver el conflicto")
    
    class Config:
        from_attributes = True
