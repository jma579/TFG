from sqlalchemy.orm import Session
from models.profesor import Profesor, ProfesorAsignatura
from schemas.profesor import ProfesorCreate, ProfesorAsignaturaCreate

# ---------- PROFESOR ----------

def create_profesor(db: Session, profesor: ProfesorCreate) -> Profesor:
    nuevo = Profesor(**profesor.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

def get_profesores(db: Session) -> list[Profesor]:
    return db.query(Profesor).all()

def get_profesor_by_id(db: Session, profesor_id: int) -> Profesor | None:
    return db.query(Profesor).filter(Profesor.id == profesor_id).first()

def update_profesor(db: Session, profesor_id: int, profesor: ProfesorCreate) -> Profesor | None:
    db_prof = get_profesor_by_id(db, profesor_id)
    if db_prof:
        for key, value in profesor.model_dump().items():
            setattr(db_prof, key, value)
        db.commit()
        db.refresh(db_prof)
    return db_prof

def delete_profesor(db: Session, profesor_id: int) -> bool:
    db_prof = get_profesor_by_id(db, profesor_id)
    if db_prof:
        db.delete(db_prof)
        db.commit()
        return True
    return False

# ---------- PROFESOR-ASIGNATURA ----------

def create_profesor_asignatura(db: Session, rel: ProfesorAsignaturaCreate) -> ProfesorAsignatura:
    nueva_rel = ProfesorAsignatura(**rel.model_dump())
    db.add(nueva_rel)
    db.commit()
    db.refresh(nueva_rel)
    return nueva_rel

def delete_profesor_asignatura(db: Session, rel_id: int) -> bool:
    rel = db.query(ProfesorAsignatura).filter(ProfesorAsignatura.id == rel_id).first()
    if rel:
        db.delete(rel)
        db.commit()
        return True
    return False
