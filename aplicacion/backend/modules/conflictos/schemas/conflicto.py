"""
Esquemas Pydantic para la entidad Conflicto.

Responsabilidades:
- Definir la estructura de salida (Out) para la API.
- Definir esquemas de actualización de estado (ignorar/resolver).
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

from constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto


class ConflictoBase(BaseModel):
    """Campos comunes del conflicto."""
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    estado: EstadoConflicto
    descripcion: str


class ConflictoEstadoUpdateIn(BaseModel):
    """
    Schema para cambiar manualmente el estado de un conflicto.
    Ej: Marcar como IGNORADO o RESUELTO manualmente.
    """
    estado: EstadoConflicto


class ConflictoOut(ConflictoBase):
    """
    Schema de respuesta completo para un Conflicto.
    """
    id: int
    sesion_id: int = Field(..., description="ID de la sesión principal afectada")
    sesion_2_id: Optional[int] = Field(None, description="ID de la segunda sesión en conflicto (si existe)")
    
    # Recursos afectados
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    restriccion_id: Optional[int] = None
    
    # Metadatos
    hash_deteccion: str
    creado_en: datetime
    resuelto_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConflictoList(BaseModel):
    """
    Schema para respuestas de listado paginado de conflictos.
    """
    total: int
    items: List[ConflictoOut]
    page: int
    size: int