from pydantic import BaseModel

class AsignaturaBase(BaseModel):
    nombre: str
    creditos: int
    horas_semanales: int
    curso: int
    cuatrimestre: int

class AsignaturaCreate(AsignaturaBase):
    pass

class AsignaturaOut(AsignaturaBase):
    id: int

    class Config:
        from_attributes  = True

class AsignaturaGradoBase(BaseModel):
    asignatura_id: int
    grado_id: int

class AsignaturaGradoCreate(AsignaturaGradoBase):
    pass

class AsignaturaGradoOut(AsignaturaGradoBase):
    id: int

    class Config:
        from_attributes  = True

class AsignaturaMencionBase(BaseModel):
    asignatura_id: int
    mencion_id: int

class AsignaturaMencionCreate(AsignaturaMencionBase):
    pass

class AsignaturaMencionOut(AsignaturaMencionBase):
    id: int

    class Config:
        from_attributes  = True
