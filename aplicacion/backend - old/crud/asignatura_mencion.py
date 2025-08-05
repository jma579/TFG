from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def create_asignatura_mencion(db: Session, relacion: schemas.AsignaturaMencionCreate):
    nueva = models.AsignaturaMencion(**relacion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva
