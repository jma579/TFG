from pydantic import BaseModel
from typing import Optional

class RestriccionBase(BaseModel):
    tipo: str
    valor: str  # JSON como texto
    asignatura_id: Optional[int] = None
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None

class RestriccionCreate(RestriccionBase):
    pass

class RestriccionOut(RestriccionBase):
    id: int

    class Config:
        from_attributes  = True
