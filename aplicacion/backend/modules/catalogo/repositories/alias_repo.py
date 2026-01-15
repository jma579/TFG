"""
Repositorio para la entidad AsignaturaAlias.

Capa de Acceso a Datos (DAL).
Responsabilidad:
- Abstraer las consultas SQL mediante SQLAlchemy ORM.
- Proporcionar métodos CRUD básicos y búsquedas especializadas.
- Delegar la confirmación de transacciones (commit) a la capa de Servicio.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import AsignaturaAlias


class AsignaturaAliasRepository:
    """
    Gestor de persistencia para AsignaturaAlias.
    """
    
    # ==========================
    # LECTURA
    # ==========================

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

    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================

    def register_usage(
            self,  db: Session, asignatura_id: int, alias: str, origen: str = "HORARIO_FEEDBACK"
    ) -> AsignaturaAlias:
        """Registra el uso de un alias para una asignatura."""
        # Normalización básica antes de buscar
        alias_clean = " ".join(alias.strip().split())
        
        if not alias_clean:
            # Si tras limpiar no queda texto, retornamos None o lanzamos error.
            # Aquí optamos por seguridad y lanzamos ValueError.
            raise ValueError("El texto del alias no puede estar vacío")

        instance = self.get_by_texto(db, asignatura_id, alias_clean)
        
        if instance:
            # Aprendizaje: Refuerzo positivo
            instance.veces_usado += 1
            # No es necesario db.add(instance) explícito si ya está en sesión, 
            # pero es buena práctica para asegurar estado dirty.
            db.add(instance)
        else:
            # Aprendizaje: Nuevo conocimiento
            instance = AsignaturaAlias(
                asignatura_id=asignatura_id,
                alias=alias_clean,
                origen=origen,
                veces_usado=1
            )
            db.add(instance)
        
        # Flush para que el ID esté disponible y constraints validadas, 
        # pero SIN COMMIT (responsabilidad del Service).
        db.flush()
        db.refresh(instance)
        
        return instance

    def delete(self, db: Session, id: int) -> bool:
        """Elimina un alias (si fue un aprendizaje erróneo)."""
        obj = db.query(AsignaturaAlias).filter(AsignaturaAlias.id == id).first()
        if not obj:
            return False
        db.delete(obj)
        db.flush()
        return True


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

alias_repository = AsignaturaAliasRepository()