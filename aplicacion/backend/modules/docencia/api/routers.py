"""
Endpoints REST para el Módulo de Docencia.

Gestión de grupos docentes, sesiones, horarios y dashboard de consulta.
"""

from fastapi import APIRouter, Depends, Query, Path, Body, status, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path as PathlibPath
import tempfile

from db.session import get_db
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate, GrupoDocenteOut, GrupoDocenteList
)
from modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, SesionOut, SesionList, SesionWithConflictosOut,
    SesionBatchRequest, SesionBatchResponse
)
from modules.docencia.schemas.dashboard import (
    ResumenHorarioOut, DashboardFiltros
)
from modules.conflictos.schemas.conflicto import ConflictoOut
from modules.docencia.services.grupo_docente_service import grupo_docente_service
from modules.docencia.services.sesion_service import sesion_service
from modules.docencia.services.dashboard_service import dashboard_service
from constants.enums import (
    TipoGrupoDocente, ModalidadSesion, TipoRecurrencia, DiaSemana, Periodo
)
from modules.docencia.schemas.horarios import (
    HorarioTemporalOut,
    HorarioTemporalConfirmIn,
    HorarioConfirmResponse,
)
from modules.docencia.services.horarios_pipeline_service import HorariosPipelineService

horarios_pipeline_service = HorariosPipelineService()

router = APIRouter(
    responses={
        404: {"description": "Recurso no encontrado"},
        409: {"description": "Conflicto - Recurso duplicado o con dependencias"},
        422: {"description": "Error de validación"}
    }
)


# Grupos Docentes

@router.get(
    "/grupos-docentes",
    response_model=GrupoDocenteList,
    summary="Listar grupos docentes",
    description="Listar grupos docentes con filtros opcionales (asignatura_id, tipo, curso, turno) y paginación.",
    tags=["Grupos Docentes"]
)
def listar_grupos_docentes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asignatura_id: Optional[int] = Query(None, gt=0),
    tipo: Optional[TipoGrupoDocente] = Query(None),
    curso: Optional[int] = Query(None, ge=1, le=6),
    turno: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    # Obtener grupos del service
    items, total = grupo_docente_service.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        asignatura_id=asignatura_id,
        tipo=tipo,
        curso=curso,
        turno=turno
    )
    
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return GrupoDocenteList(
        total=total,
        items=items,
        page=page,
        size=limit
    )


@router.get(
    "/grupos-docentes/{id}",
    response_model=GrupoDocenteOut,
    summary="Obtener grupo docente por ID",
    tags=["Grupos Docentes"]
)
def obtener_grupo_docente(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return grupo_docente_service.get_by_id(db, id)


@router.get(
    "/grupos-docentes/asignatura/{asignatura_id}/codigo/{codigo}",
    response_model=GrupoDocenteOut,
    summary="Obtener grupo docente por asignatura y código",
    description="Obtener un grupo docente por su constraint único (asignatura_id, codigo).",
    tags=["Grupos Docentes"]
)
def obtener_grupo_por_asignatura_codigo(
    asignatura_id: int = Path(..., gt=0),
    codigo: str = Path(..., min_length=1, max_length=50),
    db: Session = Depends(get_db)
):
    return grupo_docente_service.get_by_asignatura_codigo(db, asignatura_id, codigo)


@router.post(
    "/grupos-docentes",
    response_model=GrupoDocenteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo grupo docente",
    description="Crear un nuevo grupo docente. El código se normaliza a MAYÚSCULAS. La combinación (asignatura_id, codigo) debe ser única.",
    tags=["Grupos Docentes"]
)
def crear_grupo_docente(
    grupo: GrupoDocenteCreate = Body(...),
    db: Session = Depends(get_db)
):
    return grupo_docente_service.create(db, grupo)


@router.put(
    "/grupos-docentes/{id}",
    response_model=GrupoDocenteOut,
    summary="Actualizar grupo docente",
    description="Actualizar un grupo docente existente (actualización parcial). Los campos curso y turno pueden ser null.",
    tags=["Grupos Docentes"]
)
def actualizar_grupo_docente(
    id: int = Path(..., ge=1),
    grupo: GrupoDocenteUpdate = Body(...),
    db: Session = Depends(get_db)
):
    return grupo_docente_service.update(db, id, grupo)


@router.delete(
    "/grupos-docentes/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar grupo docente",
    description="Eliminar un grupo docente (DELETE físico). No se puede eliminar si tiene sesiones asociadas.",
    tags=["Grupos Docentes"]
)
def eliminar_grupo_docente(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    grupo_docente_service.delete(db, id)
    return None


# Sesiones

@router.get(
    "/sesiones",
    response_model=SesionList,
    summary="Listar sesiones",
    description="Listar sesiones con filtros opcionales (programa_id, curso, periodo, aula_id, mencion_id) y paginación.",
    tags=["Sesiones"]
)
def get_sesiones(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    programa_id: Optional[int] = Query(None),
    curso: Optional[int] = Query(None),
    periodo: Optional[Periodo] = Query(None),
    aula_id: Optional[int] = Query(None),
    mencion: Optional[str] = Query(None)
):
    items, total = sesion_service.get_multi(
        db, 
        skip=skip, 
        limit=limit,
        programa_id=programa_id,
        curso=curso,
        periodo=periodo,
        aula_id=aula_id,
        mencion=mencion
    )
    
    # Calcular la página actual basada en skip y limit
    pagina_actual = (skip // limit) + 1 if limit > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": pagina_actual,
        "size": limit
    }


@router.get(
    "/sesiones/{id}",
    response_model=SesionOut,
    summary="Obtener sesión por ID",
    description="Obtener una sesión específica por su ID (incluye profesores asignados).",
    tags=["Sesiones"]
)
def obtener_sesion(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return sesion_service.get_by_id(db, id)


@router.post(
    "/sesiones",
    response_model=SesionWithConflictosOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sesión",
    description="Crear una nueva sesión con profesores asignados. Valida horarios según tipo_recurrencia.",
    tags=["Sesiones"]
)
def crear_sesion(
    sesion: SesionCreate = Body(...),
    db: Session = Depends(get_db)
):
    return sesion_service.create(db, sesion)


@router.put(
    "/sesiones/{id}",
    response_model=SesionWithConflictosOut,
    summary="Actualizar sesión",
    description="Actualizar una sesión existente (actualización parcial). Si se cambia tipo_recurrencia, los campos de horario deben proporcionarse completos.",
    tags=["Sesiones"]
)
def actualizar_sesion(
    id: int = Path(..., ge=1),
    sesion: SesionUpdate = Body(...),
    db: Session = Depends(get_db)
):
    return sesion_service.update(db, id, sesion)

@router.post(
    "/sesiones/validate-batch",
    response_model=List[ConflictoOut],
    summary="Simular cambios y validar horario completo",
    description="Recibe el estado actual del frontend (creados, modificados, borrados), simula su aplicación y devuelve todos los conflictos del horario. No guarda cambios.",
    tags=["Sesiones"]
)
def validar_batch_sesiones(
    payload: SesionBatchRequest,
    db: Session = Depends(get_db)
):
    return sesion_service.simulate_batch(db, payload)

@router.delete(
    "/sesiones/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar sesión",
    description="Eliminar una sesión (DELETE físico). Las asignaciones profesor-sesion se eliminan automáticamente.",
    tags=["Sesiones"]
)
def eliminar_sesion(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    sesion_service.delete(db, id)
    return None

@router.post(
    "/sesiones/batch",
    response_model=SesionBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Procesar lote de cambios en sesiones",
    description="Permite crear, actualizar y eliminar múltiples sesiones en una sola operación. Devuelve las sesiones con sus conflictos detectados.",
    tags=["Sesiones"]
)
def batch_update_sesiones(
    payload: SesionBatchRequest,
    db: Session = Depends(get_db)
):
    response_data = SesionBatchResponse(
        created=[],
        updated=[],
        deleted_ids=payload.deleted
    )

    try:
        for id_sesion in payload.deleted:
            try:
                sesion_service.delete(db, id_sesion)
            except HTTPException as e:
                if e.status_code != 404:
                    raise e

        for item in payload.updated:
            update_data = item.model_dump(exclude={'id'}, exclude_unset=True)
            if not update_data:
                continue
            
            schema_update = SesionUpdate(**update_data)
            
            res_update = sesion_service.update(db, item.id, schema_update)
            response_data.updated.append(res_update)

        for create_item in payload.created:
            res_create = sesion_service.create(db, create_item)
            response_data.created.append(res_create)
        
        db.commit()
        
        return response_data

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando el lote: {str(e)}"
        )
    

# Horarios (Pipeline Extracción)

@router.post(
    "/horarios/extract",
    response_model=HorarioTemporalOut,
    status_code=status.HTTP_200_OK,
    summary="Extraer horario desde PDF",
    description="Sube un PDF de horario académico y obtiene un horario temporal editable con validación de asignaturas mediante Fuzzy Matching.",
    tags=["Horarios"],
)
async def extract_horario(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido debe ser un PDF",
        )

    try:
        original_name = file.filename or "horario.pdf"
        suffix = PathlibPath(original_name).suffix or ".pdf"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = PathlibPath(tmp.name)
            contenido = await file.read()
            tmp.write(contenido)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se ha podido almacenar temporalmente el PDF de horario",
        ) from exc

    try:
        horario_temporal = horarios_pipeline_service.extraer_horario(db=db, pdf_path=tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return horario_temporal

@router.post(
    "/horarios/refine",
    response_model=HorarioTemporalOut,
    status_code=status.HTTP_200_OK,
    summary="Refinar matching de asignaturas",
    description="Recalcula las sugerencias de asignaturas (Fuzzy Match) usando metadatos actualizados del usuario.",
    tags=["Horarios"],
)
async def refine_horario_matching(
    payload: HorarioTemporalConfirmIn,
    db: Session = Depends(get_db),
):
    return horarios_pipeline_service.refinar_matching(db, payload)

@router.post(
    "/horarios/confirm",
    response_model=HorarioConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirmar horario editado",
    description="Confirma un horario académico extraído y editado, creando grupos docentes, aulas y sesiones.",
    tags=["Horarios"],
)
async def confirm_horario(
    payload: HorarioTemporalConfirmIn,
    db: Session = Depends(get_db),
):
    return horarios_pipeline_service.confirmar_horario(db, payload)

@router.delete(
    "/horarios",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un horario completo",
    description="Elimina todas las sesiones asociadas a un programa, curso y cuatrimestre específico."
)
def delete_horario(
    programa_id: int = Query(..., gt=0),
    curso: int = Query(..., ge=1),
    cuatrimestre: int = Query(..., ge=1, le=2),
    mencion: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    num_deleted = sesion_service.borrar_horario(
        db, programa_id, curso, cuatrimestre, mencion
    )
    
    if num_deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron sesiones para los criterios especificados."
        )
        
    return {
        "status": "success",
        "message": f"Se han eliminado {num_deleted} sesiones correctamente.",
        "deleted_count": num_deleted
    }


# Dashboard

@router.get(
    "/dashboard/resumen",
    response_model=List[ResumenHorarioOut],
    summary="Obtener resumen del dashboard",
    description="Vista agregada de horarios activos por programa, curso, cuatrimestre y mención con estado de salud y estadísticas.",
    tags=["Dashboard"]
)
def get_dashboard_resumen(
    db: Session = Depends(get_db),
    programa_id: Optional[int] = Query(None, gt=0),
    curso: Optional[int] = Query(None, ge=1),
    periodo: Optional[Periodo] = Query(None)
):
    filtros = DashboardFiltros(
        programa_id=programa_id,
        curso=curso,
        periodo=periodo
    )
    return dashboard_service.get_resumen(db, filtros)
