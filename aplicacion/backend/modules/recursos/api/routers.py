"""
Endpoints REST API para el módulo de Recursos.

Define los endpoints para gestionar:
- Profesores: Personal docente
- Aulas: Espacios físicos (TODO)

Responsabilidades:
- Definir rutas HTTP (GET, POST, PUT, DELETE)
- Validar entrada (automático con Pydantic)
- Inyectar dependencias (DB session, paginación)
- Documentar API (OpenAPI/Swagger)
- Serializar respuestas a JSON
"""

from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.db.session import get_db
from backend.modules.recursos.schemas.profesor import (
    ProfesorCreate, ProfesorUpdate, ProfesorOut, ProfesorList
)
from backend.modules.recursos.services.profesor_service import profesor_service


# ============================================================
#  ROUTER: Configuración base
# ============================================================

router = APIRouter(
    # El prefijo se define en main.py al registrar el router
    responses={
        404: {"description": "Recurso no encontrado"},
        409: {"description": "Conflicto - Recurso duplicado"},
        422: {"description": "Error de validación"}
    }
)
"""
Router para endpoints del módulo Recursos.

- prefix: Todas las rutas empiezan con /v0/recursos (definido en main.py)
- tags: Agrupación en documentación Swagger
- responses: Documentación de errores comunes
"""


# ============================================================
#  ENDPOINTS DE PROFESOR
# ============================================================

@router.get(
    "/profesores/buscar",
    response_model=List[ProfesorOut],
    summary="Buscar profesores por nombre/apellidos",
    description="""
    Buscar profesores por nombre y/o apellidos (case-insensitive, búsqueda parcial).
    
    Busca en ambos órdenes: "nombre apellidos" y "apellidos nombre".
    
    **Ejemplos:**
    - `GET /profesores/buscar?busqueda=Gómez` → Juan Gómez, Kike Gómez
    - `GET /profesores/buscar?busqueda=Juan` → Juan Gómez, Juan Arroyo
    - `GET /profesores/buscar?busqueda=Juan Gómez` → Juan Gómez
    
    **Notas:**
    - Retorna lista vacía si no encuentra coincidencias (no 404)
    - Búsqueda sensible a acentos (escribir correctamente)
    """,
    tags=["Profesores"]
)
def buscar_profesores(
    busqueda: str = Query(
        ...,
        min_length=1,
        description="Texto a buscar en nombre/apellidos",
        examples=["Gómez", "Juan", "García López"]
    ),
    db: Session = Depends(get_db)
):
    """
    Buscar profesores por nombre/apellidos.
    
    Returns:
        Lista de profesores que coinciden (puede ser vacía)
    """
    return profesor_service.get_by_nombre(db, busqueda)


