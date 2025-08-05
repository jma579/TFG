from pydantic import BaseModel
from typing import Optional, List


# ───────────────────────────────
# Grado
# ───────────────────────────────
class GradoBase(BaseModel):
    nombre: str

class GradoCreate(GradoBase):
    pass

class Grado(GradoBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Mención
# ───────────────────────────────
class MencionBase(BaseModel):
    nombre: str
    grado_id: int

class MencionCreate(MencionBase):
    pass

class Mencion(MencionBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Asignatura
# ───────────────────────────────
class AsignaturaBase(BaseModel):
    nombre: str
    creditos: Optional[int]
    horas_semanales: Optional[int]
    curso: Optional[int]
    cuatrimestre: Optional[int]

class AsignaturaCreate(AsignaturaBase):
    pass

class Asignatura(AsignaturaBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# AsignaturaGrado
# ───────────────────────────────
class AsignaturaGradoBase(BaseModel):
    asignatura_id: int
    grado_id: int

class AsignaturaGradoCreate(AsignaturaGradoBase):
    pass

class AsignaturaGrado(AsignaturaGradoBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# AsignaturaMencion
# ───────────────────────────────
class AsignaturaMencionBase(BaseModel):
    asignatura_id: int
    mencion_id: int

class AsignaturaMencionCreate(AsignaturaMencionBase):
    pass

class AsignaturaMencion(AsignaturaMencionBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Profesor
# ───────────────────────────────
class ProfesorBase(BaseModel):
    nombre: str
    disponibilidad: Optional[str] = None  # JSON como string

class ProfesorCreate(ProfesorBase):
    pass

class Profesor(ProfesorBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# ProfesorAsignatura
# ───────────────────────────────
class ProfesorAsignaturaBase(BaseModel):
    profesor_id: int
    asignatura_id: int

class ProfesorAsignaturaCreate(ProfesorAsignaturaBase):
    pass

class ProfesorAsignatura(ProfesorAsignaturaBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Aula
# ───────────────────────────────
class AulaBase(BaseModel):
    nombre: str
    capacidad: Optional[int] = None
    tipo: Optional[str] = None

class AulaCreate(AulaBase):
    pass

class Aula(AulaBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Sesion (horario)
# ───────────────────────────────
class SesionBase(BaseModel):
    asignatura_id: int
    profesor_id: int
    aula_id: int
    dia: str
    hora_inicio: str  # Formato HH:MM
    hora_fin: str     # Formato HH:MM

class SesionCreate(SesionBase):
    pass

class Sesion(SesionBase):
    id: int

    class Config:
        orm_mode = True


# ───────────────────────────────
# Restricción
# ───────────────────────────────
class RestriccionBase(BaseModel):
    tipo: str
    valor: Optional[str] = None  # JSON como texto
    asignatura_id: Optional[int] = None
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None

class RestriccionCreate(RestriccionBase):
    pass

class Restriccion(RestriccionBase):
    id: int

    class Config:
        orm_mode = True
