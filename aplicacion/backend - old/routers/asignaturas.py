from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import asignaturas

router = APIRouter(prefix="/asignaturas", tags=["Asignaturas"])

# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET /asignaturas → Listar todas
@router.get("/", response_model=list[schemas.Asignatura])
def listar(db: Session = Depends(get_db)):
    return asignaturas.get_asignaturas(db)


# GET /asignaturas/{id} → Obtener una
@router.get("/{id}", response_model=schemas.Asignatura)
def obtener(id: int, db: Session = Depends(get_db)):
    asignatura = asignaturas.get_asignatura(db, id)
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura


# POST /asignaturas → Crear nueva
@router.post("/", response_model=schemas.Asignatura)
def crear(asignatura: schemas.AsignaturaCreate, db: Session = Depends(get_db)):
    return asignaturas.create_asignatura(db, asignatura)


# DELETE /asignaturas/{id} → Eliminar
@router.delete("/{id}", response_model=schemas.Asignatura)
def eliminar(id: int, db: Session = Depends(get_db)):
    return asignaturas.delete_asignatura(db, id)
