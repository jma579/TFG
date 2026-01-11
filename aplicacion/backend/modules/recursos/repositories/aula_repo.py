"""
Repositorio para operaciones de base de datos de Aula.

Responsabilidades:
- Acceso directo a la tabla aulas
- Queries básicas (CRUD)
- Búsquedas y filtros
- NO contiene lógica de negocio (va en service)
- Retorna modelos SQLAlchemy (Aula)
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database.models import Aula
from constants.enums import TipoAula


class AulaRepository:
    """
    Repositorio para operaciones de base de datos de Aula.
    """
    
    # ==========================
    # LECTURA
    # ==========================
    
    def get_by_id(self, db: Session, id: int) -> Optional[Aula]:
        """Obtener aula por ID."""
        return db.query(Aula).filter(Aula.id == id).first()
    
    def get_by_codigo(self, db: Session, codigo: str) -> Optional[Aula]:
        """Obtener aula por código único (case-insensitive)."""
        return db.query(Aula).filter(func.lower(Aula.codigo) == codigo.lower()).first()
    
    def get_by_nombre(self, db: Session, nombre: str) -> Optional[Aula]:
        """Obtener aula por nombre único (case-insensitive)."""
        return db.query(Aula).filter(func.lower(Aula.nombre) == nombre.lower()).first()
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        tipo: Optional[TipoAula] = None,
        capacidad_min: Optional[int] = None,
        capacidad_max: Optional[int] = None,
        busqueda: Optional[str] = None,
        activo: Optional[bool] = None
    ) -> Tuple[List[Aula], int]:
        """
        Listar aulas con filtros combinados.
        """
        query = db.query(Aula)
        
        # Filtros directos
        if tipo is not None:
            query = query.filter(Aula.tipo == tipo)
        if capacidad_min is not None:
            query = query.filter(Aula.capacidad >= capacidad_min)
        if capacidad_max is not None:
            query = query.filter(Aula.capacidad <= capacidad_max)
        if activo is not None:
            query = query.filter(Aula.activo == activo)
        
        # Búsqueda textual (nombre o código)
        if busqueda is not None:
            busqueda_lower = busqueda.lower()
            query = query.filter(
                or_(
                    func.lower(Aula.nombre).contains(busqueda_lower),
                    func.lower(Aula.codigo).contains(busqueda_lower)
                )
            )
        
        total = query.count()
        query = query.order_by(Aula.codigo.asc())
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================
    
    def create(self, db: Session, data: dict) -> Aula:
        """Crear aula."""
        db_aula = Aula(**data)
        db.add(db_aula)
        db.flush()
        db.refresh(db_aula)
        return db_aula
    
    def update(self, db: Session, db_obj: Aula, data: dict) -> Aula:
        """Actualizar aula."""
        for field, value in data.items():
            if value is not None:
                setattr(db_obj, field, value)
        db.flush()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: int) -> bool:
        """Soft delete: marcar como inactivo."""
        aula = self.get_by_id(db, id)
        if not aula:
            return False
        aula.activo = False
        db.flush()
        return True

    def delete_physical(self, db: Session, id: int) -> bool:
        """Hard delete: eliminar registro físico de la BD."""
        aula = self.get_by_id(db, id)
        if not aula:
            return False
        db.delete(aula)
        db.flush()
        return True
    
    # ==========================
    # VALIDACIONES
    # ==========================
    
    def exists_by_codigo(self, db: Session, codigo: str, exclude_id: Optional[int] = None) -> bool:
        """Verificar si existe código (útil para validaciones)."""
        query = db.query(Aula).filter(func.lower(Aula.codigo) == codigo.lower())
        if exclude_id is not None:
            query = query.filter(Aula.id != exclude_id)
        return query.first() is not None
    
    def exists_by_nombre(self, db: Session, nombre: str, exclude_id: Optional[int] = None) -> bool:
        """Verificar si existe nombre (útil para validaciones)."""
        query = db.query(Aula).filter(func.lower(Aula.nombre) == nombre.lower())
        if exclude_id is not None:
            query = query.filter(Aula.id != exclude_id)
        return query.first() is not None


# Instancia Singleton
aula_repository = AulaRepository()