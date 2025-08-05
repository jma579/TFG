from pydantic import BaseModel

class GradoBase(BaseModel):
    nombre: str

class GradoCreate(GradoBase):
    pass

class GradoOut(GradoBase):
    id: int

    class Config:
        from_attributes  = True
