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

from backend.modules.catalogo.services.asignatura_service import asignatura_service
from backend.modules.catalogo.schemas.asignatura import (
    AsignaturaCreate,
    AsignaturaUpdate,
    AsignaturaOut,
    AsignaturaList
)

from backend.modules.catalogo.services.mencion_service import mencion_service
from backend.modules.catalogo.schemas.mencion import (
    MencionCreate,
    MencionUpdate,
    MencionOut,
    MencionList
) 

from backend.constants.enums import TipoPrograma, Periodo, ModalidadAsignatura, Idioma 


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
        description="Filtrar por tipo de programa",
        example="grado"  # Valor en minúsculas como está definido en el enum
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



# ============================================================
#  ENDPOINTS DE ASIGNATURA
# ============================================================

@router.get(
    "/asignaturas",
    response_model=AsignaturaList,
    summary="Listar asignaturas",
    description="Obtener listado de asignaturas con filtros opcionales y paginación"
)
def listar_asignaturas(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    periodo: Optional[Periodo] = Query(None, example="cuatrimestral_1", description="Filtrar por periodo de impartición"),
    modalidad: Optional[ModalidadAsignatura] = Query(None, example="presencial", description="Filtrar por modalidad"),
    idioma: Optional[Idioma] = Query(None, example="español", description="Filtrar por idioma"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado (true=activo, false=inactivo)"),
    db: Session = Depends(get_db)
):
    """
    Listar asignaturas con filtros opcionales.
    
    **Filtros disponibles:**
    - `periodo`: anual, cuatrimestral_1, cuatrimestral_2
    - `modalidad`: presencial, online, semipresencial
    - `idioma`: español, inglés, catalán
    - `activo`: true (activas), false (inactivas), null (todas)
    
    **Paginación:**
    - `skip`: Número de registros a saltar (default: 0)
    - `limit`: Número máximo de registros (default: 100, max: 1000)
    
    **Ejemplo de uso:**
    ```
    GET /asignaturas?periodo=cuatrimestral_1&modalidad=presencial&limit=20
    ```
    """
    return asignatura_service.get_asignaturas(
        db=db,
        skip=skip,
        limit=limit,
        periodo=periodo,
        modalidad=modalidad,
        idioma=idioma,
        activo=activo
    )


@router.get(
    "/asignaturas/codigo/{codigo_plan}",
    response_model=AsignaturaOut,
    summary="Obtener asignatura por código",
    description="Obtener una asignatura buscando por su código de plan de estudios",
    responses={
        404: {"description": "Asignatura con ese código no encontrada"}
    }
)
def obtener_asignatura_por_codigo(
    codigo_plan: str = Path(..., min_length=1, max_length=6, description="Código de plan de la asignatura"),
    db: Session = Depends(get_db)
):
    """
    Obtener asignatura por código de plan.
    
    **Parámetros:**
    - `codigo_plan`: Código único de la asignatura (1-6 caracteres)
    
    **Respuestas:**
    - `200`: Asignatura encontrada
    - `404`: No existe asignatura con ese código
    - `422`: Código inválido (longitud incorrecta)
    
    **Ejemplo de uso:**
    ```
    GET /asignaturas/codigo/MAT101
    ```
    
    **Nota:** El código se normaliza automáticamente (uppercase, strip).
    """
    return asignatura_service.get_asignatura_by_codigo(db, codigo_plan)


@router.get(
    "/asignaturas/{asignatura_id}",
    response_model=AsignaturaOut,
    summary="Obtener asignatura por ID",
    description="Obtener los detalles de una asignatura específica por su ID",
    responses={
        404: {"description": "Asignatura no encontrada"}
    }
)
def obtener_asignatura(
    asignatura_id: int = Path(..., ge=1, description="ID de la asignatura"),
    db: Session = Depends(get_db)
):
    """
    Obtener asignatura por ID.
    
    **Parámetros:**
    - `asignatura_id`: ID único de la asignatura (debe ser > 0)
    
    **Respuestas:**
    - `200`: Asignatura encontrada
    - `404`: Asignatura no existe
    - `422`: ID inválido (no es un entero positivo)
    
    **Ejemplo de uso:**
    ```
    GET /asignaturas/1
    ```
    """
    return asignatura_service.get_asignatura(db, asignatura_id)


@router.post(
    "/asignaturas",
    response_model=AsignaturaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear asignatura",
    description="Crear una nueva asignatura en el sistema",
    responses={
        201: {"description": "Asignatura creada exitosamente"},
        409: {"description": "Ya existe una asignatura con ese código o nombre"},
        422: {"description": "Datos de entrada inválidos"}
    }
)
def crear_asignatura(
    asignatura: AsignaturaCreate,
    db: Session = Depends(get_db)
):
    """
    Crear nueva asignatura.
    
    **Validaciones:**
    - Código de plan único (no puede existir otra asignatura con el mismo código)
    - Nombre único (no puede existir otra asignatura con el mismo nombre)
    - ECTS entre 1 y 12 (si se proporciona)
    - Código: 1-6 caracteres (se normaliza a mayúsculas)
    - Nombre: 1-250 caracteres (se normaliza: strip + collapse spaces)
    
    **Respuestas:**
    - `201`: Asignatura creada correctamente
    - `409`: Código o nombre duplicado
    - `422`: Datos inválidos (validación de Pydantic)
    
    **Ejemplo de body:**
    ```json
    {
        "codigo_plan": "MAT101",
        "nombre": "Matemáticas I",
        "periodo": "cuatrimestral_1",
        "ects": 6,
        "modalidad": "presencial",
        "idioma": "español",
        "english_friendly": false,
        "activo": true
    }
    ```
    """
    return asignatura_service.create_asignatura(db, asignatura)


@router.put(
    "/asignaturas/{asignatura_id}",
    response_model=AsignaturaOut,
    summary="Actualizar asignatura",
    description="Actualizar una asignatura existente (actualización parcial)",
    responses={
        200: {"description": "Asignatura actualizada exitosamente"},
        404: {"description": "Asignatura no encontrada"},
        409: {"description": "El nuevo código o nombre ya existe"},
        422: {"description": "Datos de entrada inválidos"}
    }
)
def actualizar_asignatura(
    asignatura_id: int = Path(..., ge=1, description="ID de la asignatura a actualizar"),
    asignatura: AsignaturaUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Actualizar asignatura existente.
    
    **Actualización parcial:** Solo se actualizan los campos proporcionados.
    
    **Validaciones:**
    - La asignatura debe existir
    - Si se cambia el código: debe ser único (excluyendo la asignatura actual)
    - Si se cambia el nombre: debe ser único (excluyendo la asignatura actual)
    - ECTS entre 1 y 12 (si se proporciona)
    
    **Respuestas:**
    - `200`: Asignatura actualizada correctamente
    - `404`: Asignatura no existe
    - `409`: Nuevo código/nombre ya existe en otra asignatura
    - `422`: Datos inválidos
    
    **Ejemplo de body (actualizar solo ECTS):**
    ```json
    {
        "ects": 9
    }
    ```
    
    **Ejemplo de body (actualizar múltiples campos):**
    ```json
    {
        "nombre": "Matemáticas Avanzadas I",
        "ects": 9,
        "modalidad": "semipresencial"
    }
    ```
    """
    return asignatura_service.update_asignatura(db, asignatura_id, asignatura)


@router.delete(
    "/asignaturas/{asignatura_id}",
    summary="Eliminar asignatura",
    description="Desactivar una asignatura (soft delete)",
    responses={
        200: {"description": "Asignatura desactivada exitosamente"},
        404: {"description": "Asignatura no encontrada"}
    }
)
def eliminar_asignatura(
    asignatura_id: int = Path(..., ge=1, description="ID de la asignatura a eliminar"),
    db: Session = Depends(get_db)
):
    """
    Eliminar asignatura (soft delete).
    
    **Comportamiento:**
    - NO elimina físicamente el registro de la base de datos
    - Marca la asignatura como inactiva (activo = false)
    - La asignatura seguirá existiendo pero no aparecerá en listados por defecto
    
    **Validaciones:**
    - La asignatura debe existir
    
    **Respuestas:**
    - `200`: Asignatura desactivada correctamente
    - `404`: Asignatura no existe
    
    **Ejemplo de respuesta:**
    ```json
    {
        "message": "Asignatura 'MAT101 - Matemáticas I' desactivada correctamente"
    }
    ```
    
    **Nota:** Para recuperar asignaturas inactivas, usar `GET /asignaturas?activo=false`
    """
    return asignatura_service.delete_asignatura(db, asignatura_id)




# ============================================================
#  ENDPOINTS DE MENCION
# ============================================================

@router.get(
    "/menciones",
    response_model=MencionList,
    summary="Listar menciones",
    description="Obtener listado de menciones con filtros opcionales y paginación"
)
def listar_menciones(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    programa_id: Optional[int] = Query(None, ge=1, description="Filtrar por programa", example=1),
    activo: Optional[bool] = Query(None, description="Filtrar por estado (true=activo, false=inactivo)"),
    db: Session = Depends(get_db)
):
    """
    Listar menciones con filtros opcionales.
    
    **Filtros disponibles:**
    - `programa_id`: ID del programa (para listar menciones de un programa específico)
    - `activo`: true (activas), false (inactivas), null (todas)
    
    **Paginación:**
    - `skip`: Número de registros a saltar (default: 0)
    - `limit`: Número máximo de registros (default: 100, max: 1000)
    
    **Ordenación:**
    - Por `programa_id` ASC, luego por `nombre` ASC
    
    **Ejemplo de uso:**
    ```
    GET /menciones?programa_id=1&activo=true&limit=20
    ```
    """
    return mencion_service.get_menciones(
        db=db,
        skip=skip,
        limit=limit,
        programa_id=programa_id,
        activo=activo
    )


@router.get(
    "/menciones/{mencion_id}",
    response_model=MencionOut,
    summary="Obtener mención por ID",
    description="Obtener los detalles de una mención específica por su ID",
    responses={
        404: {"description": "Mención no encontrada"}
    }
)
def obtener_mencion(
    mencion_id: int = Path(..., ge=1, description="ID de la mención"),
    db: Session = Depends(get_db)
):
    """
    Obtener mención por ID.
    
    **Parámetros:**
    - `mencion_id`: ID único de la mención (debe ser >= 1)
    
    **Respuestas:**
    - `200`: Mención encontrada
    - `404`: Mención no existe
    - `422`: ID inválido (no es un entero positivo)
    
    **Ejemplo de uso:**
    ```
    GET /menciones/1
    ```
    """
    return mencion_service.get_mencion(db, mencion_id)


@router.post(
    "/menciones",
    response_model=MencionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear mención",
    description="Crear una nueva mención asociada a un programa",
    responses={
        201: {"description": "Mención creada exitosamente"},
        404: {"description": "Programa no encontrado"},
        409: {"description": "Ya existe una mención con ese nombre en el programa"},
        422: {"description": "Datos de entrada inválidos"}
    }
)
def crear_mencion(
    mencion: MencionCreate,
    db: Session = Depends(get_db)
):
    """
    Crear nueva mención.
    
    **Validaciones:**
    - El programa debe existir (404 si no existe)
    - Nombre único dentro del programa (no puede existir otra mención con el mismo nombre en el mismo programa)
    - Nombre: 1-200 caracteres (se normaliza: strip + collapse spaces)
    
    **Constraint de unicidad:**
    - `(programa_id, nombre)`: Puede haber menciones con el mismo nombre en diferentes programas,
      pero no dentro del mismo programa
    
    **Respuestas:**
    - `201`: Mención creada correctamente
    - `404`: Programa no encontrado
    - `409`: Ya existe mención con ese nombre en el programa
    - `422`: Datos inválidos (validación de Pydantic)
    
    **Ejemplo de body:**
    ```json
    {
        "programa_id": 1,
        "nombre": "Ingeniería del Software",
        "activo": true
    }
    ```
    """
    return mencion_service.create_mencion(db, mencion)


@router.put(
    "/menciones/{mencion_id}",
    response_model=MencionOut,
    summary="Actualizar mención",
    description="Actualizar una mención existente (actualización parcial)",
    responses={
        200: {"description": "Mención actualizada exitosamente"},
        404: {"description": "Mención o programa no encontrado"},
        409: {"description": "El nuevo nombre ya existe en el programa"},
        422: {"description": "Datos de entrada inválidos"}
    }
)
def actualizar_mencion(
    mencion_id: int = Path(..., ge=1, description="ID de la mención a actualizar"),
    mencion: MencionUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Actualizar mención existente.
    
    **Actualización parcial:** Solo se actualizan los campos proporcionados.
    
    **Validaciones:**
    - La mención debe existir (404)
    - Si se cambia el programa: el programa debe existir (404)
    - Si se cambia programa o nombre: la combinación debe ser única (409)
    
    **Respuestas:**
    - `200`: Mención actualizada correctamente
    - `404`: Mención o programa no existe
    - `409`: Ya existe mención con ese nombre en el programa
    - `422`: Datos inválidos
    
    **Ejemplo de body (actualizar solo nombre):**
    ```json
    {
        "nombre": "Ingeniería del Software Avanzada"
    }
    ```
    
    **Ejemplo de body (cambiar de programa):**
    ```json
    {
        "programa_id": 2,
        "nombre": "Computación"
    }
    ```
    
    **Nota:** Al cambiar de programa, se valida que no exista otra mención
    con el mismo nombre en el nuevo programa.
    """
    return mencion_service.update_mencion(db, mencion_id, mencion)


@router.delete(
    "/menciones/{mencion_id}",
    summary="Eliminar mención",
    description="Desactivar una mención (soft delete)",
    responses={
        200: {"description": "Mención desactivada exitosamente"},
        404: {"description": "Mención no encontrada"}
    }
)
def eliminar_mencion(
    mencion_id: int = Path(..., ge=1, description="ID de la mención a eliminar"),
    db: Session = Depends(get_db)
):
    """
    Eliminar mención (soft delete).
    
    **Comportamiento:**
    - NO elimina físicamente el registro de la base de datos
    - Marca la mención como inactiva (activo = false)
    - La mención seguirá existiendo pero no aparecerá en listados por defecto
    
    **Validaciones:**
    - La mención debe existir (404)
    
    **Respuestas:**
    - `200`: Mención desactivada correctamente
    - `404`: Mención no existe
    
    **Ejemplo de respuesta:**
    ```json
    {
        "message": "Mención 'Ingeniería del Software' desactivada correctamente"
    }
    ```
    
    **Nota:** Para recuperar menciones inactivas, usar `GET /menciones?activo=false`
    """
    return mencion_service.delete_mencion(db, mencion_id)