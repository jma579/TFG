from sqlalchemy.orm import Session
from models.restriccion import Restriccion
from schemas.restriccion import RestriccionCreate

def create_restriccion(db: Session, restriccion: RestriccionCreate) -> Restriccion:
    nueva_restriccion = Restriccion(**restriccion.model_dump())
    db.add(nueva_restriccion)
    db.commit()
    db.refresh(nueva_restriccion)
    return nueva_restriccion

def get_restricciones(db: Session) -> list[Restriccion]:
    return db.query(Restriccion).all()

def get_restriccion_by_id(db: Session, restriccion_id: int) -> Restriccion | None:
    return db.query(Restriccion).filter(Restriccion.id == restriccion_id).first()

def update_restriccion(db: Session, restriccion_id: int, restriccion: RestriccionCreate) -> Restriccion | None:
    db_restriccion = get_restriccion_by_id(db, restriccion_id)
    if db_restriccion:
        for key, value in restriccion.model_dump().items():
            setattr(db_restriccion, key, value)
        db.commit()
        db.refresh(db_restriccion)
    return db_restriccion

def delete_restriccion(db: Session, restriccion_id: int) -> bool:
    db_restriccion = get_restriccion_by_id(db, restriccion_id)
    if db_restriccion:
        db.delete(db_restriccion)
        db.commit()
        return True
    return False
