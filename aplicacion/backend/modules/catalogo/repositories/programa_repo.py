"""
Repositorio para la entidad Programa.

Gestiona el acceso a datos para Grados, Másteres y otras titulaciones.
Mantiene la integridad transaccional delegando el commit.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models import Programa
from constants.enums import TipoPrograma

class ProgramaRepository:
    """Gestor de persistencia para programas académicos."""
    
    # ==========================
    # LECTURA
    # ==========================

    def get_by_id(self, db: Session, programa_id: int) -> Optional[Programa]:
        """Obtiene un programa por su ID."""
        return db.query(Programa).filter(Programa.id == programa_id).first()

    def get_by_nombre_tipo(
        self, db: Session, nombre: str, tipo: TipoPrograma
    ) -> Optional[Programa]:
        """
        Busca un programa por la combinación única de nombre y tipo.
        Útil para evitar duplicados semánticos.
        """
        return db.query(Programa).filter(
            Programa.nombre.ilike(nombre),  # Búsqueda insensible a mayúsculas
            Programa.tipo == tipo,
        ).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        activo: Optional[bool] = None,
        tipo: Optional[TipoPrograma] = None,
    ) -> Tuple[List[Programa], int]:
        """Lista programas con filtrado y paginación."""
        query = db.query(Programa)
        if activo is not None:
            query = query.filter(Programa.activo == activo)
        if tipo is not None:
            query = query.filter(Programa.tipo == tipo)

        total = query.count()
        query = query.order_by(Programa.nombre.asc())
        items = query.offset(skip).limit(limit).all()
        return items, total

    # ==========================
    # ESCRITURA
    # ==========================

    def create(self, db: Session, programa_data: dict) -> Programa:
        """Crea un nuevo programa y refresca la instancia con datos de BD."""
        db_programa = Programa(**programa_data)
        db.add(db_programa)
        db.flush()
        db.refresh(db_programa)
        return db_programa

    def update(
        self, db: Session, programa: Programa, update_data: dict
    ) -> Programa:
        """Actualiza atributos de una instancia de programa existente."""
        for key, value in update_data.items():
            if value is not None:
                setattr(programa, key, value)
        db.flush()
        db.refresh(programa)
        return programa

    def delete(self, db: Session, programa_id: int) -> bool:
        """Desactiva un programa (soft-delete)."""
        programa = self.get_by_id(db, programa_id)
        if not programa:
            return False
        programa.activo = False
        db.flush()
        return True

    def exists_by_nombre_tipo(
        self, db: Session, nombre: str, tipo: TipoPrograma, exclude_id: Optional[int] = None
    ) -> bool:
        """Verifica existencia de duplicados por nombre y tipo."""
        query = db.query(Programa).filter(
            and_(Programa.nombre == nombre, Programa.tipo == tipo)
        )
        if exclude_id is not None:
            query = query.filter(Programa.id != exclude_id)
        return query.first() is not None


# Instancia única exportada
programa_repository = ProgramaRepository()