@router.get(
    "/profesores",
    response_model=ProfesorList,
    summary="Listar profesores",
    description="""
    Listar profesores con filtros opcionales y paginación.
    
    **Filtros disponibles:**
    - `departamento`: Filtrar por departamento exacto
    - `activo`: Filtrar por estado activo/inactivo
    
    **Paginación:**
    - `skip`: Número de registros a saltar (default: 0)
    - `limit`: Número máximo de registros (default: 100, max: 1000)
    
    **Ejemplo:**
    ```
    GET /profesores?departamento=Matemáticas&activo=true&skip=0&limit=20
    ```
    
    **Respuesta:**
    ```json
    {
        "total": 85,
        "items": [...],
        "page": 1,
        "size": 20
    }
    ```
    """,
    tags=["Profesores"]
)
def listar_profesores(
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
    departamento: Optional[str] = Query(
        None,
        description="Filtrar por departamento exacto",
        examples=["Matemáticas", "Ingeniería Informática", "Física Aplicada"]
    ),
    activo: Optional[bool] = Query(
        None,
        description="Filtrar por estado activo (true) o inactivo (false)",
        examples=[True, False]
    ),
    db: Session = Depends(get_db)
):
    """
    Listar profesores con filtros y paginación.
    
    Returns:
        ProfesorList con total, items, page y size
    """
    # Obtener profesores del service
    items, total = profesor_service.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        departamento=departamento,
        activo=activo
    )
    
    # Calcular número de página actual
    page = (skip // limit) + 1 if limit > 0 else 1
    
    # Retornar schema de lista paginada
    return ProfesorList(
        total=total,
        items=items,
        page=page,
        size=limit
    )


@router.get(
    "/profesores/{id}",
    response_model=ProfesorOut,
    summary="Obtener profesor por ID",
    description="""
    Obtener un profesor específico por su ID.
    
    **Errores:**
    - `404 Not Found`: Si el profesor no existe
    
    **Ejemplo:**
    ```
    GET /profesores/1
    ```
    """,
    responses={
        200: {
            "description": "Profesor encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "nombre": "Juan",
                        "apellidos": "García López",
                        "email": "juan.garcia@uam.es",
                        "telefono": "+34 912 345 678",
                        "departamento": "Matemáticas",
                        "activo": True
                    }
                }
            }
        },
        404: {
            "description": "Profesor no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Profesor con id 999 no encontrado"}
                }
            }
        }
    },
    tags=["Profesores"]
)
def obtener_profesor(
    id: int = Path(
        ...,
        ge=1,
        description="ID único del profesor",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Obtener un profesor por su ID.
    
    Args:
        id: ID del profesor
        
    Returns:
        ProfesorOut con los datos del profesor
        
    Raises:
        HTTPException 404: Si el profesor no existe
    """
    return profesor_service.get_by_id(db, id)


@router.post(
    "/profesores",
    response_model=ProfesorOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo profesor",
    description="""
    Crear un nuevo profesor.
    
    **Campos obligatorios:**
    - `nombre`: Nombre del profesor (1-120 caracteres)
    - `apellidos`: Apellidos del profesor (1-200 caracteres)
    
    **Campos opcionales:**
    - `email`: Correo electrónico (único si se proporciona)
    - `telefono`: Teléfono de contacto
    - `departamento`: Departamento al que pertenece
    - `activo`: Estado activo/inactivo (default: true)
    
    **Validaciones:**
    - Email único: No puede haber dos profesores con el mismo email
    - Normalización automática: trim + lowercase email, colapsar espacios
    
    **Errores:**
    - `409 Conflict`: Si el email ya existe
    - `422 Unprocessable Entity`: Si los datos son inválidos
    
    **Ejemplo:**
    ```json
    {
        "nombre": "Juan",
        "apellidos": "García López",
        "email": "juan.garcia@universidad.es",
        "telefono": "+34 912 345 678",
        "departamento": "Matemáticas",
        "activo": true
    }
    ```
    """,
    responses={
        201: {"description": "Profesor creado exitosamente"},
        409: {"description": "Ya existe un profesor con ese email"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Profesores"]
)
def crear_profesor(
    profesor: ProfesorCreate = Body(
        ...,
        examples=[
            {
                "nombre": "Juan",
                "apellidos": "García López",
                "email": "juan.garcia@universidad.es",
                "telefono": "+34 912 345 678",
                "departamento": "Matemáticas",
                "activo": True
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo profesor.
    
    Args:
        profesor: Datos del profesor a crear
        
    Returns:
        ProfesorOut con el profesor creado (incluye ID autogenerado)
        
    Raises:
        HTTPException 409: Si el email ya existe
    """
    return profesor_service.create(db, profesor)


@router.put(
    "/profesores/{id}",
    response_model=ProfesorOut,
    summary="Actualizar profesor",
    description="""
    Actualizar un profesor existente (actualización parcial).
    
    **Comportamiento de campos:**
    - **Campo no incluido**: No se modifica
    - **Campo con valor**: Se actualiza
    - **Campo con `null`**: Se borra (pone a None)
    
    **Ejemplos de uso:**
    
    1. **Actualizar solo departamento:**
    ```json
    {"departamento": "Matemáticas"}
    ```
    
    2. **Borrar email (poner a null):**
    ```json
    {"email": null}
    ```
    
    3. **Actualizar email y teléfono:**
    ```json
    {
        "email": "nuevo@uam.es",
        "telefono": "+34 912 345 678"
    }
    ```
    
    4. **Desactivar profesor:**
    ```json
    {"activo": false}
    ```
    
    **Validaciones:**
    - Profesor debe existir
    - Si se actualiza email (incluso a null), validar unicidad
    
    **Errores:**
    - `404 Not Found`: Si el profesor no existe
    - `409 Conflict`: Si el nuevo email ya existe (en otro profesor)
    - `422 Unprocessable Entity`: Si los datos son inválidos
    """,
    responses={
        200: {"description": "Profesor actualizado exitosamente"},
        404: {"description": "Profesor no encontrado"},
        409: {"description": "El nuevo email ya existe en otro profesor"},
        422: {"description": "Datos de entrada inválidos"}
    },
    tags=["Profesores"]
)
def actualizar_profesor(
    id: int = Path(
        ...,
        ge=1,
        description="ID del profesor a actualizar",
        examples=[1, 42, 123]
    ),
    profesor: ProfesorUpdate = Body(
        ...,
        examples=[
            {
                "email": "nuevo.email@universidad.es",
                "departamento": "Ingeniería Informática"
            }
        ]
    ),
    db: Session = Depends(get_db)
):
    """
    Actualizar un profesor existente.
    
    Args:
        id: ID del profesor a actualizar
        profesor: Datos a actualizar (solo campos proporcionados)
        
    Returns:
        ProfesorOut con los datos actualizados
        
    Raises:
        HTTPException 404: Si el profesor no existe
        HTTPException 409: Si el nuevo email ya existe
    """
    return profesor_service.update(db, id, profesor)


@router.delete(
    "/profesores/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar profesor (soft delete)",
    description="""
    Soft delete de un profesor (cambia `activo` a `false`).
    
    **IMPORTANTE:** NO elimina físicamente el registro de la base de datos.
    Solo marca el profesor como inactivo.
    
    **Por qué soft delete:**
    - Mantiene integridad referencial con sesiones/restricciones
    - Permite auditoría histórica
    - Se puede reactivar después si es necesario
    
    **Errores:**
    - `404 Not Found`: Si el profesor no existe
    
    **Ejemplo:**
    ```
    DELETE /profesores/1
    ```
    
    **Respuesta:**
    - Status: `204 No Content`
    - Body: Vacío
    """,
    responses={
        204: {"description": "Profesor desactivado exitosamente"},
        404: {"description": "Profesor no encontrado"}
    },
    tags=["Profesores"]
)
def eliminar_profesor(
    id: int = Path(
        ...,
        ge=1,
        description="ID del profesor a eliminar",
        examples=[1, 42, 123]
    ),
    db: Session = Depends(get_db)
):
    """
    Soft delete de un profesor.
    
    Args:
        id: ID del profesor a eliminar
        
    Returns:
        None (status 204 No Content)
        
    Raises:
        HTTPException 404: Si el profesor no existe
    """
    profesor_service.delete(db, id)
    return None


# TODO: Añadir endpoints de Aulas cuando se implemente
# Seguir el mismo patrón que Profesores