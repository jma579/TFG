from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_asignaturas(db: Session):
    return db.query(models.Asignatura).all()

def get_asignatura(db: Session, asignatura_id: int):
    return db.query(models.Asignatura).filter(models.Asignatura.id == asignatura_id).first()

def create_asignatura(db: Session, asignatura: schemas.AsignaturaCreate):
    nueva = models.Asignatura(**asignatura.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def delete_asignatura(db: Session, asignatura_id: int):
    asignatura = get_asignatura(db, asignatura_id)
    if asignatura:
        db.delete(asignatura)
        db.commit()
    return asignatura
