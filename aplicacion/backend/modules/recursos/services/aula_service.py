"""
Capa de servicio para la entidad Aula.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)

Validaciones:
- Unicidad de código (case-insensitive)
- Unicidad de nombre (case-insensitive)
- Existencia de aula antes de actualizar/eliminar
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.recursos.repositories.aula_repo import aula_repository
from modules.recursos.schemas.aula import AulaCreate, AulaUpdate, AulaOut, AulaList
from constants.enums import TipoAula

class AulaService:
    """
    Servicio para gestionar la lógica de negocio de Aula.
    """
    
    def __init__(self):
        self.repo = aula_repository

    # ==========================
    # LECTURA
    # ==========================
    
    def get_by_id(self, db: Session, id: int) -> AulaOut:
        """Obtener detalle de aula."""
        aula = self.repo.get_by_id(db, id)
        if not aula:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Aula {id} no encontrada")
        return AulaOut.model_validate(aula)
    
    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100,
        tipo: Optional[TipoAula] = None, activo: Optional[bool] = None,
        busqueda: Optional[str] = None
    ) -> AulaList:
        """Listar aulas con filtros."""
        items, total = self.repo.get_multi(
            db, skip, limit, tipo=tipo, activo=activo, busqueda=busqueda
        )
        return AulaList(
            total=total,
            items=[AulaOut.model_validate(i) for i in items],
            page=(skip // limit) + 1,
            size=limit
        )
    
    # ==========================
    # ESCRITURA (Transaccional)
    # ==========================

    def create(self, db: Session, aula_in: AulaCreate) -> AulaOut:
        """Crear nueva aula con validaciones de unicidad."""
        # Validar duplicados
        if self.repo.exists_by_codigo(db, aula_in.codigo):
            raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Código '{aula_in.codigo}' ya existe")
        
        # Crear y commit
        aula = self.repo.create(db, aula_in.model_dump())
        db.commit()
        db.refresh(aula)
        return AulaOut.model_validate(aula)
    
    def update(self, db: Session, id: int, aula_in: AulaUpdate) -> AulaOut:
        """Actualizar aula existente."""
        aula = self.repo.get_by_id(db, id)
        if not aula:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Aula {id} no encontrada")
        
        # Validar duplicados si cambian (excluyendo la propia aula)
        if aula_in.codigo and self.repo.exists_by_codigo(db, aula_in.codigo, exclude_id=id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Código ya existe en otra aula")
            
        if aula_in.nombre and self.repo.exists_by_nombre(db, aula_in.nombre, exclude_id=id):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Nombre ya existe en otra aula")
        
        # Update y commit
        updated = self.repo.update(db, aula, aula_in.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(updated)
        return AulaOut.model_validate(updated)
    
    def delete(self, db: Session, id: int, physical: bool) -> dict:
        """
        Eliminar aula.
        
        Args:
            physical: True para borrado físico (Hard), False para Soft Delete.
        """
        if not self.repo.get_by_id(db, id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Aula {id} no encontrada")
        
        if physical:
            # Hard Delete: Puede fallar por FK constraints
            try:
                self.repo.delete_physical(db, id)
                msg = "Aula eliminada físicamente"
            except Exception as e:
                db.rollback()
                # Detectar error de integridad referencial
                if "constraint" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="No se puede eliminar el aula: tiene sesiones o restricciones asociadas"
                    )
                raise e
        else:
            # Soft Delete
            self.repo.delete(db, id)
            msg = "Aula desactivada (Soft Delete)"
            
        db.commit()
        return {"message": msg}


# Singleton
aula_service = AulaService()