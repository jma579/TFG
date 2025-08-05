from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def create_asignatura_grado(db: Session, relacion: schemas.AsignaturaGradoCreate):
    nueva = models.AsignaturaGrado(**relacion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva
