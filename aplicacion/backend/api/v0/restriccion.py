from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.restriccion import RestriccionCreate, RestriccionUpdate, RestriccionOut
from crud.restriccion import (
    create_restriccion,
    get_restricciones,
    get_restriccion_by_id,
    update_restriccion,
    delete_restriccion,
    get_restricciones_filtradas,
)
from constants.enums import TipoRestriccionEnum
from typing import Optional

router = APIRouter(prefix="/v0/restricciones", tags=["Restricciones"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[RestriccionOut],
    summary="Listar restricciones",
    description="Obtiene una lista de restricciones con paginación y filtros opcionales"
)
def listar_restricciones(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    tipo: Optional[TipoRestriccionEnum] = Query(None, description="Filtrar por tipo de restricción"),
    asignatura_id: Optional[int] = Query(None, ge=1, description="Filtrar por asignatura"),
    profesor_id: Optional[int] = Query(None, ge=1, description="Filtrar por profesor"),
    aula_id: Optional[int] = Query(None, ge=1, description="Filtrar por aula"),
    db: Session = Depends(get_db)
):
    # Si hay filtros, usar función filtrada, sino usar paginación simple
    if tipo or asignatura_id or profesor_id or aula_id:
        return get_restricciones_filtradas(
            db, 
            tipo=tipo.value if tipo else None,
            asignatura_id=asignatura_id,
            profesor_id=profesor_id,
            aula_id=aula_id,
            skip=skip,
            limit=limit
        )
    else:
        return get_restricciones(db, skip=skip, limit=limit)

@router.get("/{restriccion_id}", 
    response_model=RestriccionOut,
    summary="Obtener restricción por ID",
    description="Obtiene los detalles de una restricción específica",
    responses={
        200: {"description": "Restricción encontrada"},
        404: {"description": "Restricción no encontrada"}
    }
)
def obtener_restriccion(restriccion_id: int, db: Session = Depends(get_db)):
    restriccion = get_restriccion_by_id(db, restriccion_id)
    if not restriccion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Restricción con ID {restriccion_id} no encontrada"
        )
    return restriccion

@router.post("/", 
    response_model=RestriccionOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva restricción",
    description="Crea una nueva restricción en el sistema",
    responses={
        201: {"description": "Restricción creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_restriccion(restriccion: RestriccionCreate, db: Session = Depends(get_db)):
    nueva_restriccion, error = create_restriccion(db, restriccion)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nueva_restriccion

@router.put("/{restriccion_id}", 
    response_model=RestriccionOut,
    summary="Actualizar restricción",
    description="Actualiza los datos de una restricción existente",
    responses={
        200: {"description": "Restricción actualizada exitosamente"},
        404: {"description": "Restricción no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_restriccion(
    restriccion_id: int, 
    datos: RestriccionUpdate, 
    db: Session = Depends(get_db)
):
    restriccion_actualizada, error = update_restriccion(db, restriccion_id, datos)
    if error:
        if "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return restriccion_actualizada

@router.delete("/{restriccion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar restricción",
    description="Elimina una restricción del sistema",
    responses={
        204: {"description": "Restricción eliminada exitosamente"},
        404: {"description": "Restricción no encontrada"}
    }
)
def eliminar_restriccion(restriccion_id: int, db: Session = Depends(get_db)):
    success, error = delete_restriccion(db, restriccion_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Restricción con ID {restriccion_id} no encontrada"
        )
