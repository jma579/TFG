"""
Repositorio para operaciones de base de datos de GrupoDocente.

Responsabilidades:
- CRUD de grupos.
- Búsqueda por filtros.
- WIPE: Borrado masivo por asignatura (para regeneración de horarios).
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import GrupoDocente
from constants.enums import TipoGrupoDocente


class GrupoDocenteRepository:
    """
    Gestor de persistencia para GrupoDocente.
    """
    
    # ==========================
    # LECTURA
    # ==========================

    def get_by_id(self, db: Session, id: int) -> Optional[GrupoDocente]:
        """Obtiene un grupo por su ID."""
        return db.query(GrupoDocente).filter(GrupoDocente.id == id).first()
    
    def get_by_asignatura_codigo(
        self, db: Session, asignatura_id: int, codigo: str
    ) -> Optional[GrupoDocente]:
        """Obtiene un grupo por asignatura y código (case insensitive)."""
        return db.query(GrupoDocente).filter(
            GrupoDocente.asignatura_id == asignatura_id,
            func.lower(GrupoDocente.codigo) == codigo.lower()
        ).first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        asignatura_id: Optional[int] = None,
        tipo: Optional[TipoGrupoDocente] = None,
        curso: Optional[int] = None
    ) -> Tuple[List[GrupoDocente], int]:
        """Obtiene múltiples grupos con filtros opcionales y paginación."""
        query = db.query(GrupoDocente)
        
        if asignatura_id:
            query = query.filter(GrupoDocente.asignatura_id == asignatura_id)
        if tipo:
            query = query.filter(GrupoDocente.tipo == tipo)
        if curso:
            query = query.filter(GrupoDocente.curso == curso)
            
        total = query.count()
        query = query.order_by(GrupoDocente.curso, GrupoDocente.codigo)
        items = query.offset(skip).limit(limit).all()
        return items, total

    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================

    def create(self, db: Session, data: dict) -> GrupoDocente:
        """Crea un grupo. El commit es responsabilidad del servicio."""
        db_grupo = GrupoDocente(**data)
        db.add(db_grupo)
        db.flush()
        db.refresh(db_grupo)
        return db_grupo

    def update(self, db: Session, db_obj: GrupoDocente, data: dict) -> GrupoDocente:
        """Actualiza un grupo. El commit es responsabilidad del servicio."""
        for field, value in data.items():
            setattr(db_obj, field, value)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """Borrado físico individual."""
        obj = self.get_by_id(db, id)
        if not obj:
            return False
        db.delete(obj)
        db.flush()
        return True

    def delete_by_asignatura(self, db: Session, asignatura_id: int) -> int:
        """
        WIPE STRATEGY: Elimina TODOS los grupos docentes de una asignatura.
        
        IMPORTANTE: Debido a la configuración `cascade='all, delete-orphan'` en 
        el modelo SQLAlchemy, esto eliminará automáticamente todas las SESIONES 
        asociadas a estos grupos.
        """
        count = db.query(GrupoDocente).filter(
            GrupoDocente.asignatura_id == asignatura_id
        ).delete(synchronize_session=False)
        
        db.flush()
        return count

    # ==========================
    # VALIDACIONES
    # ==========================

    def exists_by_asignatura_codigo(
        self, db: Session, asignatura_id: int, codigo: str, exclude_id: Optional[int] = None
    ) -> bool:
        query = db.query(GrupoDocente).filter(
            GrupoDocente.asignatura_id == asignatura_id,
            func.lower(GrupoDocente.codigo) == codigo.lower()
        )
        if exclude_id is not None:
            query = query.filter(GrupoDocente.id != exclude_id)
        return query.first() is not None


grupo_docente_repository = GrupoDocenteRepository()