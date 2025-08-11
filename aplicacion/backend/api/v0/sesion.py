from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.sesion import SesionCreate, SesionUpdate, SesionOut
from crud.sesion import (
    create_sesion,
    get_sesiones,
    get_sesiones_with_relations,
    get_sesion_by_id,
    get_sesion_by_id_with_relations,
    update_sesion,
    delete_sesion,
    get_sesiones_by_profesor,
    get_sesiones_by_asignatura,
    get_sesiones_by_aula,
)
from constants.enums import DiaSemanaEnum
from typing import Optional

router = APIRouter(prefix="/v0/sesiones", tags=["Sesiones"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[SesionOut],
    summary="Listar sesiones",
    description="Obtiene una lista de sesiones con paginación y opción de incluir relaciones"
)
def listar_sesiones(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    incluir_relaciones: bool = Query(False, description="Incluir datos de asignatura, profesor y aula"),
    db: Session = Depends(get_db)
):
    if incluir_relaciones:
        return get_sesiones_with_relations(db, skip=skip, limit=limit)
    else:
        return get_sesiones(db, skip=skip, limit=limit)

@router.get("/{sesion_id}", 
    response_model=SesionOut,
    summary="Obtener sesión por ID",
    description="Obtiene los detalles de una sesión específica",
    responses={
        200: {"description": "Sesión encontrada"},
        404: {"description": "Sesión no encontrada"}
    }
)
def obtener_sesion(
    sesion_id: int,
    incluir_relaciones: bool = Query(False, description="Incluir datos de asignatura, profesor y aula"),
    db: Session = Depends(get_db)
):
    if incluir_relaciones:
        sesion = get_sesion_by_id_with_relations(db, sesion_id)
    else:
        sesion = get_sesion_by_id(db, sesion_id)
    
    if not sesion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Sesión con ID {sesion_id} no encontrada"
        )
    return sesion

@router.post("/", 
    response_model=SesionOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sesión",
    description="Crea una nueva sesión en el sistema",
    responses={
        201: {"description": "Sesión creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_sesion(sesion: SesionCreate, db: Session = Depends(get_db)):
    nueva_sesion, error = create_sesion(db, sesion)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nueva_sesion

@router.put("/{sesion_id}", 
    response_model=SesionOut,
    summary="Actualizar sesión",
    description="Actualiza los datos de una sesión existente",
    responses={
        200: {"description": "Sesión actualizada exitosamente"},
        404: {"description": "Sesión no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_sesion(
    sesion_id: int, 
    datos: SesionUpdate, 
    db: Session = Depends(get_db)
):
    sesion_actualizada, error = update_sesion(db, sesion_id, datos)
    if error:
        if "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return sesion_actualizada

@router.delete("/{sesion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar sesión",
    description="Elimina una sesión del sistema",
    responses={
        204: {"description": "Sesión eliminada exitosamente"},
        404: {"description": "Sesión no encontrada"}
    }
)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    success, error = delete_sesion(db, sesion_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Sesión con ID {sesion_id} no encontrada"
        )

# ========== ENDPOINTS DE CONSULTA ==========

@router.get("/profesor/{profesor_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por profesor",
    description="Lista todas las sesiones de un profesor específico"
)
def obtener_sesiones_por_profesor(profesor_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_profesor(db, profesor_id)
    return sesiones

@router.get("/asignatura/{asignatura_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por asignatura",
    description="Lista todas las sesiones de una asignatura específica"
)
def obtener_sesiones_por_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_asignatura(db, asignatura_id)
    return sesiones

@router.get("/aula/{aula_id}", 
    response_model=list[SesionOut],
    summary="Obtener sesiones por aula",
    description="Lista todas las sesiones que se imparten en un aula específica"
)
def obtener_sesiones_por_aula(aula_id: int, db: Session = Depends(get_db)):
    sesiones = get_sesiones_by_aula(db, aula_id)
    return sesiones
