from pydantic import BaseModel

class MencionBase(BaseModel):
    nombre: str
    grado_id: int

class MencionCreate(MencionBase):
    pass

class MencionOut(MencionBase):
    id: int

    class Config:
        from_attributes  = True
