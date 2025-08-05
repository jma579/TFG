from sqlalchemy.orm import Session
from models import models
from schemas import schemas

def get_aulas(db: Session):
    return db.query(models.Aula).all()

def get_aula(db: Session, aula_id: int):
    return db.query(models.Aula).filter(models.Aula.id == aula_id).first()

def create_aula(db: Session, aula: schemas.AulaCreate):
    nueva = models.Aula(**aula.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def delete_aula(db: Session, aula_id: int):
    aula = get_aula(db, aula_id)
    if aula:
        db.delete(aula)
        db.commit()
    return aula
