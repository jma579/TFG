"""
Endpoints REST API para el módulo de Docencia.

Define los endpoints para gestionar:
- GrupoDocente: Grupos de docencia (teoría, práctica, laboratorio, etc.)
- Sesion: Sesiones de clase programadas

Responsabilidades:
- Definir rutas HTTP (GET, POST, PUT, DELETE)
- Validar entrada (automático con Pydantic)
- Inyectar dependencias (DB session, paginación)
- Documentar API (OpenAPI/Swagger)
- Serializar respuestas a JSON
"""

from fastapi import APIRouter, Depends, Query, Path, Body, status, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path as PathlibPath
import tempfile

from db.session import get_db
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate, GrupoDocenteOut, GrupoDocenteList
)
from modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, SesionOut, SesionList, SesionWithConflictosOut
)
from modules.docencia.services.grupo_docente_service import grupo_docente_service
from modules.docencia.services.sesion_service import sesion_service
from constants.enums import (
    TipoGrupoDocente, ModalidadSesion, TipoRecurrencia, DiaSemana
)
from modules.docencia.schemas.horarios import (
    HorarioTemporalOut,
    HorarioTemporalConfirmIn,
    HorarioConfirmResponse,
)
from modules.docencia.services.horarios_pipeline_service import HorariosPipelineService

# Instancia compartida del servicio de pipeline de horarios.
# En esta fase es suficiente con un singleton simple a nivel de módulo.
horarios_pipeline_service = HorariosPipelineService()


# ============================================================
#  ROUTER: Configuración base
# ============================================================

router = APIRouter(
    # El prefijo se define en main.py al registrar el router
    responses={
        404: {"description": "Recurso no encontrado"},
        409: {"description": "Conflicto - Recurso duplicado o con dependencias"},
        422: {"description": "Error de validación"}
    }
)
"""
Router para endpoints del módulo Docencia.

- prefix: Todas las rutas empiezan con /v0/docencia (definido en main.py)
- tags: Agrupación en documentación Swagger
- responses: Documentación de errores comunes
"""


# ============================================================
#  ENDPOINTS DE GRUPO DOCENTE
# ============================================================

