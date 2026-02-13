"""
Schemas relacionados con el Dashboard de la docencia.
"""

from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from constants.enums import Periodo

class EstadoHorario(str, Enum):
    OK = "OK"
    CONFLICTO = "CONFLICTO"

class ResumenHorarioOut(BaseModel):
    programa_id: int
    programa_nombre: str
    curso: int
    periodo: Optional[Periodo] = None
    
    menciones: List[str] = Field(default_factory=list)

    total_asignaturas: int
    total_sesiones: int
    
    estado: EstadoHorario
    conflictos_count: int
    
    ultima_actualizacion: datetime

    class Config:
        from_attributes = True

class DashboardFiltros(BaseModel):
    programa_id: Optional[int] = None
    curso: Optional[int] = None
    periodo: Optional[Periodo] = None