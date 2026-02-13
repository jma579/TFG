"""
Endpoints REST para el Módulo de Recursos.

Gestión de profesores y aulas.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from db.session import get_db
from constants.enums import TipoAula

# Servicios
from modules.recursos.services.profesor_service import profesor_service
from modules.recursos.services.aula_service import aula_service

# Schemas
from modules.recursos.schemas.profesor import (
    ProfesorOut, ProfesorList, ProfesorUpdate
)
from modules.recursos.schemas.aula import (
    AulaCreate, AulaUpdate, AulaOut, AulaList
)

router = APIRouter()


# Profesores

@router.get("/profesores", response_model=ProfesorList, status_code=status.HTTP_200_OK)
def listar_profesores(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    return profesor_service.get_profesores(db, skip, limit, activo)


@router.get("/profesores/{profesor_id}", response_model=ProfesorOut, status_code=status.HTTP_200_OK)
def obtener_profesor(
    profesor_id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return profesor_service.get_profesor(db, profesor_id)


@router.put("/profesores/{profesor_id}", response_model=ProfesorOut, status_code=status.HTTP_200_OK)
def actualizar_profesor(
    profesor_in: ProfesorUpdate,
    profesor_id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return profesor_service.update_profesor(db, profesor_id, profesor_in)


@router.delete("/profesores/{profesor_id}", status_code=status.HTTP_200_OK)
def eliminar_profesor(
    profesor_id: int = Path(..., ge=1),
    physical: bool = Query(False, description="True=Borrado Físico, False=Soft Delete"),
    db: Session = Depends(get_db)
):
    return profesor_service.delete_profesor(db, profesor_id, physical)


# Aulas

@router.get("/aulas", response_model=AulaList, status_code=status.HTTP_200_OK)
def listar_aulas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tipo: Optional[TipoAula] = Query(None),
    activo: Optional[bool] = Query(None),
    busqueda: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return aula_service.get_multi(db, skip, limit, tipo, activo, busqueda)


@router.get("/aulas/{aula_id}", response_model=AulaOut, status_code=status.HTTP_200_OK)
def obtener_aula(
    aula_id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return aula_service.get_by_id(db, aula_id)


@router.post("/aulas", response_model=AulaOut, status_code=status.HTTP_201_CREATED)
def crear_aula(
    aula_in: AulaCreate,
    db: Session = Depends(get_db)
):
    return aula_service.create(db, aula_in)


@router.put("/aulas/{aula_id}", response_model=AulaOut, status_code=status.HTTP_200_OK)
def actualizar_aula(
    aula_in: AulaUpdate,
    aula_id: int = Path(..., ge=1),
    db: Session = Depends(get_db)
):
    return aula_service.update(db, aula_id, aula_in)


@router.delete("/aulas/{aula_id}", status_code=status.HTTP_200_OK)
def eliminar_aula(
    aula_id: int = Path(..., ge=1),
    physical: bool = Query(False, description="True=Borrado Físico, False=Soft Delete"),
    db: Session = Depends(get_db)
):
    return aula_service.delete(db, aula_id, physical)