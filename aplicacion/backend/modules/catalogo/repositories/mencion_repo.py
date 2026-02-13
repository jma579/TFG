"""
Repositorio para la entidad Mencion.

Proporciona métodos CRUD y búsquedas especializadas mediante SQLAlchemy ORM.
Delega la confirmación de transacciones (commit) a la capa de Servicio.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List, Tuple

from database.models import Mencion


class MencionRepository:
    """
    Gestor de persistencia para Menciones (Especializaciones de un Programa).
    """
        
    def get_by_id(self, db: Session, mencion_id: int) -> Optional[Mencion]:
        """Busca una mención por su identificador único."""
        return db.query(Mencion).filter(Mencion.id == mencion_id).first()
    
    def get_by_programa_nombre(
        self,
        db: Session,
        programa_id: int,
        nombre: str
    ) -> Optional[Mencion]:
        """Busca mención por clave compuesta (programa_id + nombre)."""
        return db.query(Mencion).filter(
            and_(
                Mencion.programa_id == programa_id,
                Mencion.nombre == nombre
            )
        ).first()
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        programa_id: Optional[int] = None,
        activo: Optional[bool] = None
    ) -> Tuple[List[Mencion], int]:
        """Lista menciones con filtros y paginación."""
        query = db.query(Mencion)
        
        if programa_id is not None:
            query = query.filter(Mencion.programa_id == programa_id)
        
        if activo is not None:
            query = query.filter(Mencion.activo == activo)
        
        total = query.count()
        query = query.order_by(Mencion.programa_id.asc(), Mencion.nombre.asc())
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    

    def create(self, db: Session, mencion_data: dict) -> Mencion:
        """Crea una nueva mención."""
        mencion = Mencion(**mencion_data)
        db.add(mencion)
        db.flush() 
        db.refresh(mencion)
        return mencion
    
    def update(
        self,
        db: Session,
        mencion_id: int,
        mencion_data: dict
    ) -> Optional[Mencion]:
        """Actualiza parcialmente una mención existente."""
        mencion = self.get_by_id(db, mencion_id)
        if not mencion:
            return None
        
        for field, value in mencion_data.items():
            if value is not None:
                setattr(mencion, field, value)
        
        db.flush()
        db.refresh(mencion)
        return mencion
    
    def delete(self, db: Session, mencion_id: int) -> bool:
        """Soft-delete: marca la mención como inactiva."""
        mencion = self.get_by_id(db, mencion_id)
        if not mencion:
            return False
        
        mencion.activo = False
        db.flush()
        return True
    
    
    def exists_by_programa_nombre(
        self,
        db: Session,
        programa_id: int,
        nombre: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Verifica la existencia de duplicados en el mismo programa."""
        query = db.query(Mencion).filter(
            and_(
                Mencion.programa_id == programa_id,
                Mencion.nombre == nombre
            )
        )
        
        if exclude_id is not None:
            query = query.filter(Mencion.id != exclude_id)
        
        return db.query(query.exists()).scalar()


mencion_repository = MencionRepository()