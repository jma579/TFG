from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.mencion import MencionCreate, MencionUpdate, MencionOut
from crud.mencion import (
    create_mencion,
    get_menciones,
    get_mencion_by_id,
    get_menciones_by_grado_id,
    update_mencion,
    delete_mencion,
)

router = APIRouter(prefix="/v0/menciones", tags=["Menciones"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[MencionOut],
    summary="Listar menciones",
    description="Obtiene una lista de menciones con paginación"
)
def listar_menciones(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    return get_menciones(db, skip=skip, limit=limit)

@router.get("/{mencion_id}", 
    response_model=MencionOut,
    summary="Obtener mención por ID",
    description="Obtiene los detalles de una mención específica",
    responses={
        200: {"description": "Mención encontrada"},
        404: {"description": "Mención no encontrada"}
    }
)
def obtener_mencion(mencion_id: int, db: Session = Depends(get_db)):
    mencion = get_mencion_by_id(db, mencion_id)
    if not mencion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Mención con ID {mencion_id} no encontrada"
        )
    return mencion

@router.post("/", 
    response_model=MencionOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva mención",
    description="Crea una nueva mención en el sistema",
    responses={
        201: {"description": "Mención creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_mencion(mencion: MencionCreate, db: Session = Depends(get_db)):
    nueva_mencion, error = create_mencion(db, mencion)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nueva_mencion

@router.put("/{mencion_id}", 
    response_model=MencionOut,
    summary="Actualizar mención",
    description="Actualiza los datos de una mención existente",
    responses={
        200: {"description": "Mención actualizada exitosamente"},
        404: {"description": "Mención no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_mencion(
    mencion_id: int, 
    datos: MencionUpdate, 
    db: Session = Depends(get_db)
):
    mencion_actualizada, error = update_mencion(db, mencion_id, datos)
    if error:
        if "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return mencion_actualizada

@router.delete("/{mencion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar mención",
    description="Elimina una mención del sistema",
    responses={
        204: {"description": "Mención eliminada exitosamente"},
        404: {"description": "Mención no encontrada"}
    }
)
def eliminar_mencion(mencion_id: int, db: Session = Depends(get_db)):
    success, error = delete_mencion(db, mencion_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Mención con ID {mencion_id} no encontrada"
        )

# ========== ENDPOINTS DE CONSULTA ==========

@router.get("/grado/{grado_id}", 
    response_model=list[MencionOut],
    summary="Obtener menciones por grado",
    description="Lista todas las menciones asociadas a un grado específico"
)
def obtener_menciones_por_grado(grado_id: int, db: Session = Depends(get_db)):
    menciones = get_menciones_by_grado_id(db, grado_id)
    return menciones