@router.get(
    "/grupos-docentes",
    response_model=GrupoDocenteList,
    summary="Listar grupos docentes",
    description="""
    Listar grupos docentes con filtros opcionales y paginación.
    
    **Filtros disponibles:**
    - `asignatura_id`: Filtrar por asignatura específica
    - `tipo`: Filtrar por tipo de grupo (teoria, practica, laboratorio, etc.)
    - `curso`: Filtrar por curso académico (1, 2, 3, 4, etc.)
    - `turno`: Filtrar por turno (búsqueda parcial, case-insensitive)
    
    **Paginación:**
    - `skip`: Número de registros a saltar (default: 0)
    - `limit`: Número máximo de registros (default: 100, max: 1000)
    
    **Ejemplo:**
    ```
    GET /grupos-docentes?asignatura_id=42&tipo=teoria&skip=0&limit=20
    ```
    
    **Respuesta:**
    ```json
    {
        "total": 8,
        "items": [...],
        "page": 1,
        "size": 20
    }
    ```
    """,
    tags=["Grupos Docentes"]
)
def listar_grupos_docentes(
    skip: int = Query(
        0,
        ge=0,
        description="Número de registros a saltar (offset para paginación)",
        examples=[0, 20, 40]
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Número máximo de registros a retornar",
        examples=[10, 20, 50, 100]
    ),
    asignatura_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por asignatura específica",
        examples=[1, 42, 123]
    ),
    tipo: Optional[TipoGrupoDocente] = Query(
        None,
        description="Filtrar por tipo de grupo",
        examples=["teoria", "practica", "laboratorio"]
    ),
    curso: Optional[int] = Query(
        None,
        ge=1,
        le=6,
        description="Filtrar por curso académico",
        examples=[1, 2, 3, 4]
    ),
    turno: Optional[str] = Query(
        None,
        min_length=1,
        description="Filtrar por turno (búsqueda parcial)",
        examples=["mañana", "tarde", "noche", "M"]
    ),
    db: Session = Depends(get_db)
):
    """
    Listar grupos docentes con filtros y paginación.
    
    Returns:
        GrupoDocenteList con total, items, page y size
    """
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
    
    # Calcular número de página actual
    page = (skip // limit) + 1 if limit > 0 else 1
    
    # Retornar schema de lista paginada
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
    description="""
    Obtener un grupo docente específico por su ID.
    
    **Errores:**
    - `404 Not Found`: Si el grupo no existe
    
    **Ejemplo:**
    ```
    GET /grupos-docentes/1
    ```
    """,
    responses={
        200: {
            "description": "Grupo docente encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "asignatura_id": 42,
                        "codigo": "T1",
                        "tipo": "teoria",
                        "curso": 3,
                        "turno": "mañana"
                    }
                }
            }
        },
        404: {
            "description": "Grupo docente no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Grupo docente con id 999 no encontrado"}
                }
            }
        }
    },
    tags=["Grupos Docentes"]
)
def obtener_grupo_docente(
    id: int = Path(
        ...,
        ge=1,
        description="ID único del grupo docente",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Obtener un grupo docente por su ID.
    
    Args:
        id: ID del grupo docente
        
    Returns:
        GrupoDocenteOut con los datos del grupo
        
    Raises:
        HTTPException 404: Si el grupo no existe
    """
    return grupo_docente_service.get_by_id(db, id)


@router.get(
    "/grupos-docentes/asignatura/{asignatura_id}/codigo/{codigo}",
    response_model=GrupoDocenteOut,
    summary="Obtener grupo docente por asignatura y código",
    description="""
    Obtener un grupo docente por su constraint único (asignatura_id, codigo).
    
    **Útil cuando conoces:**
    - La asignatura a la que pertenece
    - El código del grupo (T1, P1, L1, etc.)
    
    **Errores:**
    - `404 Not Found`: Si el grupo no existe para esa asignatura
    
    **Ejemplos:**
    ```
    GET /grupos-docentes/asignatura/42/codigo/T1
    GET /grupos-docentes/asignatura/15/codigo/LAB-1
    ```
    """,
    responses={
        200: {"description": "Grupo docente encontrado"},
        404: {
            "description": "Grupo no encontrado para esa asignatura",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Grupo con código 'T1' no encontrado para la asignatura con id 42"
                    }
                }
            }
        }
    },
    tags=["Grupos Docentes"]
)
def obtener_grupo_por_asignatura_codigo(
    asignatura_id: int = Path(
        ...,
        gt=0,
        description="ID de la asignatura",
        examples=[1, 42, 123]
    ),
    codigo: str = Path(
        ...,
        min_length=1,
        max_length=50,
        description="Código único del grupo dentro de la asignatura",
        examples=["T1", "P1", "LAB-1", "TEORIA-M"]
    ),
    db: Session = Depends(get_db)
):
    """
    Obtener un grupo docente por asignatura y código.
    
    Args:
        asignatura_id: ID de la asignatura
        codigo: Código del grupo
        
    Returns:
        GrupoDocenteOut con los datos del grupo
        
    Raises:
        HTTPException 404: Si el grupo no existe
    """
    return grupo_docente_service.get_by_asignatura_codigo(db, asignatura_id, codigo)


@router.post(
    "/grupos-docentes",
    response_model=GrupoDocenteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo grupo docente",
    description="""
    Crear un nuevo grupo docente.
    
    **Campos obligatorios:**
    - `asignatura_id`: ID de la asignatura (debe existir)
    - `codigo`: Código único del grupo dentro de la asignatura (ej: T1, P1, LAB-1)
    - `tipo`: Tipo de grupo (teoria, practica, laboratorio, seminario, taller, tutoria, examen)
    
    **Campos opcionales:**
    - `curso`: Curso académico del grupo (1-6)
    - `turno`: Turno del grupo (mañana, tarde, noche, etc.)
    
    **Validaciones:**
    - asignatura_id debe existir (FK)
    - (asignatura_id, codigo) debe ser único (case-insensitive)
    - Código se normaliza a MAYÚSCULAS automáticamente
    
    **Errores:**
    - `404 Not Found`: Si la asignatura no existe
    - `409 Conflict`: Si ya existe un grupo con ese código para esa asignatura
    - `422 Unprocessable Entity`: Si los datos son inválidos
    
    **Ejemplo:**
    ```json
    {
        "asignatura_id": 42,
        "codigo": "T1",
        "tipo": "teoria",
        "curso": 3,
        "turno": "mañana"
    }
    ```
    """,
    responses={
        201: {"description": "Grupo docente creado exitosamente"},
        404: {"description": "Asignatura no encontrada"},
        409: {"description": "Ya existe un grupo con ese código para esa asignatura"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Grupos Docentes"]
)
def crear_grupo_docente(
    grupo: GrupoDocenteCreate = Body(
        ...,
        examples=[
            {
                "asignatura_id": 42,
                "codigo": "T1",
                "tipo": "teoria",
                "curso": 3,
                "turno": "mañana"
            },
            {
                "asignatura_id": 42,
                "codigo": "P1",
                "tipo": "practica",
                "curso": 3,
                "turno": "tarde"
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo grupo docente.
    
    Args:
        grupo: Datos del grupo a crear
        
    Returns:
        GrupoDocenteOut con el grupo creado (incluye ID autogenerado)
        
    Raises:
        HTTPException 404: Si la asignatura no existe
        HTTPException 409: Si el código ya existe para esa asignatura
    """
    return grupo_docente_service.create(db, grupo)


@router.put(
    "/grupos-docentes/{id}",
    response_model=GrupoDocenteOut,
    summary="Actualizar grupo docente",
    description="""
    Actualizar un grupo docente existente (actualización parcial).
    
    **Comportamiento de campos:**
    - **Campo no incluido**: No se modifica
    - **Campo con valor**: Se actualiza
    - **Campo con `null`**: Se borra (pone a None) - solo curso y turno
    
    **Nota:** asignatura_id, codigo y tipo NO pueden ser null (obligatorios en DB)
    
    **Ejemplos de uso:**
    
    1. **Actualizar solo el turno:**
    ```json
    {"turno": "tarde"}
    ```
    
    2. **Borrar curso (poner a null):**
    ```json
    {"curso": null}
    ```
    
    3. **Cambiar tipo y turno:**
    ```json
    {
        "tipo": "laboratorio",
        "turno": "mañana"
    }
    ```
    
    4. **Mover a otra asignatura (cambia código si es necesario):**
    ```json
    {
        "asignatura_id": 50,
        "codigo": "T2"
    }
    ```
    
    **Validaciones:**
    - Grupo debe existir
    - Si se actualiza asignatura_id, validar que existe
    - Si se cambia asignatura_id O codigo, validar unicidad compuesta
    
    **Errores:**
    - `404 Not Found`: Si el grupo o la nueva asignatura no existen
    - `409 Conflict`: Si el nuevo (asignatura_id, codigo) ya existe
    - `422 Unprocessable Entity`: Si los datos son inválidos
    """,
    responses={
        200: {"description": "Grupo docente actualizado exitosamente"},
        404: {"description": "Grupo docente o asignatura no encontrados"},
        409: {"description": "El nuevo código ya existe para esa asignatura"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Grupos Docentes"]
)
def actualizar_grupo_docente(
    id: int = Path(
        ...,
        ge=1,
        description="ID del grupo docente a actualizar",
        examples=[1, 42, 123]
    ),
    grupo: GrupoDocenteUpdate = Body(
        ...,
        examples=[
            {
                "turno": "tarde"
            },
            {
                "tipo": "laboratorio",
                "curso": 2
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Actualizar un grupo docente existente.
    
    Args:
        id: ID del grupo a actualizar
        grupo: Datos a actualizar (solo campos proporcionados)
        
    Returns:
        GrupoDocenteOut con los datos actualizados
        
    Raises:
        HTTPException 404: Si el grupo o la nueva asignatura no existen
        HTTPException 409: Si el nuevo (asignatura_id, codigo) ya existe
    """
    return grupo_docente_service.update(db, id, grupo)


@router.delete(
    "/grupos-docentes/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar grupo docente (DELETE físico)",
    description="""
    Eliminar un grupo docente (DELETE físico de la base de datos).
    
    **IMPORTANTE:** NO es soft delete. El registro se elimina permanentemente.
    
    **Por qué DELETE físico:**
    - Esta entidad NO tiene campo 'activo'
    - Eliminación física permite mantener integridad de datos
    
    **Restricción:**
    - No se puede eliminar si tiene sesiones asociadas
    - En ese caso, retorna 409 Conflict
    
    **Errores:**
    - `404 Not Found`: Si el grupo no existe
    - `409 Conflict`: Si tiene sesiones asociadas (FK constraint)
    
    **Ejemplo:**
    ```
    DELETE /grupos-docentes/1
    ```
    
    **Respuesta:**
    - Status: `204 No Content`
    - Body: Vacío
    """,
    responses={
        204: {"description": "Grupo docente eliminado exitosamente"},
        404: {"description": "Grupo docente no encontrado"},
        409: {
            "description": "No se puede eliminar, tiene sesiones asociadas",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No se puede eliminar el grupo con id 1 porque tiene sesiones asociadas"
                    }
                }
            }
        }
    },
    tags=["Grupos Docentes"]
)
def eliminar_grupo_docente(
    id: int = Path(
        ...,
        ge=1,
        description="ID del grupo docente a eliminar",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Eliminar un grupo docente (DELETE físico).
    
    Args:
        id: ID del grupo a eliminar
        
    Returns:
        None (status 204 No Content)
        
    Raises:
        HTTPException 404: Si el grupo no existe
        HTTPException 409: Si tiene sesiones asociadas
    """
    grupo_docente_service.delete(db, id)
    return None


# ============================================================
#  ENDPOINTS DE SESION
# ============================================================

@router.get(
    "/sesiones",
    response_model=SesionList,
    summary="Listar sesiones",
    description="""
    Listar sesiones con filtros opcionales y paginación.
    
    **Filtros disponibles:**
    - `grupo_docente_id`: Filtrar por grupo docente específico
    - `aula_id`: Filtrar por aula específica
    - `modalidad`: Filtrar por modalidad (presencial, online, hibrida)
    - `tipo_recurrencia`: Filtrar por tipo (semanal, quincenal, mensual, puntual)
    - `dia_semana`: Filtrar por día de la semana (solo para recurrentes)
    
    **Paginación:**
    - `skip`: Número de registros a saltar (default: 0)
    - `limit`: Número máximo de registros (default: 100, max: 1000)
    
    **Ejemplo:**
    ```
    GET /sesiones?grupo_docente_id=1&modalidad=presencial&skip=0&limit=20
    ```
    
    **Respuesta:**
    ```json
    {
        "total": 15,
        "items": [
            {
                "id": 1,
                "grupo_docente_id": 1,
                "aula_id": 10,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": [...]
            }
        ],
        "page": 1,
        "size": 20
    }
    ```
    """,
    tags=["Sesiones"]
)
def listar_sesiones(
    skip: int = Query(
        0,
        ge=0,
        description="Número de registros a saltar (offset para paginación)",
        examples=[0, 20, 40]
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Número máximo de registros a retornar",
        examples=[10, 20, 50, 100]
    ),
    grupo_docente_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por grupo docente específico",
        examples=[1, 42, 123]
    ),
    aula_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por aula específica",
        examples=[1, 10, 200]
    ),
    modalidad: Optional[ModalidadSesion] = Query(
        None,
        description="Filtrar por modalidad",
        examples=["presencial", "online", "hibrida"]
    ),
    tipo_recurrencia: Optional[TipoRecurrencia] = Query(
        None,
        description="Filtrar por tipo de recurrencia",
        examples=["semanal", "quincenal", "mensual", "puntual"]
    ),
    dia_semana: Optional[DiaSemana] = Query(
        None,
        description="Filtrar por día de la semana (solo recurrentes)",
        examples=["lunes", "martes", "miercoles"]
    ),
    db: Session = Depends(get_db)
):
    """
    Listar sesiones con filtros y paginación.
    
    Returns:
        SesionList con total, items, page y size
    """
    # Obtener sesiones del service
    items, total = sesion_service.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        grupo_docente_id=grupo_docente_id,
        aula_id=aula_id,
        modalidad=modalidad,
        tipo_recurrencia=tipo_recurrencia,
        dia_semana=dia_semana
    )
    
    # Calcular número de página actual
    page = (skip // limit) + 1 if limit > 0 else 1
    
    # Retornar schema de lista paginada
    return SesionList(
        total=total,
        items=items,
        page=page,
        size=limit
    )


@router.get(
    "/sesiones/{id}",
    response_model=SesionOut,
    summary="Obtener sesión por ID",
    description="""
    Obtener una sesión específica por su ID (incluye profesores asignados).
    
    **Errores:**
    - `404 Not Found`: Si la sesión no existe
    
    **Ejemplo:**
    ```
    GET /sesiones/1
    ```
    
    **Respuesta:**
    ```json
    {
        "id": 1,
        "grupo_docente_id": 42,
        "aula_id": 10,
        "modalidad": "presencial",
        "tipo_recurrencia": "semanal",
        "dia_semana": "lunes",
        "hora_inicio": "09:00:00",
        "hora_fin": "11:00:00",
        "inicio": null,
        "fin": null,
        "profesores": [
            {
                "profesor_id": 5,
                "rol_en_sesion": "Docente",
                "nombre": "Juan",
                "apellidos": "García López"
            }
        ]
    }
    ```
    """,
    responses={
        200: {"description": "Sesión encontrada"},
        404: {
            "description": "Sesión no encontrada",
            "content": {
                "application/json": {
                    "example": {"detail": "Sesión con id 999 no encontrada"}
                }
            }
        }
    },
    tags=["Sesiones"]
)
def obtener_sesion(
    id: int = Path(
        ...,
        ge=1,
        description="ID único de la sesión",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Obtener una sesión por su ID.
    
    Args:
        id: ID de la sesión
        
    Returns:
        SesionOut con los datos de la sesión (incluye profesores)
        
    Raises:
        HTTPException 404: Si la sesión no existe
    """
    return sesion_service.get_by_id(db, id)


@router.post(
    "/sesiones",
    response_model=SesionWithConflictosOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sesión",
    description="""
    Crear una nueva sesión con profesores asignados.
    
    **Campos obligatorios:**
    - `grupo_docente_id`: ID del grupo docente (debe existir)
    - `aula_id`: ID del aula (debe existir)
    - `modalidad`: Modalidad (PRESENCIAL, ONLINE, HIBRIDA)
    - `tipo_recurrencia`: Tipo (SEMANAL, QUINCENAL, MENSUAL, PUNTUAL)
    
    **Si tipo_recurrencia es SEMANAL/QUINCENAL/MENSUAL:**
    - `dia_semana`: LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO
    - `hora_inicio`: Hora de inicio (HH:MM:SS)
    - `hora_fin`: Hora de fin (HH:MM:SS)
    - `inicio` y `fin` deben ser null
    
    **Si tipo_recurrencia es PUNTUAL:**
    - `inicio`: Fecha y hora de inicio (YYYY-MM-DDTHH:MM:SS)
    - `fin`: Fecha y hora de fin (YYYY-MM-DDTHH:MM:SS)
    - `dia_semana`, `hora_inicio` y `hora_fin` deben ser null
    
    **Profesores (opcional):**
    - Lista de profesores con `profesor_id` y `rol_en_sesion` opcional
    
    **Validaciones:**
    - grupo_docente_id debe existir (404)
    - aula_id debe existir (404)
    - Todos los profesor_id deben existir (404)
    - Campos de horario correctos según tipo_recurrencia (422)
    - hora_inicio < hora_fin (422)
    - inicio < fin (422)
    
    **TODO (Fase 3.5):**
    - Detectar conflictos de horarios (aula, profesor, grupo)
    - Retornar 409 si hay conflictos
    
    **Ejemplos:**
    
    1. **Sesión semanal:**
    ```json
    {
        "grupo_docente_id": 1,
        "aula_id": 10,
        "modalidad": "presencial",
        "tipo_recurrencia": "semanal",
        "dia_semana": "lunes",
        "hora_inicio": "09:00:00",
        "hora_fin": "11:00:00",
        "profesores": [
            {"profesor_id": 5, "rol_en_sesion": "Docente"}
        ]
    }
    ```
    
    2. **Sesión puntual:**
    ```json
    {
        "grupo_docente_id": 1,
        "aula_id": 10,
        "modalidad": "online",
        "tipo_recurrencia": "puntual",
        "inicio": "2025-10-25T09:00:00",
        "fin": "2025-10-25T11:00:00",
        "profesores": []
    }
    ```
    """,
    responses={
        201: {"description": "Sesión creada exitosamente"},
        404: {"description": "Grupo, aula o profesor no encontrado"},
        409: {"description": "Conflicto de horarios (TODO: Fase 3.5)"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Sesiones"]
)
def crear_sesion(
    sesion: SesionCreate = Body(
        ...,
        examples=[
            {
                "grupo_docente_id": 1,
                "aula_id": 10,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": [
                    {"profesor_id": 5, "rol_en_sesion": "Docente"}
                ]
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Crear una nueva sesión.
    
    Args:
        sesion: Datos de la sesión a crear (incluye profesores)
        
    Returns:
        SesionOut con la sesión creada (incluye ID y profesores)
        
    Raises:
        HTTPException 404: Si grupo, aula o algún profesor no existe
        HTTPException 409: Si hay conflictos de horarios (TODO: Fase 3.5)
        HTTPException 422: Si los datos son inválidos
    """
    return sesion_service.create(db, sesion)


@router.put(
    "/sesiones/{id}",
    response_model=SesionWithConflictosOut,
    summary="Actualizar sesión",
    description="""
    Actualizar una sesión existente (actualización parcial).
    
    **Comportamiento:**
    - Solo se actualizan los campos proporcionados
    - Campo no incluido: no se modifica
    - Campo con valor: se actualiza
    - Profesores: si se proporciona la lista, se reemplaza completamente
    
    **IMPORTANTE:**
    - Si se cambia `tipo_recurrencia`, los campos de horario correspondientes
      deben proporcionarse completos
    - Ejemplo: cambiar de SEMANAL a PUNTUAL requiere `inicio` y `fin`
    
    **Validaciones:**
    - Sesión debe existir (404)
    - Si se actualiza grupo_docente_id, validar que existe (404)
    - Si se actualiza aula_id, validar que existe (404)
    - Si se actualizan profesores, validar que todos existen (404)
    - Validar horarios según tipo_recurrencia (422)
    
    **TODO (Fase 3.5):**
    - Detectar conflictos si cambian horarios o recursos
    - Actualizar conflictos persistidos
    
    **Ejemplos:**
    
    1. **Cambiar solo el aula:**
    ```json
    {"aula_id": 20}
    ```
    
    2. **Cambiar horario:**
    ```json
    {
        "hora_inicio": "10:00:00",
        "hora_fin": "12:00:00"
    }
    ```
    
    3. **Reemplazar profesores:**
    ```json
    {
        "profesores": [
            {"profesor_id": 10, "rol_en_sesion": "Docente"},
            {"profesor_id": 15, "rol_en_sesion": "Ayudante"}
        ]
    }
    ```
    
    4. **Cambiar de semanal a puntual:**
    ```json
    {
        "tipo_recurrencia": "puntual",
        "inicio": "2025-10-25T09:00:00",
        "fin": "2025-10-25T11:00:00"
    }
    ```
    """,
    responses={
        200: {"description": "Sesión actualizada exitosamente"},
        404: {"description": "Sesión, grupo, aula o profesor no encontrado"},
        409: {"description": "Conflicto de horarios (TODO: Fase 3.5)"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Sesiones"]
)
def actualizar_sesion(
    id: int = Path(
        ...,
        ge=1,
        description="ID de la sesión a actualizar",
        examples=[1, 42, 123]
    ),
    sesion: SesionUpdate = Body(
        ...,
        examples=[
            {"aula_id": 20},
            {
                "hora_inicio": "10:00:00",
                "hora_fin": "12:00:00"
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Actualizar una sesión existente.
    
    Args:
        id: ID de la sesión a actualizar
        sesion: Datos a actualizar (solo campos proporcionados)
        
    Returns:
        SesionOut con los datos actualizados
        
    Raises:
        HTTPException 404: Si la sesión, grupo, aula o profesor no existen
        HTTPException 409: Si hay conflictos de horarios (TODO: Fase 3.5)
        HTTPException 422: Si los datos son inválidos
    """
    return sesion_service.update(db, id, sesion)


@router.delete(
    "/sesiones/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar sesión (DELETE físico)",
    description="""
    Eliminar una sesión (DELETE físico de la base de datos).
    
    **IMPORTANTE:** NO es soft delete. El registro se elimina permanentemente.
    
    **Por qué DELETE físico:**
    - Esta entidad NO tiene campo 'activo'
    - Eliminación física permite limpiar horarios obsoletos
    
    **Cascadas:**
    - Las asignaciones profesor-sesion se eliminan automáticamente (CASCADE)
    
    **TODO (Fase 3.5):**
    - Eliminar conflictos asociados a esta sesión
    
    **Errores:**
    - `404 Not Found`: Si la sesión no existe
    
    **Ejemplo:**
    ```
    DELETE /sesiones/1
    ```
    
    **Respuesta:**
    - Status: `204 No Content`
    - Body: Vacío
    """,
    responses={
        204: {"description": "Sesión eliminada exitosamente"},
        404: {"description": "Sesión no encontrada"}
    },
    tags=["Sesiones"]
)
def eliminar_sesion(
    id: int = Path(
        ...,
        ge=1,
        description="ID de la sesión a eliminar",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Eliminar una sesión (DELETE físico).
    
    Args:
        id: ID de la sesión a eliminar
        
    Returns:
        None (status 204 No Content)
        
    Raises:
        HTTPException 404: Si la sesión no existe
    """
    sesion_service.delete(db, id)
    return None


# ============================================================
#  ENDPOINTS DE HORARIOS (PIPELINE EXTRACCIÓN)
# ============================================================

@router.post(
    "/horarios/extract",
    response_model=HorarioTemporalOut,
    status_code=status.HTTP_200_OK,
    summary="Subir un PDF de horario y obtener un horario temporal editable",
    description="""
    Subir un horario académico en PDF y obtener un horario temporal editable.
    Validación previa de asignaturas mediante Fuzzy Matching.

    Este endpoint ejecuta el **pipeline de extracción, parsing y fuzzy matching** del módulo
    de horarios y devuelve un objeto `HorarioTemporalOut` con:

    - Información global del horario (`titulo`, `plan`, `periodo`)
    - Listado de tablas de horario (`horarios`) con:
        - `curso`, `periodo`, `mencion`, `pagina`
        - `sesiones` extraídas (asignatura, aula, día, horas, tipo, grupo)
    - Metadatos de extracción (`extraction_metadata`)
    - Metadatos de parsing (`parsing_metadata`)

    **Flujo interno:**
    1. Valida que el archivo subido sea un PDF.
    2. Guarda el archivo temporalmente en disco.
    3. Ejecuta el `HorariosPipelineService` (extractor + parser).
    4. Elimina el archivo temporal.
    5. Devuelve el horario temporal editable.

    **Importante:**
    - En esta versión NO se realiza persistencia en BD ni normalización.
    - El resultado está pensado para que el frontend permita la edición manual
      antes de confirmar el horario en un endpoint posterior.
    """,
    responses={
        200: {"description": "Horario extraído correctamente"},
        400: {
            "description": "El archivo subido no es un PDF válido",
            "content": {
                "application/json": {
                    "example": {"detail": "El archivo subido debe ser un PDF"}
                }
            },
        },
        500: {
            "description": "Error interno al procesar el horario",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Se ha producido un error al procesar el horario"
                    }
                }
            },
        },
    },
    tags=["Horarios"],
)
async def extract_horario(
    file: UploadFile = File(
        ...,
        description="Archivo PDF de horario a procesar",
    ),
    db: Session = Depends(get_db)
):
    """
    Extraer un horario académico a partir de un PDF.

    Args:
        file: Archivo PDF de horario subido por el cliente.

    Returns:
        HorarioTemporalOut con el horario temporal editable.

    Raises:
        HTTPException 400: Si el archivo no es un PDF.
        HTTPException 500: Si ocurre un error en la extracción/parsing.
    """
    # 1) Validar tipo de contenido
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido debe ser un PDF",
        )

    # 2) Guardar el PDF en un archivo temporal
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

    # 3) Ejecutar el pipeline (Pasando DB y PATH)
    try:
        horario_temporal = horarios_pipeline_service.extraer_horario(db=db, pdf_path=tmp_path)
    finally:
        # 4) Limpiar el archivo temporal
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return horario_temporal

@router.post(
    "/horarios/refine",
    response_model=HorarioTemporalOut,
    status_code=status.HTTP_200_OK,
    summary="Refinar matching de asignaturas (recalcular sugerencias)",
    description="""
    Recibe un horario temporal con metadatos actualizados (ej: usuario corrigió el Plan de Estudios o el Periodo)
    y **recalcula las sugerencias de asignaturas** (Fuzzy Match) usando este nuevo contexto.

    **Caso de uso:**
    1. Usuario sube PDF. El sistema no detecta bien la titulación. Muchas asignaturas salen en rojo.
    2. Usuario edita manualmente el "Plan de Estudios" en el frontend.
    3. Frontend llama a este endpoint.
    4. El sistema re-ejecuta el matcher sabiendo ahora que es "Grado en Matemáticas".
    5. Devuelve el horario con las asignaturas en verde (matches encontrados).
    """,
    tags=["Horarios"],
)
async def refine_horario_matching(
    payload: HorarioTemporalConfirmIn,
    db: Session = Depends(get_db),
):
    """
    Recalcular sugerencias de asignaturas basándose en cambios del usuario.
    """
    # Reutilizamos el servicio, que tiene la lógica de 'refinar_matching'
    return horarios_pipeline_service.refinar_matching(db, payload)

@router.post(
    "/horarios/confirm",
    response_model=HorarioConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirmar un horario editado y preparar la creación de grupos y sesiones",
    description="""
    Confirmar un horario académico previamente extraído y editado en el frontend.

    Este endpoint recibe un objeto `HorarioTemporalConfirmIn`, que representa
    el horario temporal editable devuelto por `/horarios/extract` pero ya
    revisado y modificado por el usuario.

    **Flujo previsto (fases posteriores):**
    1. Reconstruir una estructura compatible con el ParsingResult del parser.
    2. Ejecutar el normalizador de horarios para obtener estructuras de dominio.
    3. Crear o reutilizar:
        - Programas y asignaturas
        - Grupos docentes
        - Aulas
        - Sesiones
    4. Detectar incidencias (asignaturas no encontradas, aulas faltantes, etc.)
       y reflejarlas en `warnings` y `errors`.

    En esta primera versión, el endpoint devuelve una respuesta vacía bien
    tipada, de forma que el contrato con el frontend quede definido mientras
    se implementa la lógica de normalización y persistencia.
    """,
    responses={
        200: {"description": "Horario confirmado (respuesta provisional)"},
        422: {"description": "Datos de entrada inválidos"},
    },
    tags=["Horarios"],
)
async def confirm_horario(
    payload: HorarioTemporalConfirmIn,
    db: Session = Depends(get_db),
):
    """
    Confirmar un horario editado para su futura normalización y persistencia.

    Args:
        payload: Horario temporal editado que envía el frontend.

    Returns:
        HorarioConfirmResponse (por ahora vacío, sin grupos ni sesiones reales).
    """
    return horarios_pipeline_service.confirmar_horario(db, payload)
