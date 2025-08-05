from pydantic import BaseModel

class AulaBase(BaseModel):
    nombre: str
    capacidad: int
    tipo: str

class AulaCreate(AulaBase):
    pass

class AulaOut(AulaBase):
    id: int

    class Config:
        from_attributes  = True
