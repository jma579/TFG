"""
Service para la entidad Mencion.

Capa de lógica de negocio (Business Logic Layer).
Responsable de:
- Validaciones de negocio (existencia de FK, unicidad compuesta)
- Orquestación de operaciones del Repository
- Manejo de transacciones unitarias para la API (Commits)
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from modules.catalogo.repositories.mencion_repo import mencion_repository
from modules.catalogo.repositories.programa_repo import programa_repository
from modules.catalogo.schemas.mencion import (
    MencionCreate,
    MencionUpdate,
    MencionOut,
    MencionList
)


class MencionService:
    """Service para lógica de negocio de Mencion."""
    
    def __init__(self):
        """Inicializa el servicio con los repositorios necesarios."""
        self.repo = mencion_repository
        self.programa_repo = programa_repository
    
    
    def get_mencion(self, db: Session, mencion_id: int) -> MencionOut:
        """Obtiene una mención por su ID."""
        mencion = self.repo.get_by_id(db, mencion_id)
        if not mencion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        return MencionOut.model_validate(mencion)
    
    def get_menciones(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        programa_id: Optional[int] = None,
        activo: Optional[bool] = None
    ) -> MencionList:
        """Lista menciones con filtros de programa y estado."""
        items, total = self.repo.get_multi(db, skip, limit, programa_id, activo)
        return MencionList(
            total=total,
            items=[MencionOut.model_validate(item) for item in items],
            page=(skip // limit) + 1,
            size=limit
        )
    
    
    def create_mencion(self, db: Session, mencion_in: MencionCreate) -> MencionOut:
        """Crea una nueva mención."""
        if not self.programa_repo.get_by_id(db, mencion_in.programa_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Programa con ID {mencion_in.programa_id} no encontrado"
            )
            
        if self.repo.exists_by_programa_nombre(db, mencion_in.programa_id, mencion_in.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La mención '{mencion_in.nombre}' ya existe en este programa"
            )
        
        mencion = self.repo.create(db, mencion_in.model_dump())
        db.commit()
        db.refresh(mencion)
        
        return MencionOut.model_validate(mencion)
    
    def update_mencion(
        self,
        db: Session,
        mencion_id: int,
        mencion_in: MencionUpdate
    ) -> MencionOut:
        """Actualiza una mención existente."""
        mencion = self.repo.get_by_id(db, mencion_id)
        if not mencion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        
        data = mencion_in.model_dump(exclude_unset=True)
        
        programa_id = data.get("programa_id", mencion.programa_id)
        nombre = data.get("nombre", mencion.nombre)
        
        if mencion_in.programa_id and not self.programa_repo.get_by_id(db, programa_id):
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nuevo programa con ID {programa_id} no encontrado"
            )
             
        if self.repo.exists_by_programa_nombre(db, programa_id, nombre, exclude_id=mencion_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una mención '{nombre}' en el programa destino"
            )

        updated = self.repo.update(db, mencion_id, data)
        db.commit()
        db.refresh(updated)
        
        return MencionOut.model_validate(updated)
    
    def delete_mencion(self, db: Session, mencion_id: int) -> dict:
        """Desactiva una mención (Soft Delete)."""
        if not self.repo.get_by_id(db, mencion_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        
        self.repo.delete(db, mencion_id)
        db.commit()
        
        return {"message": "Mención desactivada correctamente"}


mencion_service = MencionService()