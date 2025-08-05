from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_menciones(db: Session):
    return db.query(models.Mencion).all()

def get_mencion(db: Session, mencion_id: int):
    return db.query(models.Mencion).filter(models.Mencion.id == mencion_id).first()

def create_mencion(db: Session, mencion: schemas.MencionCreate):
    nueva = models.Mencion(**mencion.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def delete_mencion(db: Session, mencion_id: int):
    mencion = get_mencion(db, mencion_id)
    if mencion:
        db.delete(mencion)
        db.commit()
    return mencion
