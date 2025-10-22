"""
Endpoints REST API para el módulo de Docencia.

Define los endpoints para gestionar:
- GrupoDocente: Grupos de docencia (teoría, práctica, laboratorio, etc.)
- Sesion: Sesiones de clase programadas (PENDIENTE)

Responsabilidades:
- Definir rutas HTTP (GET, POST, PUT, DELETE)
- Validar entrada (automático con Pydantic)
- Inyectar dependencias (DB session, paginación)
- Documentar API (OpenAPI/Swagger)
- Serializar respuestas a JSON
"""

from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.db.session import get_db
from backend.modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate, GrupoDocenteOut, GrupoDocenteList
)
from backend.modules.docencia.services.grupo_docente_service import grupo_docente_service
from backend.constants.enums import TipoGrupoDocente


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