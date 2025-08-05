from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.aula import AulaCreate, AulaOut
from crud.aula import *

router = APIRouter(prefix="/aulas", tags=["Aulas"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[AulaOut])
def listar_aulas(db: Session = Depends(get_db)):
    return get_aulas(db)

@router.get("/{aula_id}", response_model=AulaOut)
def obtener_aula(aula_id: int, db: Session = Depends(get_db)):
    aula = get_aula_by_id(db, aula_id)
    if not aula:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return aula

@router.post("/", response_model=AulaOut, status_code=201)
def crear_aula(aula: AulaCreate, db: Session = Depends(get_db)):
    return create_aula(db, aula)

@router.put("/{aula_id}", response_model=AulaOut)
def actualizar_aula(aula_id: int, datos: AulaCreate, db: Session = Depends(get_db)):
    aula = update_aula(db, aula_id, datos)
    if not aula:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return aula

@router.delete("/{aula_id}", status_code=204)
def eliminar_aula(aula_id: int, db: Session = Depends(get_db)):
    ok = delete_aula(db, aula_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
