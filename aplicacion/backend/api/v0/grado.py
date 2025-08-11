from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.grado import GradoCreate, GradoUpdate, GradoOut
from crud.grado import (
    create_grado,
    get_grados,
    get_grado_by_id,
    get_grado_by_nombre,
    update_grado,
    delete_grado,
)
from typing import Optional

router = APIRouter(prefix="/v0/grados", tags=["Grados"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[GradoOut],
    summary="Listar grados",
    description="Obtiene una lista de grados con paginación"
)
def listar_grados(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    return get_grados(db, skip=skip, limit=limit)

@router.get("/buscar", 
    response_model=GradoOut,
    summary="Buscar grado por nombre",
    description="Busca un grado específico por su nombre exacto"
)
def buscar_grado_por_nombre(
    nombre: str = Query(..., min_length=2, max_length=100, description="Nombre del grado a buscar"),
    db: Session = Depends(get_db)
):
    grado = get_grado_by_nombre(db, nombre)
    if not grado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Grado con nombre '{nombre}' no encontrado"
        )
    return grado

@router.get("/{grado_id}", 
    response_model=GradoOut,
    summary="Obtener grado por ID",
    description="Obtiene los detalles de un grado específico",
    responses={
        200: {"description": "Grado encontrado"},
        404: {"description": "Grado no encontrado"}
    }
)
def obtener_grado(grado_id: int, db: Session = Depends(get_db)):
    grado = get_grado_by_id(db, grado_id)
    if not grado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Grado con ID {grado_id} no encontrado"
        )
    return grado

@router.post("/", 
    response_model=GradoOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo grado",
    description="Crea un nuevo grado en el sistema",
    responses={
        201: {"description": "Grado creado exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_grado(grado: GradoCreate, db: Session = Depends(get_db)):
    nuevo_grado, error = create_grado(db, grado)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nuevo_grado

@router.put("/{grado_id}", 
    response_model=GradoOut,
    summary="Actualizar grado",
    description="Actualiza los datos de un grado existente",
    responses={
        200: {"description": "Grado actualizado exitosamente"},
        404: {"description": "Grado no encontrado"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_grado(
    grado_id: int, 
    datos: GradoUpdate, 
    db: Session = Depends(get_db)
):
    grado_actualizado, error = update_grado(db, grado_id, datos)
    if error:
        if "no encontrado" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return grado_actualizado

@router.delete("/{grado_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar grado",
    description="Elimina un grado del sistema",
    responses={
        204: {"description": "Grado eliminado exitosamente"},
        404: {"description": "Grado no encontrado"}
    }
)
def eliminar_grado(grado_id: int, db: Session = Depends(get_db)):
    success, error = delete_grado(db, grado_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Grado con ID {grado_id} no encontrado"
        )
