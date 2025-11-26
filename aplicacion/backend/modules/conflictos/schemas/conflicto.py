from typing import Optional, List
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

class ConflictoList(BaseModel):
    """Lista paginada de conflictos.

    Mantiene el mismo contrato que otros List del backend (total, items, page, size).
    """

    total: int
    items: List[ConflictoOut]
    page: int
    size: int


class ConflictoEstadoUpdateIn(BaseModel):
    """Payload de actualización de estado de un conflicto.

    Permite cambiar el estado a ABIERTO, RESUELTO o IGNORADO.
    """

    estado: EstadoConflicto
