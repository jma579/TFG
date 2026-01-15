"""
Service para la lógica de negocio de la entidad Programa.

Responsabilidades:
- Implementar casos de uso (operaciones de negocio)
- Validar reglas de dominio
- Orquestar llamadas a repositorios
- Manejar transacciones de base de datos para la API
"""

from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException, status

from modules.catalogo.repositories.programa_repo import programa_repository
from modules.catalogo.schemas.programa import (
    ProgramaCreate, 
    ProgramaUpdate, 
    ProgramaOut, 
    ProgramaList
)
from constants.enums import TipoPrograma


class ProgramaService:
    """
    Service para gestionar la lógica de negocio de Programas.
    Patrón: Repository → Service → Router
    """
    
    def __init__(self):
        self.repo = programa_repository
    
    # ============================================================
    #  LECTURA
    # ============================================================
    
    def get_programa(self, db: Session, programa_id: int) -> ProgramaOut:
        """Obtiene un programa por ID."""
        prog = self.repo.get_by_id(db, programa_id)
        if not prog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Programa no encontrado"
            )
        return ProgramaOut.model_validate(prog)

    def get_programas(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        activo: Optional[bool] = None, 
        tipo: Optional[TipoPrograma] = None
    ) -> ProgramaList:
        """Lista programas con filtros."""
        items, total = self.repo.get_multi(db, skip, limit, activo, tipo)
        return ProgramaList(
            total=total, 
            items=[ProgramaOut.model_validate(p) for p in items], 
            page=(skip // limit) + 1, 
            size=limit
        )

    # ============================================================
    #  ESCRITURA (Transaccional)
    # ============================================================

    def create_programa(self, db: Session, programa_in: ProgramaCreate) -> ProgramaOut:
        """Crea un nuevo programa validando duplicados."""
        if self.repo.exists_by_nombre_tipo(db, programa_in.nombre, programa_in.tipo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un programa con ese nombre y tipo"
            )
        
        programa = self.repo.create(db, programa_in.model_dump())
        db.commit()
        db.refresh(programa)
        
        return ProgramaOut.model_validate(programa)

    def update_programa(
        self, 
        db: Session, 
        programa_id: int, 
        programa_in: ProgramaUpdate
    ) -> ProgramaOut:
        """Actualiza un programa existente."""
        prog = self.repo.get_by_id(db, programa_id)
        if not prog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Programa no encontrado"
            )
        
        data = programa_in.model_dump(exclude_unset=True)
        
        # Validar duplicados solo si cambian nombre o tipo
        if "nombre" in data or "tipo" in data:
            nuevo_nombre = data.get("nombre", prog.nombre)
            nuevo_tipo = data.get("tipo", prog.tipo)
            
            if self.repo.exists_by_nombre_tipo(db, nuevo_nombre, nuevo_tipo, exclude_id=programa_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflicto: Ya existe otro programa con ese nombre y tipo"
                )

        updated = self.repo.update(db, prog, data)
        db.commit()
        db.refresh(updated)
        
        return ProgramaOut.model_validate(updated)

    def delete_programa(self, db: Session, programa_id: int) -> dict:
        """Desactiva un programa (Soft Delete)."""
        if not self.repo.delete(db, programa_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Programa no encontrado"
            )
        
        db.commit()
        return {"message": "Programa desactivado correctamente"}


programa_service = ProgramaService()