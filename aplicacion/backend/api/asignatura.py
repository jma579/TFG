from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.asignatura import *
from crud.asignatura import *

router = APIRouter(prefix="/asignaturas", tags=["Asignaturas"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[AsignaturaOut])
def listar_asignaturas(db: Session = Depends(get_db)):
    return get_asignaturas(db)

@router.get("/{asignatura_id}", response_model=AsignaturaOut)
def obtener_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    asignatura = get_asignatura_by_id(db, asignatura_id)
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura

@router.post("/", response_model=AsignaturaOut, status_code=201)
def crear_asignatura(asignatura: AsignaturaCreate, db: Session = Depends(get_db)):
    return create_asignatura(db, asignatura)

@router.put("/{asignatura_id}", response_model=AsignaturaOut)
def actualizar_asignatura(asignatura_id: int, datos: AsignaturaCreate, db: Session = Depends(get_db)):
    asignatura = update_asignatura(db, asignatura_id, datos)
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    return asignatura

@router.delete("/{asignatura_id}", status_code=204)
def eliminar_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    ok = delete_asignatura(db, asignatura_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
