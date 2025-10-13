from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.profesor import ProfesorCreate, ProfesorUpdate, ProfesorOut, ProfesorAsignaturaCreate
from crud.profesor import (
    create_profesor,
    get_profesores,
    get_profesor_by_id,
    update_profesor,
    delete_profesor,
    create_profesor_asignatura,
    delete_profesor_asignatura,
    get_profesores_by_asignatura_id,
)

router = APIRouter(prefix="/v0/profesores", tags=["Profesores"])

# ========== ENDPOINTS PRINCIPALES ==========

@router.get("/", 
    response_model=list[ProfesorOut],
    summary="Listar profesores",
    description="Obtiene una lista de profesores con paginación"
)
def listar_profesores(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    db: Session = Depends(get_db)
):
    return get_profesores(db, skip=skip, limit=limit)

@router.get("/{profesor_id}", 
    response_model=ProfesorOut,
    summary="Obtener profesor por ID",
    description="Obtiene los detalles de un profesor específico",
    responses={
        200: {"description": "Profesor encontrado"},
        404: {"description": "Profesor no encontrado"}
    }
)
def obtener_profesor(profesor_id: int, db: Session = Depends(get_db)):
    profesor = get_profesor_by_id(db, profesor_id)
    if not profesor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Profesor con ID {profesor_id} no encontrado"
        )
    return profesor

@router.post("/", 
    response_model=ProfesorOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo profesor",
    description="Crea un nuevo profesor en el sistema",
    responses={
        201: {"description": "Profesor creado exitosamente"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def crear_profesor(profesor: ProfesorCreate, db: Session = Depends(get_db)):
    nuevo_profesor, error = create_profesor(db, profesor)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return nuevo_profesor

@router.put("/{profesor_id}", 
    response_model=ProfesorOut,
    summary="Actualizar profesor",
    description="Actualiza los datos de un profesor existente",
    responses={
        200: {"description": "Profesor actualizado exitosamente"},
        404: {"description": "Profesor no encontrado"},
        400: {"description": "Error en los datos proporcionados"}
    }
)
def actualizar_profesor(
    profesor_id: int, 
    datos: ProfesorUpdate, 
    db: Session = Depends(get_db)
):
    profesor_actualizado, error = update_profesor(db, profesor_id, datos)
    if error:
        if "no encontrado" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return profesor_actualizado

@router.delete("/{profesor_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar profesor",
    description="Elimina un profesor del sistema",
    responses={
        204: {"description": "Profesor eliminado exitosamente"},
        404: {"description": "Profesor no encontrado"}
    }
)
def eliminar_profesor(profesor_id: int, db: Session = Depends(get_db)):
    success, error = delete_profesor(db, profesor_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=error or f"Profesor con ID {profesor_id} no encontrado"
        )

# ========== ENDPOINTS PARA RELACIONES ==========

@router.post("/{profesor_id}/asignaturas/{asignatura_id}", 
    status_code=status.HTTP_201_CREATED,
    summary="Asignar profesor a asignatura",
    description="Crea una relación entre un profesor y una asignatura"
)
def asignar_profesor_a_asignatura(
    profesor_id: int, 
    asignatura_id: int, 
    db: Session = Depends(get_db)
):
    # Crear el objeto de datos para la relación
    relacion_data = ProfesorAsignaturaCreate(profesor_id=profesor_id, asignatura_id=asignatura_id)
    relacion, error = create_profesor_asignatura(db, relacion_data)
    if error:
        if "no encontrado" in error.lower() or "no encontrada" in error.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"message": "Profesor asignado a la asignatura exitosamente", "id": relacion.id}

@router.delete("/relaciones/{relacion_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar relación profesor-asignatura",
    description="Elimina una relación específica entre profesor y asignatura por ID de relación"
)
def eliminar_relacion_profesor_asignatura(
    relacion_id: int, 
    db: Session = Depends(get_db)
):
    success, error = delete_profesor_asignatura(db, relacion_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

# ========== ENDPOINTS DE CONSULTA ==========

@router.get("/asignatura/{asignatura_id}", 
    response_model=list[ProfesorOut],
    summary="Obtener profesores por asignatura",
    description="Lista todos los profesores que imparten una asignatura específica"
)
def obtener_profesores_por_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    profesores = get_profesores_by_asignatura_id(db, asignatura_id)
    return profesores
