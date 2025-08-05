from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from schemas import schemas
from crud import menciones


router = APIRouter(prefix="/menciones", tags=["Menciones"])

# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /menciones → Listar todas
@router.get("/", response_model=list[schemas.Mencion])
def listar(db: Session = Depends(get_db)):
    return menciones.get_menciones(db)


# GET /menciones/{id} → Obtener una
@router.get("/{id}", response_model=schemas.Mencion)
def obtener(id: int, db: Session = Depends(get_db)):
    mencion = menciones.get_mencion(db, id)
    if not mencion:
        raise HTTPException(status_code=404, detail="Mención no encontrada")
    return mencion

# POST /menciones → Crear nueva
@router.post("/", response_model=schemas.Mencion)
def crear(mencion: schemas.MencionCreate, db: Session = Depends(get_db)):
    return menciones.create_mencion(db, mencion)


# DELETE /menciones/{id} → Eliminar una
@router.delete("/{id}", response_model=schemas.Mencion)
def eliminar(id: int, db: Session = Depends(get_db)):
    return menciones.delete_mencion(db, id)
