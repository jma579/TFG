from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_profesores(db: Session):
    return db.query(models.Profesor).all()

def get_profesor(db: Session, profesor_id: int):
    return db.query(models.Profesor).filter(models.Profesor.id == profesor_id).first()

def create_profesor(db: Session, profesor: schemas.ProfesorCreate):
    nuevo = models.Profesor(**profesor.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def delete_profesor(db: Session, profesor_id: int):
    profesor = get_profesor(db, profesor_id)
    if profesor:
        db.delete(profesor)
        db.commit()
    return profesor
