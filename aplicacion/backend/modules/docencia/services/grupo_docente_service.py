"""
Capa de servicio para la entidad GrupoDocente.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate, GrupoDocenteOut
)
from constants.enums import TipoGrupoDocente

from modules.catalogo.repositories.asignatura_repo import asignatura_repository


class GrupoDocenteService:
    """
    Servicio para gestionar la lógica de negocio de GrupoDocente.
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, grupo_in: GrupoDocenteCreate) -> GrupoDocenteOut:
        """Crear nuevo grupo docente."""
        asignatura = asignatura_repository.get_by_id(db, grupo_in.asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con id {grupo_in.asignatura_id} no encontrada"
            )
        
        if grupo_docente_repository.exists_by_asignatura_codigo(
            db, grupo_in.asignatura_id, grupo_in.codigo
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya existe un grupo con código '{grupo_in.codigo}' "
                    f"para la asignatura con id {grupo_in.asignatura_id}"
                )
            )
        
        grupo = grupo_docente_repository.create(db, grupo_in)
        
        db.commit()
        db.refresh(grupo)
        
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_by_id(self, db: Session, id: int) -> GrupoDocenteOut:
        """Obtener grupo docente por ID."""
        grupo = grupo_docente_repository.get_by_id(db, id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_by_asignatura_codigo(
        self,
        db: Session,
        asignatura_id: int,
        codigo: str
    ) -> GrupoDocenteOut:
        """Obtener grupo por constraint único (asignatura_id, codigo)."""
        grupo = grupo_docente_repository.get_by_asignatura_codigo(
            db, asignatura_id, codigo
        )
        
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Grupo con código '{codigo}' no encontrado "
                    f"para la asignatura con id {asignatura_id}"
                )
            )
        
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        asignatura_id: Optional[int] = None,
        tipo: Optional[TipoGrupoDocente] = None,
        curso: Optional[int] = None,
        turno: Optional[str] = None
    ) -> Tuple[List[GrupoDocenteOut], int]:
        """Listar grupos docentes con filtros y paginación."""
        items, total = grupo_docente_repository.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            asignatura_id=asignatura_id,
            tipo=tipo,
            curso=curso,
            turno=turno
        )
        
        items_out = [GrupoDocenteOut.model_validate(item) for item in items]
        
        return items_out, total
    
    
    def update(
        self,
        db: Session,
        id: int,
        grupo_in: GrupoDocenteUpdate
    ) -> GrupoDocenteOut:
        """Actualizar grupo docente existente (actualización parcial)."""
        grupo = grupo_docente_repository.get_by_id(db, id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        
        if grupo_in.asignatura_id is not None:
            asignatura = asignatura_repository.get_by_id(db, grupo_in.asignatura_id)
            if not asignatura:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Asignatura con id {grupo_in.asignatura_id} no encontrada"
                )
        
        final_asignatura_id = (
            grupo_in.asignatura_id if grupo_in.asignatura_id is not None
            else grupo.asignatura_id
        )
        final_codigo = (
            grupo_in.codigo if grupo_in.codigo is not None
            else grupo.codigo
        )
        
        cambio_asignatura = (
            grupo_in.asignatura_id is not None and
            grupo_in.asignatura_id != grupo.asignatura_id
        )
        cambio_codigo = (
            grupo_in.codigo is not None and
            grupo_in.codigo.lower() != grupo.codigo.lower()
        )
        
        if cambio_asignatura or cambio_codigo:
            if grupo_docente_repository.exists_by_asignatura_codigo(
                db, final_asignatura_id, final_codigo, exclude_id=id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Ya existe otro grupo con código '{final_codigo}' "
                        f"para la asignatura con id {final_asignatura_id}"
                    )
                )
        
        grupo = grupo_docente_repository.update(db, grupo, grupo_in)
        
        # Commit
        db.commit()
        db.refresh(grupo)
        
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def delete(self, db: Session, id: int) -> None:
        """Eliminar grupo docente (DELETE físico)."""
        grupo = grupo_docente_repository.get_by_id(db, id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        
        try:
            grupo_docente_repository.delete(db, id)
            db.commit()
            
        except Exception as e:
            db.rollback()
            if "FOREIGN KEY constraint failed" in str(e) or "foreign key constraint" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"No se puede eliminar el grupo con id {id} porque tiene "
                        "sesiones asociadas"
                    )
                )
            raise


grupo_docente_service = GrupoDocenteService()