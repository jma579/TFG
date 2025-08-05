from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import profesores

router = APIRouter(prefix="/profesores", tags=["Profesores"])

# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /profesores → Listar todos
@router.get("/", response_model=list[schemas.Profesor])
def listar_profesores(db: Session = Depends(get_db)):
    return profesores.get_profesores(db)


# GET /profesores/{id} → Obtener uno
@router.get("/{profesor_id}", response_model=schemas.Profesor)
def obtener_profesor(profesor_id: int, db: Session = Depends(get_db)):
    profe = profesores.get_profesor(db, profesor_id)
    if not profe:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return profe


# POST /profesores → Crear nuevo
@router.post("/", response_model=schemas.Profesor)
def crear_profesor(profesor: schemas.ProfesorCreate, db: Session = Depends(get_db)):
    return profesores.create_profesor(db, profesor)


# DELETE /profesores/{id} → Eliminar
@router.delete("/{profesor_id}", response_model=schemas.Profesor)
def eliminar_profesor(profesor_id: int, db: Session = Depends(get_db)):
    profe = profesores.delete_profesor(db, profesor_id)
    if not profe:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return profe
