from sqlalchemy.orm import Session
from models.asignatura import Asignatura, AsignaturaGrado, AsignaturaMencion
from schemas.asignatura import (
    AsignaturaCreate, AsignaturaGradoCreate, AsignaturaMencionCreate
)

# ---------- ASIGNATURA ----------

def create_asignatura(db: Session, asignatura: AsignaturaCreate) -> Asignatura:
    nueva = Asignatura(**asignatura.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def get_asignaturas(db: Session) -> list[Asignatura]:
    return db.query(Asignatura).all()

def get_asignatura_by_id(db: Session, asignatura_id: int) -> Asignatura | None:
    return db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()

def update_asignatura(db: Session, asignatura_id: int, asignatura: AsignaturaCreate) -> Asignatura | None:
    db_asig = get_asignatura_by_id(db, asignatura_id)
    if db_asig:
        for key, value in asignatura.model_dump().items():
            setattr(db_asig, key, value)
        db.commit()
        db.refresh(db_asig)
    return db_asig

def delete_asignatura(db: Session, asignatura_id: int) -> bool:
    db_asig = get_asignatura_by_id(db, asignatura_id)
    if db_asig:
        db.delete(db_asig)
        db.commit()
        return True
    return False

# ---------- ASIGNATURA-GRADO ----------

def create_asignatura_grado(db: Session, data: AsignaturaGradoCreate) -> AsignaturaGrado:
    rel = AsignaturaGrado(**data.model_dump())
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel

def delete_asignatura_grado(db: Session, rel_id: int) -> bool:
    rel = db.query(AsignaturaGrado).filter(AsignaturaGrado.id == rel_id).first()
    if rel:
        db.delete(rel)
        db.commit()
        return True
    return False

# ---------- ASIGNATURA-MENCION ----------

def create_asignatura_mencion(db: Session, data: AsignaturaMencionCreate) -> AsignaturaMencion:
    rel = AsignaturaMencion(**data.model_dump())
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel

def delete_asignatura_mencion(db: Session, rel_id: int) -> bool:
    rel = db.query(AsignaturaMencion).filter(AsignaturaMencion.id == rel_id).first()
    if rel:
        db.delete(rel)
        db.commit()
        return True
    return False
