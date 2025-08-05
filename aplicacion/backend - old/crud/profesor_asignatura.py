from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def create_profesor_asignatura(db: Session, relacion: schemas.ProfesorAsignaturaCreate):
    nueva = models.ProfesorAsignatura(**relacion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva
