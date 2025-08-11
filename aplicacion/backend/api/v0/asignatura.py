from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.asignatura import *
from crud.asignatura import *
from constants.enums import CuatrimestreEnum
from typing import Optional

router = APIRouter(prefix="/v0/asignaturas", tags=["Asignaturas"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[AsignaturaOut],
    summary="Listar asignaturas",
    description="Obtiene una lista de asignaturas con paginación"
)
def listar_asignaturas(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    return get_asignaturas(db, skip=skip, limit=limit)

@router.get("/{asignatura_id}", 
    response_model=AsignaturaOut,
    summary="Obtener asignatura por ID",
    description="Obtiene los detalles de una asignatura específica",
    responses={
        200: {"description": "Asignatura encontrada"},
        404: {"description": "Asignatura no encontrada"}
    }
)
def obtener_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    asignatura = get_asignatura_by_id(db, asignatura_id)
    if not asignatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Asignatura con ID {asignatura_id} no encontrada"
        )
    return asignatura

@router.post("/", 
    response_model=AsignaturaOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva asignatura",
    description="Crea una nueva asignatura en el sistema",
    responses={
        201: {"description": "Asignatura creada exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_asignatura(asignatura: AsignaturaCreate, db: Session = Depends(get_db)):
    nueva_asignatura, error = create_asignatura(db, asignatura)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nueva_asignatura

@router.put("/{asignatura_id}", 
    response_model=AsignaturaOut,
    summary="Actualizar asignatura",
    description="Actualiza los datos de una asignatura existente",
    responses={
        200: {"description": "Asignatura actualizada exitosamente"},
        404: {"description": "Asignatura no encontrada"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_asignatura(
    asignatura_id: int, 
    datos: AsignaturaUpdate, 
    db: Session = Depends(get_db)
):
    asignatura_actualizada, error = update_asignatura(db, asignatura_id, datos)
    if error:
        if "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return asignatura_actualizada

@router.delete("/{asignatura_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar asignatura",
    description="Elimina una asignatura del sistema",
    responses={
        204: {"description": "Asignatura eliminada exitosamente"},
        404: {"description": "Asignatura no encontrada"}
    }
)
def eliminar_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    success, error = delete_asignatura(db, asignatura_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Asignatura con ID {asignatura_id} no encontrada"
        )

# ========== ENDPOINTS PARA RELACIONES ==========

@router.post("/{asignatura_id}/grados/{grado_id}", 
    status_code=status.HTTP_201_CREATED,
    summary="Asignar asignatura a grado",
    description="Crea una relación entre una asignatura y un grado"
)
def asignar_asignatura_a_grado(
    asignatura_id: int, 
    grado_id: int, 
    db: Session = Depends(get_db)
):
    # Crear el objeto de datos para la relación
    relacion_data = AsignaturaGradoCreate(asignatura_id=asignatura_id, grado_id=grado_id)
    relacion, error = create_asignatura_grado(db, relacion_data)
    if error:
        if "no encontrada" in error.lower() or "no encontrado" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"message": "Asignatura asignada al grado exitosamente", "id": relacion.id}

@router.delete("/relaciones/grado/{relacion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar relación asignatura-grado",
    description="Elimina una relación específica entre asignatura y grado por ID de relación"
)
def eliminar_relacion_asignatura_grado(
    relacion_id: int, 
    db: Session = Depends(get_db)
):
    success, error = delete_asignatura_grado(db, relacion_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

@router.post("/{asignatura_id}/menciones/{mencion_id}", 
    status_code=status.HTTP_201_CREATED,
    summary="Asignar asignatura a mención",
    description="Crea una relación entre una asignatura y una mención"
)
def asignar_asignatura_a_mencion(
    asignatura_id: int, 
    mencion_id: int, 
    db: Session = Depends(get_db)
):
    # Crear el objeto de datos para la relación
    relacion_data = AsignaturaMencionCreate(asignatura_id=asignatura_id, mencion_id=mencion_id)
    relacion, error = create_asignatura_mencion(db, relacion_data)
    if error:
        if "no encontrada" in error.lower() or "no encontrado" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"message": "Asignatura asignada a la mención exitosamente", "id": relacion.id}

@router.delete("/relaciones/mencion/{relacion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar relación asignatura-mención",
    description="Elimina una relación específica entre asignatura y mención por ID de relación"
)
def eliminar_relacion_asignatura_mencion(
    relacion_id: int, 
    db: Session = Depends(get_db)
):
    success, error = delete_asignatura_mencion(db, relacion_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

# ========== ENDPOINTS DE CONSULTA ==========

@router.get("/grado/{grado_id}", 
    response_model=list[AsignaturaOut],
    summary="Obtener asignaturas por grado",
    description="Lista todas las asignaturas asociadas a un grado específico"
)
def obtener_asignaturas_por_grado(grado_id: int, db: Session = Depends(get_db)):
    asignaturas = get_asignaturas_by_grado_id(db, grado_id)
    return asignaturas

@router.get("/mencion/{mencion_id}", 
    response_model=list[AsignaturaOut],
    summary="Obtener asignaturas por mención",
    description="Lista todas las asignaturas asociadas a una mención específica"
)
def obtener_asignaturas_por_mencion(mencion_id: int, db: Session = Depends(get_db)):
    asignaturas = get_asignaturas_by_mencion_id(db, mencion_id)
    return asignaturas
