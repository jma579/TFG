from pydantic import BaseModel
from typing import Dict

class ProfesorBase(BaseModel):
    nombre: str
    disponibilidad: Dict  # formato JSON

class ProfesorCreate(ProfesorBase):
    pass

class ProfesorOut(ProfesorBase):
    id: int

    class Config:
        from_attributes  = True

class ProfesorAsignaturaBase(BaseModel):
    profesor_id: int
    asignatura_id: int

class ProfesorAsignaturaCreate(ProfesorAsignaturaBase):
    pass

class ProfesorAsignaturaOut(ProfesorAsignaturaBase):
    id: int

    class Config:
        from_attributes  = True
