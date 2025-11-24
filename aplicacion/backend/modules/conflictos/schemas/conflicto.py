from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto

class ConflictoOut(BaseModel):
    id: int
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    estado: EstadoConflicto
    sesion_id: int
    sesion_2_id: Optional[int] = None
    descripcion: Optional[str] = None
    hash_deteccion: str
    model_config = ConfigDict(from_attributes=True)
