"""
Endpoints de la API REST para el Módulo Catálogo.

Este router centraliza la gestión de las entidades académicas fundamentales y
el proceso de ingesta de datos mediante fichas docentes (PDF).

Funcionalidades:
1. Ingesta de Fichas: Procesamiento de PDFs, extracción, normalización y persistencia.
2. Asignaturas: Gestión restringida (Solo Lectura y Borrado). La creación es vía PDF.
3. Programas: Gestión completa (CRUD) de titulaciones (Grados, Másteres).
4. Menciones: Gestión completa (CRUD) de especialidades.
"""

import shutil
import tempfile
import os
import traceback
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, Query, Path, 
    status, HTTPException, UploadFile, File
)
from sqlalchemy.orm import Session

# Infraestructura y configuración
from db.session import get_db
from constants.enums import Periodo, ModalidadAsignatura, Idioma, TipoPrograma

# Servicios de Dominio
from modules.catalogo.services.asignatura_service import asignatura_service
from modules.catalogo.services.programa_service import programa_service
from modules.catalogo.services.mencion_service import mencion_service
from modules.catalogo.services.ficha_pipeline_service import FichaPipelineService

# Schemas - Asignatura
from modules.catalogo.schemas.asignatura import (
    AsignaturaOut,
    AsignaturaList,
    AsignaturaProgramaOut,
    AsignaturaUpdate
)

# Schemas - Programa
from modules.catalogo.schemas.programa import (
    ProgramaCreate,
    ProgramaUpdate,
    ProgramaOut,
    ProgramaList
)

# Schemas - Mención
from modules.catalogo.schemas.mencion import (
    MencionCreate,
    MencionUpdate,
    MencionOut,
    MencionList
)

# Schemas Externos (Recursos)
from modules.recursos.schemas.profesor import ProfesorOut


router = APIRouter()

# Instancia del servicio de pipeline (Stateless)
ficha_pipeline = FichaPipelineService()


# =============================================================================
#  SECCIÓN 1: PIPELINE DE INGESTA (PDFs)
# =============================================================================

@router.post(
    "/fichas/process",
    status_code=status.HTTP_200_OK,
    summary="Procesar Ficha Académica (PDF)",
    description="Sube un PDF, extrae su contenido y actualiza/crea la asignatura, profesores y programas asociados."
)
def procesar_ficha_endpoint(
    file: UploadFile = File(..., description="Archivo PDF de la guía docente"),
    db: Session = Depends(get_db)
):
    """
    Endpoint transaccional para la ingesta de fichas.
    
    Flujo:
    1. Valida el formato del archivo.
    2. Guarda el PDF en un archivo temporal.
    3. Invoca al FichaPipelineService para la extracción y persistencia.
    4. Limpia el archivo temporal.
    5. Retorna estadísticas del proceso.
    """
    # 1. Validación básica
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El archivo debe tener extensión .pdf"
        )

    tmp_path = None
    try:
        # 2. Guardado temporal seguro
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        # 3. Ejecución del Pipeline (Orquestador Transaccional)
        result = ficha_pipeline.procesar_ficha(tmp_path, db)

        # 4. Manejo de resultados de negocio
        if not result.success:
            # Errores controlados del dominio (ej: PDF ilegible)
            return {
                "success": False,
                "errors": result.errors,
                "metadata": result.metadata
            }

        return {
            "success": True,
            "message": f"Ficha procesada correctamente. Código: {result.metadata.get('codigo', 'N/A')}",
            "data": {
                "asignatura_id": result.asignatura_id,
                "stats": result.created_entities,
                "metadata": result.metadata
            }
        }

    except Exception as e:
        # 5. Captura de errores inesperados (Crash)
        error_msg = f"Error crítico procesando ficha: {str(e)}"
        print(traceback.format_exc()) # Log en servidor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    finally:
        # 6. Limpieza garantizada
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# =============================================================================
#  SECCIÓN 2: GESTIÓN DE ASIGNATURAS (Solo Lectura y Borrado)
# =============================================================================

@router.get("/asignaturas", response_model=AsignaturaList)
def listar_asignaturas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    periodo: Optional[Periodo] = None,
    modalidad: Optional[ModalidadAsignatura] = None,
    idioma: Optional[Idioma] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Listar asignaturas con filtros."""
    return asignatura_service.get_asignaturas(
        db, skip=skip, limit=limit,
        periodo=periodo, modalidad=modalidad, idioma=idioma, activo=activo
    )

@router.get("/asignaturas/codigo/{codigo_plan}", response_model=AsignaturaOut)
def obtener_asignatura_por_codigo(
    codigo_plan: str = Path(..., description="Código del plan (ej: G71)"),
    db: Session = Depends(get_db),
):
    """Buscar asignatura por su código único."""
    return asignatura_service.get_asignatura_by_codigo(db, codigo_plan)

@router.get("/asignaturas/{asignatura_id}", response_model=AsignaturaOut)
def obtener_asignatura(
    asignatura_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Obtener detalle de una asignatura por ID."""
    return asignatura_service.get_asignatura(db, asignatura_id)

