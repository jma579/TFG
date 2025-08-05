from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import aulas


router = APIRouter(prefix="/aulas", tags=["Aulas"])


# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /aulas → Listar todas
@router.get("/", response_model=list[schemas.Aula])
def listar(db: Session = Depends(get_db)):
    return aulas.get_aulas(db)


# GET /aulas/{id} → Obtener una
@router.get("/{id}", response_model=schemas.Aula)
def obtener(id: int, db: Session = Depends(get_db)):
    aula = aulas.get_aula(db, id)
    if not aula:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return aula


# POST /aulas → Crear nueva
@router.post("/", response_model=schemas.Aula)
def crear(aula: schemas.AulaCreate, db: Session = Depends(get_db)):
    return aulas.create_aula(db, aula)


# DELETE /aulas/{id} → Eliminar
@router.delete("/{id}", response_model=schemas.Aula)
def eliminar(id: int, db: Session = Depends(get_db)):
    return aulas.delete_aula(db, id)
