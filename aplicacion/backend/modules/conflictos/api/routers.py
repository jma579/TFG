"""Endpoints REST API para el módulo de Conflictos.

Responsabilidades:
- Listar conflictos con filtros y paginación
- Listar conflictos por sesión
- Actualizar el estado de un conflicto (ABIERTO, RESUELTO, IGNORADO)

El prefijo /v0/conflictos se define en main.py al registrar este router.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session

from db.session import get_db
from constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto
from modules.conflictos.schemas.conflicto import (
    ConflictoOut,
    ConflictoList,
    ConflictoEstadoUpdateIn,
)
from modules.conflictos.service.conflictos_service import conflicto_service


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
    description="""Listar conflictos con filtros opcionales y paginación.

Filtros disponibles:
- tipo: tipo de conflicto (solapamiento profesor, aula, restricción, etc.)
- severidad: severidad mínima a considerar
- estado: estado del conflicto (ABIERTO, RESUELTO, IGNORADO)
- profesor_id, aula_id, sesion_id

Paginación:
- skip: número de registros a saltar (offset)
- limit: tamaño de página (máx. 100)
""",
)
async def listar_conflictos(
    skip: int = Query(
        0,
        ge=0,
        description="Número de registros a saltar (offset)",
        examples=[0, 10, 20],
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Número máximo de registros a retornar",
        examples=[10, 20, 50],
    ),
    tipo: Optional[TipoConflicto] = Query(
        None,
        description="Filtrar por tipo de conflicto",
    ),
    severidad: Optional[SeveridadConflicto] = Query(
        None,
        description="Filtrar por severidad del conflicto",
    ),
    estado: Optional[EstadoConflicto] = Query(
        None,
        description="Filtrar por estado del conflicto",
    ),
    profesor_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por profesor implicado",
    ),
    aula_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por aula implicada",
    ),
    sesion_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filtrar por sesión implicada",
    ),
    db: Session = Depends(get_db),
):
    """Listar conflictos con filtros y paginación."""

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
    response_model=ConflictoList,
    summary="Listar conflictos de una sesión",
    description="""Listar todos los conflictos en los que participa una sesión concreta.

Incluye conflictos donde la sesión es sesion_id o sesion_2_id.
""",
)
async def listar_conflictos_por_sesion(
    sesion_id: int = Path(
        ..., gt=0, description="ID de la sesión cuyas conflictos se quieren consultar"
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Número de registros a saltar (offset)",
        examples=[0, 10, 20],
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Número máximo de registros a retornar",
        examples=[10, 20, 50],
    ),
    db: Session = Depends(get_db),
):
    """Listar conflictos asociados a una sesión concreta."""

    items, total = conflicto_service.get_by_sesion(
        db=db,
        sesion_id=sesion_id,
        skip=skip,
        limit=limit,
    )

    page = (skip // limit) + 1 if limit > 0 else 1

    return ConflictoList(total=total, items=items, page=page, size=limit)


@router.patch(
    "/{id}",
    response_model=ConflictoOut,
    status_code=status.HTTP_200_OK,
    summary="Actualizar estado de un conflicto",
    description="""Actualizar el estado de un conflicto existente.

Permite marcar conflictos como ABIERTO, RESUELTO o IGNORADO.
""",
)
async def actualizar_estado_conflicto(
    id: int = Path(..., gt=0, description="ID del conflicto a actualizar"),
    body: ConflictoEstadoUpdateIn = Body(
        ..., description="Nuevo estado del conflicto (ABIERTO, RESUELTO, IGNORADO)"
    ),
    db: Session = Depends(get_db),
):
    """Actualizar el estado de un conflicto.

    Delegado en la capa de servicio para aplicar reglas de negocio.
    """

    return conflicto_service.update_estado(
        db=db,
        conflicto_id=id,
        estado_in=body,
    )
