from sqlalchemy.orm import Session
from models.aula import Aula
from schemas.aula import AulaCreate

def create_aula(db: Session, aula: AulaCreate) -> Aula:
    nueva_aula = Aula(**aula.model_dump())
    db.add(nueva_aula)
    db.commit()
    db.refresh(nueva_aula)
    return nueva_aula

def get_aulas(db: Session) -> list[Aula]:
    return db.query(Aula).all()

def get_aula_by_id(db: Session, aula_id: int) -> Aula | None:
    return db.query(Aula).filter(Aula.id == aula_id).first()

def update_aula(db: Session, aula_id: int, aula: AulaCreate) -> Aula | None:
    db_aula = get_aula_by_id(db, aula_id)
    if db_aula:
        for key, value in aula.model_dump().items():
            setattr(db_aula, key, value)
        db.commit()
        db.refresh(db_aula)
    return db_aula

def delete_aula(db: Session, aula_id: int) -> bool:
    db_aula = get_aula_by_id(db, aula_id)
    if db_aula:
        db.delete(db_aula)
        db.commit()
        return True
    return False
