"""
Endpoints REST API para el módulo Catálogo.

Define los endpoints para gestionar:
- Programas (Grados, Másteres, Doctorados)

Responsabilidades:
- Definir rutas HTTP (GET, POST, PUT, DELETE)
- Validar entrada (automático con Pydantic)
- Inyectar dependencias (DB session, paginación)
- Documentar API (OpenAPI/Swagger)
- Serializar respuestas a JSON
"""

from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.db.session import get_db
from backend.modules.catalogo.services.programa_service import programa_service
from backend.modules.catalogo.schemas.programa import (
    ProgramaCreate,
    ProgramaUpdate,
    ProgramaOut,
    ProgramaList
)
from backend.constants.enums import TipoPrograma


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
Router para endpoints del módulo Catálogo.

- prefix: Todas las rutas empiezan con /v0/catalogo
- tags: Agrupación en documentación Swagger
- responses: Documentación de errores comunes
"""


# ============================================================
#  ENDPOINT: Listar programas (GET /programas)
# ============================================================

@router.get(
    "/programas",
    response_model=ProgramaList,
    summary="Listar programas",
    description="Obtiene una lista paginada de programas con filtros opcionales",
    response_description="Lista de programas con metadatos de paginación"
)
def listar_programas(
    skip: int = Query(
        default=0,
        ge=0,
        description="Número de registros a saltar (offset para paginación)",
        example=0
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Número máximo de registros a devolver",
        example=10
    ),
    activo: Optional[bool] = Query(
        default=None,
        description="Filtrar por estado activo. Si no se especifica, devuelve todos",
        example=True
    ),
    tipo: Optional[TipoPrograma] = Query(
        default=None,
        description="Filtrar por tipo de programa (GRADO, MASTER, DOCTORADO, DOBLE_GRADO)",
        example="GRADO"
    ),
    db: Session = Depends(get_db)
):
    """
    **Listar programas con filtros y paginación.**
    
    ### Parámetros de consulta:
    - **skip**: Offset para paginación (por defecto 0)
    - **limit**: Límite de resultados (por defecto 100, máximo 500)
    - **activo**: Filtrar por estado (opcional)
    - **tipo**: Filtrar por tipo de programa (opcional)
    
    ### Respuesta:
    Objeto con:
    - **total**: Número total de registros (sin paginar)
    - **items**: Lista de programas de la página actual
    - **page**: Número de página actual
    - **size**: Tamaño de página
    
    ### Ejemplos de uso:
    ```
    # Todos los programas (primera página)
    GET /v0/catalogo/programas
    
    # Segunda página (items 10-19)
    GET /v0/catalogo/programas?skip=10&limit=10
    
    # Solo programas activos de tipo GRADO
    GET /v0/catalogo/programas?activo=true&tipo=GRADO
    ```
    """
    return programa_service.get_programas(
        db=db,
        skip=skip,
        limit=limit,
        activo=activo,
        tipo=tipo
    )


# ============================================================
#  ENDPOINT: Obtener programa por ID (GET /programas/{id})
# ============================================================

@router.get(
    "/programas/{programa_id}",
    response_model=ProgramaOut,
    summary="Obtener programa por ID",
    description="Obtiene los detalles de un programa específico",
    response_description="Datos completos del programa",
    responses={
        200: {
            "description": "Programa encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "nombre": "Grado en Matemáticas",
                        "tipo": "GRADO",
                        "activo": True
                    }
                }
            }
        },
        404: {
            "description": "Programa no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "Programa con ID 999 no encontrado"}
                }
            }
        }
    }
)
def obtener_programa(
    programa_id: int = Path(
        ...,
        ge=1,
        description="ID del programa a buscar",
        example=1
    ),
    db: Session = Depends(get_db)
):
    """
    **Obtener un programa específico por su ID.**
    
    ### Parámetros:
    - **programa_id**: ID único del programa (debe ser >= 1)
    
    ### Respuesta exitosa (200):
    Objeto con todos los datos del programa.
    
    ### Errores:
    - **404 Not Found**: Si el programa no existe
    
    ### Ejemplo:
    ```
    GET /v0/catalogo/programas/1
    
    Response:
    {
      "id": 1,
      "nombre": "Grado en Matemáticas",
      "tipo": "GRADO",
      "activo": true
    }
    ```
    """
    return programa_service.get_programa(db, programa_id)


# ============================================================
#  ENDPOINT: Crear programa (POST /programas)
# ============================================================

@router.post(
    "/programas",
    response_model=ProgramaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo programa",
    description="Crea un nuevo programa académico con validaciones",
    response_description="Programa creado con ID generado"
)
def crear_programa(
    programa: ProgramaCreate,
    db: Session = Depends(get_db)
):
    """
    **Crear un nuevo programa académico.**
    
    ### Body (JSON):
    Objeto ProgramaCreate con:
    - **nombre**: Nombre del programa (1-200 caracteres)
    - **tipo**: Tipo (GRADO, MASTER, DOCTORADO, DOBLE_GRADO)
    - **activo**: Estado (opcional, por defecto true)
    
    ### Validaciones:
    - El par (nombre, tipo) debe ser único
    - Nombre no puede estar vacío
    - Tipo debe ser un valor válido del enum
    
    ### Respuesta exitosa (201 Created):
    Objeto con todos los datos del programa (incluye ID generado).
    
    ### Errores:
    - **409 Conflict**: Si ya existe un programa con ese (nombre, tipo)
    - **422 Unprocessable Entity**: Si los datos no cumplen el schema
    
    ### Ejemplo:
    ```
    POST /v0/catalogo/programas
    Content-Type: application/json
    
    {
      "nombre": "Grado en Física",
      "tipo": "GRADO",
      "activo": true
    }
    
    Response (201):
    {
      "id": 1,
      "nombre": "Grado en Física",
      "tipo": "GRADO",
      "activo": true
    }
    ```
    """
    return programa_service.create_programa(db, programa)


# ============================================================
#  ENDPOINT: Actualizar programa (PUT /programas/{id})
# ============================================================

@router.put(
    "/programas/{programa_id}",
    response_model=ProgramaOut,
    summary="Actualizar programa",
    description="Actualiza los datos de un programa existente (actualización parcial)",
    response_description="Programa actualizado"
)
def actualizar_programa(
    programa_id: int = Path(
        ...,
        ge=1,
        description="ID del programa a actualizar",
        example=1
    ),
    programa: ProgramaUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    **Actualizar un programa existente.**
    
    ### Parámetros:
    - **programa_id**: ID del programa a actualizar
    
    ### Body (JSON):
    Objeto ProgramaUpdate con campos opcionales:
    - **nombre**: Nuevo nombre (opcional)
    - **tipo**: Nuevo tipo (opcional)
    - **activo**: Nuevo estado (opcional)
    
    **Solo se actualizan los campos enviados** (actualización parcial).
    
    ### Validaciones:
    - El programa debe existir
    - Si se actualiza nombre o tipo, el nuevo par debe ser único
    
    ### Respuesta exitosa (200):
    Objeto con todos los datos del programa actualizado.
    
    ### Errores:
    - **404 Not Found**: Si el programa no existe
    - **409 Conflict**: Si el nuevo (nombre, tipo) ya existe en otro programa
    - **422 Unprocessable Entity**: Si los datos no cumplen el schema
    
    ### Ejemplos:
    ```
    # Actualizar solo el nombre
    PUT /v0/catalogo/programas/1
    {
      "nombre": "Grado en Matemáticas Aplicadas"
    }
    
    # Actualizar nombre y estado
    PUT /v0/catalogo/programas/1
    {
      "nombre": "Nuevo nombre",
      "activo": false
    }
    
    # Actualizar todo
    PUT /v0/catalogo/programas/1
    {
      "nombre": "Otro nombre",
      "tipo": "MASTER",
      "activo": true
    }
    ```
    """
    return programa_service.update_programa(db, programa_id, programa)


# ============================================================
#  ENDPOINT: Eliminar programa (DELETE /programas/{id})
# ============================================================

@router.delete(
    "/programas/{programa_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar programa (soft delete)",
    description="Desactiva un programa (no lo elimina físicamente)",
    response_description="Mensaje de confirmación"
)
def eliminar_programa(
    programa_id: int = Path(
        ...,
        ge=1,
        description="ID del programa a desactivar",
        example=1
    ),
    db: Session = Depends(get_db)
):
    """
    **Desactivar un programa (soft delete).**
    
    No elimina el registro físicamente de la base de datos.
    Solo actualiza el campo `activo` a `false`.
    
    ### Parámetros:
    - **programa_id**: ID del programa a desactivar
    
    ### Respuesta exitosa (200):
    ```json
    {
      "message": "Programa desactivado correctamente"
    }
    ```
    
    ### Errores:
    - **404 Not Found**: Si el programa no existe
    
    ### Ejemplo:
    ```
    DELETE /v0/catalogo/programas/1
    
    Response (200):
    {
      "message": "Programa desactivado correctamente"
    }
    ```
    
    ### Nota:
    Para reactivar un programa, usar PUT con `{"activo": true}`.
    """
    return programa_service.delete_programa(db, programa_id)