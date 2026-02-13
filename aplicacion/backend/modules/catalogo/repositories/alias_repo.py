"""
Repositorio para la entidad AsignaturaAlias.

Proporciona métodos CRUD y búsquedas especializadas para gestionar
alias de asignaturas. Abstrae las consultas SQL mediante SQLAlchemy ORM.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import AsignaturaAlias


class AsignaturaAliasRepository:
    """Gestor de persistencia para AsignaturaAlias."""
    
    def get_by_texto(self, db: Session, asignatura_id: int, alias: str) -> Optional[AsignaturaAlias]:
        """Busca un alias por su texto (case insensitive) para una asignatura dada."""
        return db.query(AsignaturaAlias).filter(
            AsignaturaAlias.asignatura_id == asignatura_id,
            func.lower(AsignaturaAlias.alias) == alias.strip().lower()
        ).first()

    def get_all_by_asignatura(self, db: Session, asignatura_id: int) -> List[AsignaturaAlias]:
        """Devuelve todos los alias conocidos de una asignatura."""
        return db.query(AsignaturaAlias).filter(
            AsignaturaAlias.asignatura_id == asignatura_id
        ).all()

    def register_usage(
        self, db: Session, asignatura_id: int, alias: str, origen: str = "HORARIO_FEEDBACK"
    ) -> AsignaturaAlias:
        """
        Registra el uso de un alias para una asignatura.
        
        Si el alias ya existe, incrementa su contador de usos.
        Si es nuevo, lo crea con contador en 1.
        """
        alias_clean = " ".join(alias.strip().split())
        
        if not alias_clean:
            raise ValueError("El texto del alias no puede estar vacío")

        instance = self.get_by_texto(db, asignatura_id, alias_clean)
        
        if instance:
            instance.veces_usado += 1
            db.add(instance)
        else:
            instance = AsignaturaAlias(
                asignatura_id=asignatura_id,
                alias=alias_clean,
                origen=origen,
                veces_usado=1
            )
            db.add(instance)
        
        db.flush()
        db.refresh(instance)
        
        return instance

    def delete(self, db: Session, id: int) -> bool:
        """Elimina un alias por su ID."""
        obj = db.query(AsignaturaAlias).filter(AsignaturaAlias.id == id).first()
        if not obj:
            return False
        
        db.delete(obj)
        db.flush()
        return True


alias_repository = AsignaturaAliasRepository()