from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.restriccion import RestriccionCreate, RestriccionOut
from crud.restriccion import *

router = APIRouter(prefix="/restricciones", tags=["Restricciones"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[RestriccionOut])
def listar_restricciones(db: Session = Depends(get_db)):
    return get_restricciones(db)

@router.get("/{restriccion_id}", response_model=RestriccionOut)
def obtener_restriccion(restriccion_id: int, db: Session = Depends(get_db)):
    restriccion = get_restriccion_by_id(db, restriccion_id)
    if not restriccion:
        raise HTTPException(status_code=404, detail="Restricción no encontrada")
    return restriccion

@router.post("/", response_model=RestriccionOut, status_code=201)
def crear_restriccion(restriccion: RestriccionCreate, db: Session = Depends(get_db)):
    return create_restriccion(db, restriccion)

@router.put("/{restriccion_id}", response_model=RestriccionOut)
def actualizar_restriccion(restriccion_id: int, datos: RestriccionCreate, db: Session = Depends(get_db)):
    restriccion = update_restriccion(db, restriccion_id, datos)
    if not restriccion:
        raise HTTPException(status_code=404, detail="Restricción no encontrada")
    return restriccion

@router.delete("/{restriccion_id}", status_code=204)
def eliminar_restriccion(restriccion_id: int, db: Session = Depends(get_db)):
    ok = delete_restriccion(db, restriccion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Restricción no encontrada")