@router.get("/asignaturas/{asignatura_id}/programas", response_model=List[AsignaturaProgramaOut])
def listar_programas_asignatura(
    asignatura_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Ver en qué titulaciones (programas) se imparte la asignatura."""
    return asignatura_service.get_programas_de_asignatura(db, asignatura_id)

@router.get("/asignaturas/{asignatura_id}/profesores", response_model=List[ProfesorOut])
def listar_profesores_asignatura(
    asignatura_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Ver el equipo docente asignado a la asignatura."""
    return asignatura_service.get_profesores_de_asignatura(db, asignatura_id)

@router.delete("/asignaturas/{asignatura_id}")
def eliminar_asignatura(
    asignatura_id: int = Path(..., ge=1),
    physical: bool = Query(False, description="True=Borrado físico, False=Soft delete"),
    db: Session = Depends(get_db),
):
    """Eliminar o desactivar una asignatura."""
    return asignatura_service.delete_asignatura(db, asignatura_id, physical=physical)

@router.put("/asignaturas/{asignatura_id}", response_model=AsignaturaOut)
def actualizar_asignatura(
    asignatura_in: AsignaturaUpdate,
    asignatura_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """
    Actualizar datos de una asignatura.
    Permite cambios parciales (ej: solo activar/desactivar).
    """
    return asignatura_service.update_asignatura(db, asignatura_id, asignatura_in)


# =============================================================================
#  SECCIÓN 3: GESTIÓN DE PROGRAMAS (CRUD Completo)
# =============================================================================

@router.get("/programas", response_model=ProgramaList)
def listar_programas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    activo: Optional[bool] = Query(None),
    tipo: Optional[TipoPrograma] = Query(None),
    db: Session = Depends(get_db),
):
    """Listar programas académicos con filtros."""
    return programa_service.get_programas(db, skip=skip, limit=limit, activo=activo, tipo=tipo)

@router.get("/programas/{programa_id}", response_model=ProgramaOut)
def obtener_programa(
    programa_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Obtener detalle de un programa académico."""
    return programa_service.get_programa(db, programa_id)

@router.get("/programas/{programa_id}/asignaturas", response_model=AsignaturaList)
def listar_asignaturas_programa(
    programa_id: int = Path(..., ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Listar el plan de estudios (asignaturas) de un programa."""
    return asignatura_service.get_asignaturas_by_programa(db, programa_id, skip, limit)

@router.post("/programas", response_model=ProgramaOut, status_code=status.HTTP_201_CREATED)
def crear_programa(
    programa_in: ProgramaCreate,
    db: Session = Depends(get_db),
):
    """Crear un nuevo programa académico."""
    return programa_service.create_programa(db, programa_in)

@router.put("/programas/{programa_id}", response_model=ProgramaOut)
def actualizar_programa(
    programa_in: ProgramaUpdate,
    programa_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Actualizar datos de un programa académico."""
    return programa_service.update_programa(db, programa_id, programa_in)

@router.delete("/programas/{programa_id}")
def eliminar_programa(
    programa_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Eliminar un programa académico."""
    return programa_service.delete_programa(db, programa_id)


# =============================================================================
#  SECCIÓN 4: GESTIÓN DE MENCIONES (CRUD Completo)
# =============================================================================

@router.get("/menciones", response_model=MencionList)
def listar_menciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    programa_id: Optional[int] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Listar menciones con filtros."""
    return mencion_service.get_menciones(
        db, skip=skip, limit=limit, programa_id=programa_id, activo=activo
    )

@router.get("/menciones/{mencion_id}", response_model=MencionOut)
def obtener_mencion(
    mencion_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Obtener detalle de una mención."""
    return mencion_service.get_mencion(db, mencion_id)

@router.post("/menciones", response_model=MencionOut, status_code=status.HTTP_201_CREATED)
def crear_mencion(
    mencion_in: MencionCreate,
    db: Session = Depends(get_db),
):
    """Crear una nueva mención."""
    return mencion_service.create_mencion(db, mencion_in)

@router.put("/menciones/{mencion_id}", response_model=MencionOut)
def actualizar_mencion(
    mencion_in: MencionUpdate,
    mencion_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Actualizar datos de una mención."""
    return mencion_service.update_mencion(db, mencion_id, mencion_in)

@router.delete("/menciones/{mencion_id}")
def eliminar_mencion(
    mencion_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    """Eliminar una mención."""
    return mencion_service.delete_mencion(db, mencion_id)