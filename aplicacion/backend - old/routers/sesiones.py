from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import sesiones

router = APIRouter(prefix="/sesiones", tags=["Sesiones"])


# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /sesiones → Listar todas
@router.get("/", response_model=list[schemas.Sesion])
def listar(db: Session = Depends(get_db)):
    return sesiones.get_sesiones(db)


# GET /sesiones/{id} → Obtener una
@router.get("/{id}", response_model=schemas.Sesion)
def obtener(id: int, db: Session = Depends(get_db)):
    sesion = sesiones.get_sesion(db, id)
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return sesion


# POST /sesiones → Crear nueva
@router.post("/", response_model=schemas.Sesion)
def crear(sesion: schemas.SesionCreate, db: Session = Depends(get_db)):
    return sesiones.create_sesion(db, sesion)


# DELETE /sesiones/{id} → Eliminar
@router.delete("/{id}", response_model=schemas.Sesion)
def eliminar(id: int, db: Session = Depends(get_db)):
    return sesiones.delete_sesion(db, id)
