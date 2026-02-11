from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from constants.enums import Periodo

class EstadoHorario(str, Enum):
    """
    Estado calculado del bloque de horario.
    Coincide con los badges del frontend.
    """
    OK = "OK"
    CONFLICTO = "CONFLICTO"

class ResumenHorarioOut(BaseModel):
    """
    Modelo de salida para una tarjeta del Dashboard.
    Representa un bloque único de (Programa + Curso + Cuatrimestre + [Mención]).
    """
    # Identificación del bloque
    programa_id: int
    programa_nombre: str
    curso: int
    periodo: Optional[Periodo] = None
    
    # Itinerario
    # Si la lista está vacía [], el frontend lo interpreta como "Curso General/Troncal".
    # Si tiene datos, son las menciones específicas (ej: ["Computación"]).
    menciones: List[str] = Field(default_factory=list)

    # Métricas
    total_asignaturas: int
    total_sesiones: int
    
    # Estado y Salud
    estado: EstadoHorario
    conflictos_count: int
    
    # Metadatos
    ultima_actualizacion: datetime

    class Config:
        from_attributes = True

class DashboardFiltros(BaseModel):
    """
    Esquema para recibir filtros opcionales desde el frontend (query params).
    """
    programa_id: Optional[int] = None
    curso: Optional[int] = None
    periodo: Optional[Periodo] = None