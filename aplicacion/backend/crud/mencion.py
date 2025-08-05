from sqlalchemy.orm import Session
from models.mencion import Mencion
from schemas.mencion import MencionCreate

def create_mencion(db: Session, mencion: MencionCreate) -> Mencion:
    nueva_mencion = Mencion(**mencion.model_dump())
    db.add(nueva_mencion)
    db.commit()
    db.refresh(nueva_mencion)
    return nueva_mencion

def get_menciones(db: Session) -> list[Mencion]:
    return db.query(Mencion).all()

def get_mencion_by_id(db: Session, mencion_id: int) -> Mencion | None:
    return db.query(Mencion).filter(Mencion.id == mencion_id).first()

def update_mencion(db: Session, mencion_id: int, mencion: MencionCreate) -> Mencion | None:
    db_mencion = get_mencion_by_id(db, mencion_id)
    if db_mencion:
        for key, value in mencion.model_dump().items():
            setattr(db_mencion, key, value)
        db.commit()
        db.refresh(db_mencion)
    return db_mencion

def delete_mencion(db: Session, mencion_id: int) -> bool:
    db_mencion = get_mencion_by_id(db, mencion_id)
    if db_mencion:
        db.delete(db_mencion)
        db.commit()
        return True
    return False
