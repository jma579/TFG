"""
Repositorio para la entidad Asignatura.

Capa de Acceso a Datos (DAL).
Responsabilidad:
- Abstraer las consultas SQL mediante SQLAlchemy ORM.
- Proporcionar métodos CRUD básicos y búsquedas especializadas.
- Delegar la confirmación de transacciones (commit) a la capa de Servicio.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from database.models import Asignatura, ProgramaAsignatura
from constants.enums import Periodo, ModalidadAsignatura, Idioma

class AsignaturaRepository:
    """Gestor de persistencia para asignaturas."""

    # ==========================
    # LECTURA (Consultas)
    # ==========================

    def get_by_id(self, db: Session, asignatura_id: int) -> Optional[Asignatura]:
        """Busca una asignatura por su identificador primario."""
        return db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()

    def get_by_codigo(self, db: Session, codigo_plan: str) -> Optional[Asignatura]:
        """Busca una asignatura por su código de plan de estudios (único)."""
        return db.query(Asignatura).filter(Asignatura.codigo_plan == codigo_plan).first()

    def get_by_programa(
        self, db: Session, programa_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Asignatura], int]:
        """Recupera las asignaturas asociadas a un programa específico."""
        query = (
            db.query(Asignatura)
            .join(ProgramaAsignatura, ProgramaAsignatura.asignatura_id == Asignatura.id)
            .filter(ProgramaAsignatura.programa_id == programa_id)
        )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        periodo: Optional[Periodo] = None,
        modalidad: Optional[ModalidadAsignatura] = None,
        idioma: Optional[Idioma] = None,
        activo: Optional[bool] = None,
    ) -> Tuple[List[Asignatura], int]:
        """Lista asignaturas con filtros y paginación."""
        query = db.query(Asignatura)
        
        if periodo:
            query = query.filter(Asignatura.periodo == periodo)
        if modalidad:
            query = query.filter(Asignatura.modalidad == modalidad)
        if idioma:
            query = query.filter(Asignatura.idioma == idioma)
        if activo is not None:
            query = query.filter(Asignatura.activo == activo)

        total = query.count()
        query = query.order_by(Asignatura.codigo_plan.asc())
        
        # Eager loading para optimizar rendimiento
        items = query.offset(skip).limit(limit).options(
            joinedload(Asignatura.programa_asignaturas).joinedload(ProgramaAsignatura.programa)
        ).all()

        return items, total

    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================

    def create(self, db: Session, asignatura_data: dict) -> Asignatura:
        """Crea una asignatura y hace flush para generar ID."""
        db_asignatura = Asignatura(**asignatura_data)
        db.add(db_asignatura)
        db.flush()
        db.refresh(db_asignatura)
        return db_asignatura

    def update(
        self, db: Session, asignatura_id: int, asignatura_data: dict
    ) -> Optional[Asignatura]:
        """Actualiza parcialmente una asignatura."""
        db_asignatura = self.get_by_id(db, asignatura_id)
        if not db_asignatura:
            return None

        for field, value in asignatura_data.items():
            if value is not None:
                setattr(db_asignatura, field, value)

        db.flush()
        db.refresh(db_asignatura)
        return db_asignatura

    def delete(self, db: Session, asignatura_id: int) -> bool:
        """Soft Delete: Marca la asignatura como inactiva."""
        db_asignatura = self.get_by_id(db, asignatura_id)
        if not db_asignatura:
            return False

        db_asignatura.activo = False
        db.flush()
        return True

    def delete_physical(self, db: Session, asignatura_id: int) -> bool:
        """Hard Delete: Elimina físicamente el registro de la base de datos."""
        db_asignatura = self.get_by_id(db, asignatura_id)
        if not db_asignatura:
            return False

        db.delete(db_asignatura)
        db.flush()
        return True

    def exists_by_codigo(
        self, db: Session, codigo_plan: str, exclude_id: Optional[int] = None
    ) -> bool:
        """Verifica existencia de duplicados por código."""
        query = db.query(Asignatura).filter(Asignatura.codigo_plan == codigo_plan)
        if exclude_id is not None:
            query = query.filter(Asignatura.id != exclude_id)
        return db.query(query.exists()).scalar()

asignatura_repository = AsignaturaRepository()