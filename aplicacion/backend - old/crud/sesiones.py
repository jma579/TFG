from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_sesiones(db: Session):
    return db.query(models.Sesion).all()

def get_sesion(db: Session, sesion_id: int):
    return db.query(models.Sesion).filter(models.Sesion.id == sesion_id).first()

def create_sesion(db: Session, sesion: schemas.SesionCreate):
    nueva = models.Sesion(**sesion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def delete_sesion(db: Session, sesion_id: int):
    sesion = get_sesion(db, sesion_id)
    if sesion:
        db.delete(sesion)
        db.commit()
    return sesion
