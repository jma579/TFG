"""
Repositorio para la entidad Profesor.

Capa de Acceso a Datos (DAL).
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from database.models import Profesor

class ProfesorRepository:
    """Gestor de persistencia para profesores."""

    # ==========================
    # LECTURA
    # ==========================

    def get_by_id(self, db: Session, profesor_id: int) -> Optional[Profesor]:
        """Busca un profesor por su ID."""
        return db.query(Profesor).filter(Profesor.id == profesor_id).first()

    def get_by_nombre_apellidos(
        self, db: Session, nombre: str, apellidos: str
    ) -> Optional[Profesor]:
        """Busca por coincidencia de nombre y apellidos (insensible a mayúsculas)."""
        return db.query(Profesor).filter(
            Profesor.nombre.ilike(nombre),
            Profesor.apellidos.ilike(apellidos)
        ).first()

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100, activo: Optional[bool] = None
    ) -> Tuple[List[Profesor], int]:
        """Lista profesores con filtros."""
        query = db.query(Profesor)
        if activo is not None:
            query = query.filter(Profesor.activo == activo)
            
        total = query.count()
        query = query.order_by(Profesor.apellidos.asc(), Profesor.nombre.asc())
        items = query.offset(skip).limit(limit).all()
        return items, total

    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================

    def create(self, db: Session, data: dict) -> Profesor:
        """Crea un nuevo profesor."""
        prof = Profesor(**data)
        db.add(prof)
        db.flush()
        db.refresh(prof)
        return prof

    def update(self, db: Session, profesor_id: int, data: dict) -> Optional[Profesor]:
        """Actualiza datos de un profesor existente."""
        prof = self.get_by_id(db, profesor_id)
        if not prof:
            return None
            
        for k, v in data.items():
            if v is not None:
                setattr(prof, k, v)
                
        db.flush()
        db.refresh(prof)
        return prof

    def delete(self, db: Session, profesor_id: int) -> bool:
        """Soft Delete: Desactiva el profesor."""
        prof = self.get_by_id(db, profesor_id)
        if not prof:
            return False
        prof.activo = False
        db.flush()
        return True

    def delete_physical(self, db: Session, profesor_id: int) -> bool:
        """Hard Delete: Eliminación física irreversible."""
        prof = self.get_by_id(db, profesor_id)
        if not prof:
            return False
        db.delete(prof)
        db.flush()
        return True

profesor_repository = ProfesorRepository()