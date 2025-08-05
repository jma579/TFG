from sqlalchemy.orm import Session
from models.sesion import Sesion
from schemas.sesion import SesionCreate

def create_sesion(db: Session, sesion: SesionCreate) -> Sesion:
    nueva_sesion = Sesion(**sesion.model_dump())
    db.add(nueva_sesion)
    db.commit()
    db.refresh(nueva_sesion)
    return nueva_sesion

def get_sesiones(db: Session) -> list[Sesion]:
    return db.query(Sesion).all()

def get_sesion_by_id(db: Session, sesion_id: int) -> Sesion | None:
    return db.query(Sesion).filter(Sesion.id == sesion_id).first()

def update_sesion(db: Session, sesion_id: int, sesion: SesionCreate) -> Sesion | None:
    db_sesion = get_sesion_by_id(db, sesion_id)
    if db_sesion:
        for key, value in sesion.model_dump().items():
            setattr(db_sesion, key, value)
        db.commit()
        db.refresh(db_sesion)
    return db_sesion

def delete_sesion(db: Session, sesion_id: int) -> bool:
    db_sesion = get_sesion_by_id(db, sesion_id)
    if db_sesion:
        db.delete(db_sesion)
        db.commit()
        return True
    return False
