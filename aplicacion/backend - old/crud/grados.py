from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_grados(db: Session):
    return db.query(models.Grado).all()

def get_grado(db: Session, grado_id: int):
    return db.query(models.Grado).filter(models.Grado.id == grado_id).first()

def create_grado(db: Session, grado: schemas.GradoCreate):
    nuevo = models.Grado(**grado.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def delete_grado(db: Session, grado_id: int):
    grado = get_grado(db, grado_id)
    if grado:
        db.delete(grado)
        db.commit()
    return grado
