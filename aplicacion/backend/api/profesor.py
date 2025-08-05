from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.profesor import ProfesorCreate, ProfesorOut
from crud.profesor import *

router = APIRouter(prefix="/profesores", tags=["Profesores"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[ProfesorOut])
def listar_profesores(db: Session = Depends(get_db)):
    return get_profesores(db)

@router.get("/{profesor_id}", response_model=ProfesorOut)
def obtener_profesor(profesor_id: int, db: Session = Depends(get_db)):
    profesor = get_profesor_by_id(db, profesor_id)
    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return profesor

@router.post("/", response_model=ProfesorOut, status_code=201)
def crear_profesor(profesor: ProfesorCreate, db: Session = Depends(get_db)):
    return create_profesor(db, profesor)

@router.put("/{profesor_id}", response_model=ProfesorOut)
def actualizar_profesor(profesor_id: int, datos: ProfesorCreate, db: Session = Depends(get_db)):
    profesor = update_profesor(db, profesor_id, datos)
    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return profesor

@router.delete("/{profesor_id}", status_code=204)
def eliminar_profesor(profesor_id: int, db: Session = Depends(get_db)):
    ok = delete_profesor(db, profesor_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
