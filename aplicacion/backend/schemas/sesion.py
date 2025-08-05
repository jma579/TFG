from pydantic import BaseModel
from datetime import time

class SesionBase(BaseModel):
    asignatura_id: int
    profesor_id: int
    aula_id: int
    dia: str
    hora_inicio: time
    hora_fin: time

class SesionCreate(SesionBase):
    pass

class SesionOut(SesionBase):
    id: int

    class Config:
        from_attributes  = True
