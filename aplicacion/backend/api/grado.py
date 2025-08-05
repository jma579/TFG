from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas.grado import GradoCreate, GradoOut
from crud.grado import (
    create_grado,
    get_grados,
    get_grado_by_id,
    update_grado,
    delete_grado,
)

router = APIRouter(prefix="/grados", tags=["Grados"])

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[GradoOut])
def listar_grados(db: Session = Depends(get_db)):
    return get_grados(db)

@router.get("/{grado_id}", response_model=GradoOut)
def obtener_grado(grado_id: int, db: Session = Depends(get_db)):
    grado = get_grado_by_id(db, grado_id)
    if not grado:
        raise HTTPException(status_code=404, detail="Grado no encontrado")
    return grado

@router.post("/", response_model=GradoOut, status_code=201)
def crear_grado(grado: GradoCreate, db: Session = Depends(get_db)):
    return create_grado(db, grado)

@router.put("/{grado_id}", response_model=GradoOut)
def actualizar_grado(grado_id: int, datos: GradoCreate, db: Session = Depends(get_db)):
    grado = update_grado(db, grado_id, datos)
    if not grado:
        raise HTTPException(status_code=404, detail="Grado no encontrado")
    return grado

@router.delete("/{grado_id}", status_code=204)
def eliminar_grado(grado_id: int, db: Session = Depends(get_db)):
    ok = delete_grado(db, grado_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Grado no encontrado")
