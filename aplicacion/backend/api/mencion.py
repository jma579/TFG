from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.mencion import MencionCreate, MencionOut
from crud.mencion import *

router = APIRouter(prefix="/menciones", tags=["Menciones"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[MencionOut])
def listar_menciones(db: Session = Depends(get_db)):
    return get_menciones(db)

@router.get("/{mencion_id}", response_model=MencionOut)
def obtener_mencion(mencion_id: int, db: Session = Depends(get_db)):
    mencion = get_mencion_by_id(db, mencion_id)
    if not mencion:
        raise HTTPException(status_code=404, detail="Mención no encontrada")
    return mencion

@router.post("/", response_model=MencionOut, status_code=201)
def crear_mencion(mencion: MencionCreate, db: Session = Depends(get_db)):
    return create_mencion(db, mencion)

@router.put("/{mencion_id}", response_model=MencionOut)
def actualizar_mencion(mencion_id: int, datos: MencionCreate, db: Session = Depends(get_db)):
    mencion = update_mencion(db, mencion_id, datos)
    if not mencion:
        raise HTTPException(status_code=404, detail="Mención no encontrada")
    return mencion

@router.delete("/{mencion_id}", status_code=204)
def eliminar_mencion(mencion_id: int, db: Session = Depends(get_db)):
    ok = delete_mencion(db, mencion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Mención no encontrada")
