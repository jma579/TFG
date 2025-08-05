from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import grados


router = APIRouter(prefix="/grados", tags=["Grados"])


# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /grados → Listar todos
@router.get("/", response_model=list[schemas.Grado])
def listar(db: Session = Depends(get_db)):
    return grados.get_grados(db)


# GET /grados/{id} → Obtener uno
@router.get("/{id}", response_model=schemas.Grado)
def obtener(id: int, db: Session = Depends(get_db)):
    return grados.get_grado(db, id)


# POST /grados → Crear nuevo
@router.post("/", response_model=schemas.Grado)
def crear(grado: schemas.GradoCreate, db: Session = Depends(get_db)):
    return grados.create_grado(db, grado)


# DELETE /grados/{id} → Eliminar
@router.delete("/{id}", response_model=schemas.Grado)
def eliminar(id: int, db: Session = Depends(get_db)):
    return grados.delete_grado(db, id)
