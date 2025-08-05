from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_restricciones(db: Session):
    return db.query(models.Restriccion).all()

def get_restriccion(db: Session, restriccion_id: int):
    return db.query(models.Restriccion).filter(models.Restriccion.id == restriccion_id).first()

def create_restriccion(db: Session, restriccion: schemas.RestriccionCreate):
    nueva = models.Restriccion(**restriccion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def delete_restriccion(db: Session, restriccion_id: int):
    r = get_restriccion(db, restriccion_id)
    if r:
        db.delete(r)
        db.commit()
    return r
