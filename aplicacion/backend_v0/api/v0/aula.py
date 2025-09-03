from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.aula import AulaCreate, AulaUpdate, AulaOut
from crud.aula import (
    create_aula,
    get_aulas,
    get_aula_by_id,
    update_aula,
    delete_aula,
    get_aulas_by_tipo,
)
from constants.enums import TipoAulaEnum

router = APIRouter(prefix="/v0/aulas", tags=["Aulas"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[AulaOut],
    summary="Listar aulas",
    description="Obtiene una lista de aulas con paginación"
)
def listar_aulas(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    return get_aulas(db, skip=skip, limit=limit)

@router.get("/tipo/{tipo_aula}", 
    response_model=list[AulaOut],
    summary="Obtener aulas por tipo",
    description="Lista todas las aulas de un tipo específico"
)
def obtener_aulas_por_tipo(
    tipo_aula: TipoAulaEnum,
    db: Session = Depends(get_db)
):
    aulas = get_aulas_by_tipo(db, tipo_aula.value)
    return aulas

@router.get("/{aula_id}", 
    response_model=AulaOut,
    summary="Obtener aula por ID",
    description="Obtiene los detalles de un aula específica",
    responses={
        200: {"description": "Aula encontrada"},
        404: {"description": "Aula no encontrada"}
    }
)
def obtener_aula(aula_id: int, db: Session = Depends(get_db)):
    aula = get_aula_by_id(db, aula_id)
    if not aula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Aula con ID {aula_id} no encontrada"
        )
    return aula

@router.post("/", 
    response_model=AulaOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva aula",
    description="Crea una nueva aula en el sistema",
    responses={
        201: {"description": "Aula creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_aula(aula: AulaCreate, db: Session = Depends(get_db)):
    nueva_aula, error = create_aula(db, aula)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nueva_aula

@router.put("/{aula_id}", 
    response_model=AulaOut,
    summary="Actualizar aula",
    description="Actualiza los datos de un aula existente",
    responses={
        200: {"description": "Aula actualizada exitosamente"},
        404: {"description": "Aula no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_aula(
    aula_id: int, 
    datos: AulaUpdate, 
    db: Session = Depends(get_db)
):
    aula_actualizada, error = update_aula(db, aula_id, datos)
    if error:
        if "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return aula_actualizada

@router.delete("/{aula_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar aula",
    description="Elimina un aula del sistema",
    responses={
        204: {"description": "Aula eliminada exitosamente"},
        404: {"description": "Aula no encontrada"}
    }
)
def eliminar_aula(aula_id: int, db: Session = Depends(get_db)):
    success, error = delete_aula(db, aula_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Aula con ID {aula_id} no encontrada"
        )
