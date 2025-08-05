from sqlalchemy.orm import Session
from models.grado import Grado
from schemas.grado import GradoCreate

def create_grado(db: Session, grado: GradoCreate) -> Grado:
    nuevo_grado = Grado(**grado.model_dump())
    db.add(nuevo_grado)
    db.commit()
    db.refresh(nuevo_grado)
    return nuevo_grado

def get_grados(db: Session) -> list[Grado]:
    return db.query(Grado).all()

def get_grado_by_id(db: Session, grado_id: int) -> Grado | None:
    return db.query(Grado).filter(Grado.id == grado_id).first()

def update_grado(db: Session, grado_id: int, grado: GradoCreate) -> Grado | None:
    db_grado = get_grado_by_id(db, grado_id)
    if db_grado:
        for key, value in grado.model_dump().items():
            setattr(db_grado, key, value)
        db.commit()
        db.refresh(db_grado)
    return db_grado

def delete_grado(db: Session, grado_id: int) -> bool:
    db_grado = get_grado_by_id(db, grado_id)
    if db_grado:
        db.delete(db_grado)
        db.commit()
        return True
    return False
