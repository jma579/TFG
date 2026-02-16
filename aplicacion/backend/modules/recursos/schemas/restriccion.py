from pydantic import BaseModel, ConfigDict, Field
from datetime import time
from typing import List, Optional
from constants.enums import DiaSemana


# Esquemas para CRUD manual

class RestriccionBase(BaseModel):
    """Atributos base compartidos por todos los esquemas de restricción."""
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time

class RestriccionCreate(RestriccionBase):
    """
    Esquema para crear una restricción manualmente.
    Nota: No incluimos profesor_id aquí porque lo tomaremos del path parameter 
    en el endpoint (ej. POST /profesores/{profesor_id}/restricciones).
    """
    pass

class RestriccionUpdate(BaseModel):
    """Esquema para actualizar una restricción manualmente (PATCH)."""
    dia_semana: Optional[DiaSemana] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None

class RestriccionResponse(RestriccionBase):
    """Esquema de salida para devolver los datos al cliente."""
    id: int
    profesor_id: int
    model_config = ConfigDict(from_attributes=True)


# Esquemas para importación masiva 

class ImportacionRestriccionesResponse(BaseModel):
    """Respuesta estructurada para el flujo de ingesta de Excel (Drop & Load)."""
    registros_creados: int = Field(default=0)
    registros_eliminados: int = Field(default=0)
    errores: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)