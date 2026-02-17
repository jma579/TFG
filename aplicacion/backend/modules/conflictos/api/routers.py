"""
Endpoints REST para el Módulo de Conflictos.

Gestión de conflictos de horarios con filtros, paginación y actualización de estados.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session

from db.session import get_db
from constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto
from modules.conflictos.schemas.conflicto import (
    ConflictoOut,
    ConflictoList,
    ConflictoEstadoUpdateIn,
)
from modules.conflictos.services.conflictos_service import conflicto_service


router = APIRouter(
    responses={
        404: {"description": "Recurso no encontrado"},
        422: {"description": "Error de validación"},
    }
)


@router.get(
    "",
    response_model=ConflictoList,
    summary="Listar conflictos",
    description="Listar conflictos con filtros opcionales (tipo, severidad, estado, profesor_id, aula_id, sesion_id) y paginación."
)
async def listar_conflictos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tipo: Optional[TipoConflicto] = Query(None),
    severidad: Optional[SeveridadConflicto] = Query(None),
    estado: Optional[EstadoConflicto] = Query(None),
    profesor_id: Optional[int] = Query(None, gt=0),
    aula_id: Optional[int] = Query(None, gt=0),
    sesion_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    items, total = conflicto_service.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        tipo=tipo,
        severidad=severidad,
        estado=estado,
        profesor_id=profesor_id,
        aula_id=aula_id,
        sesion_id=sesion_id,
    )

    page = (skip // limit) + 1 if limit > 0 else 1

    return ConflictoList(total=total, items=items, page=page, size=limit)


@router.get(
    "/sesion/{sesion_id}",
    response_model=List[ConflictoOut],
    summary="Listar conflictos de una sesión",
    description="Listar todos los conflictos donde participa una sesión (sesion_id o sesion_2_id)."
)
async def listar_conflictos_por_sesion(
    sesion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    items = conflicto_service.get_by_sesion(
        db=db,
        sesion_id=sesion_id
    )

    return items


@router.patch(
    "/{id}",
    response_model=ConflictoOut,
    status_code=status.HTTP_200_OK,
    summary="Actualizar estado de un conflicto",
    description="Actualizar el estado de un conflicto (ABIERTO, RESUELTO, IGNORADO)."
)
async def actualizar_estado_conflicto(
    id: int = Path(..., gt=0, description="ID del conflicto a actualizar"),
    body: ConflictoEstadoUpdateIn = Body(...),
    db: Session = Depends(get_db),
):
    return conflicto_service.update_estado(
        db=db,
        conflicto_id=id,
        estado_in=body,
    )


@router.post(
    "/analizar",
    status_code=status.HTTP_200_OK,
    summary="Analizar y sincronizar todos los conflictos del sistema",
    description="Ejecuta el motor de conflictos sobre todos los horarios y sincroniza los resultados en la BD usando Smart Merge."
)
async def analizar_sistema_global(
    db: Session = Depends(get_db),
):
    """
    Dispara la detección global de conflictos.
    Devuelve un diccionario con el resumen de eliminados, insertados y el total actual.
    """
    stats = conflicto_service.analizar_sistema_global(db)
    return stats