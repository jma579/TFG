from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.sesion import SesionCreate, SesionOut
from crud.sesion import *

router = APIRouter(prefix="/sesiones", tags=["Sesiones"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[SesionOut])
def listar_sesiones(db: Session = Depends(get_db)):
    return get_sesiones(db)

@router.get("/{sesion_id}", response_model=SesionOut)
def obtener_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = get_sesion_by_id(db, sesion_id)
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return sesion

@router.post("/", response_model=SesionOut, status_code=201)
def crear_sesion(sesion: SesionCreate, db: Session = Depends(get_db)):
    return create_sesion(db, sesion)

@router.put("/{sesion_id}", response_model=SesionOut)
def actualizar_sesion(sesion_id: int, datos: SesionCreate, db: Session = Depends(get_db)):
    sesion = update_sesion(db, sesion_id, datos)
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return sesion

@router.delete("/{sesion_id}", status_code=204)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    ok = delete_sesion(db, sesion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
