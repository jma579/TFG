"""
Repository para la tabla intermedia ProfesorAsignatura.

Responsabilidades:
- Asociar profesores con asignaturas (relación N:M)
- Buscar asignaturas de un profesor
- Buscar profesores de una asignatura
- Verificar existencia de relaciones
- Eliminar relaciones
"""

from typing import List
from sqlalchemy.orm import Session, joinedload
from database.models import ProfesorAsignatura


class ProfesorAsignaturaRepository:
    """Repository para gestionar relaciones Profesor-Asignatura."""
    
    def create(
        self,
        db: Session,
        profesor_id: int,
        asignatura_id: int
    ) -> ProfesorAsignatura:
        """Crear relación Profesor-Asignatura."""
        rel = ProfesorAsignatura(
            profesor_id=profesor_id,
            asignatura_id=asignatura_id
        )
        
        db.add(rel)
        db.flush()
        db.refresh(rel)
        return rel
    
    def get_by_profesor(
        self,
        db: Session,
        profesor_id: int
    ) -> List[ProfesorAsignatura]:
        """Obtener todas las asignaturas de un profesor."""
        return db.query(ProfesorAsignatura)\
            .options(joinedload(ProfesorAsignatura.asignatura))\
            .filter(ProfesorAsignatura.profesor_id == profesor_id)\
            .all()
    
    def get_by_asignatura(
        self,
        db: Session,
        asignatura_id: int
    ) -> List[ProfesorAsignatura]:
        """Obtener todos los profesores de una asignatura."""
        return db.query(ProfesorAsignatura)\
            .options(joinedload(ProfesorAsignatura.profesor))\
            .filter(ProfesorAsignatura.asignatura_id == asignatura_id)\
            .all()
    
    def exists(
        self,
        db: Session,
        profesor_id: int,
        asignatura_id: int
    ) -> bool:
        """Verificar si ya existe la relación Profesor-Asignatura."""
        return db.query(ProfesorAsignatura)\
            .filter(
                ProfesorAsignatura.profesor_id == profesor_id,
                ProfesorAsignatura.asignatura_id == asignatura_id
            )\
            .first() is not None
    
    def delete(
        self,
        db: Session,
        profesor_id: int,
        asignatura_id: int
    ) -> bool:
        """Eliminar relación Profesor-Asignatura."""
        result = db.query(ProfesorAsignatura)\
            .filter(
                ProfesorAsignatura.profesor_id == profesor_id,
                ProfesorAsignatura.asignatura_id == asignatura_id
            )\
            .delete()
        
        db.flush()
        return result > 0
    
    def delete_all_by_asignatura(
        self,
        db: Session,
        asignatura_id: int
    ) -> int:
        """Eliminar todas las relaciones de una asignatura con profesores."""
        result = db.query(ProfesorAsignatura)\
            .filter(ProfesorAsignatura.asignatura_id == asignatura_id)\
            .delete()
        
        db.flush()
        return result
    
    def delete_all_by_profesor(
        self,
        db: Session,
        profesor_id: int
    ) -> int:
        """Eliminar todas las relaciones de un profesor con asignaturas."""
        result = db.query(ProfesorAsignatura)\
            .filter(ProfesorAsignatura.profesor_id == profesor_id)\
            .delete()
        
        db.flush()
        return result


profesor_asignatura_repository = ProfesorAsignaturaRepository()