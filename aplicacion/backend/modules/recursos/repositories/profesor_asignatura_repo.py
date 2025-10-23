"""
Repository para la tabla intermedia ProfesorAsignatura.

Responsabilidades:
- Asociar profesores con asignaturas (relación N:M)
- Buscar asignaturas de un profesor
- Buscar profesores de una asignatura
- Verificar existencia de relaciones
- Eliminar relaciones
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import ProfesorAsignatura, Profesor, Asignatura


class ProfesorAsignaturaRepository:
    """
    Repository para gestionar relaciones Profesor-Asignatura.
    
    Esta clase maneja la tabla intermedia 'profesores_asignaturas' que
    implementa la relación muchos-a-muchos entre Profesor y Asignatura.
    """
    
    def create(
        self,
        db: Session,
        profesor_id: int,
        asignatura_id: int
    ) -> ProfesorAsignatura:
        """
        Crear relación Profesor-Asignatura.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            asignatura_id: ID de la asignatura
            
        Returns:
            ProfesorAsignatura creada
            
        Raises:
            IntegrityError: Si la relación ya existe (violación UNIQUE constraint)
            
        Example:
            >>> rel = profesor_asignatura_repository.create(
            ...     db,
            ...     profesor_id=1,
            ...     asignatura_id=5
            ... )
            >>> print(rel.profesor_id, rel.asignatura_id)
            1 5
        """
        rel = ProfesorAsignatura(
            profesor_id=profesor_id,
            asignatura_id=asignatura_id
        )
        
        db.add(rel)
        db.flush()  # Flush para obtener ID sin hacer commit
        db.refresh(rel)
        return rel
    
    def get_by_profesor(
        self,
        db: Session,
        profesor_id: int
    ) -> List[ProfesorAsignatura]:
        """
        Obtener todas las asignaturas de un profesor.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            
        Returns:
            Lista de relaciones ProfesorAsignatura con asignaturas cargadas
            
        Note:
            Usa joinedload para cargar las asignaturas en la misma query (eager loading)
            y evitar el problema N+1.
            
        Example:
            >>> relaciones = profesor_asignatura_repository.get_by_profesor(db, profesor_id=1)
            >>> for rel in relaciones:
            ...     print(rel.asignatura.nombre)
            Cálculo I
            Álgebra Lineal
        """
        return db.query(ProfesorAsignatura)\
            .options(joinedload(ProfesorAsignatura.asignatura))\
            .filter(ProfesorAsignatura.profesor_id == profesor_id)\
            .all()
    
    def get_by_asignatura(
        self,
        db: Session,
        asignatura_id: int
    ) -> List[ProfesorAsignatura]:
        """
        Obtener todos los profesores de una asignatura.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            
        Returns:
            Lista de relaciones ProfesorAsignatura con profesores cargados
            
        Note:
            Usa joinedload para cargar los profesores en la misma query (eager loading).
            
        Example:
            >>> relaciones = profesor_asignatura_repository.get_by_asignatura(db, asignatura_id=5)
            >>> for rel in relaciones:
            ...     print(f"{rel.profesor.nombre} {rel.profesor.apellidos}")
            Juan Pérez
            María García
        """
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
        """
        Verificar si ya existe la relación Profesor-Asignatura.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            asignatura_id: ID de la asignatura
            
        Returns:
            True si existe, False si no
            
        Note:
            Útil para evitar intentar crear relaciones duplicadas antes de llamar a create().
            
        Example:
            >>> if not profesor_asignatura_repository.exists(db, 1, 5):
            ...     profesor_asignatura_repository.create(db, 1, 5)
        """
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
        """
        Eliminar relación Profesor-Asignatura.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            asignatura_id: ID de la asignatura
            
        Returns:
            True si se eliminó, False si no existía
            
        Example:
            >>> deleted = profesor_asignatura_repository.delete(db, 1, 5)
            >>> if deleted:
            ...     print("Relación eliminada")
        """
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
        """
        Eliminar todas las relaciones de una asignatura con profesores.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            
        Returns:
            Número de relaciones eliminadas
            
        Note:
            Útil cuando se elimina una asignatura o se quiere reemplazar
            completamente su lista de profesores.
            
        Example:
            >>> count = profesor_asignatura_repository.delete_all_by_asignatura(db, 5)
            >>> print(f"Eliminadas {count} relaciones")
            Eliminadas 3 relaciones
        """
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
        """
        Eliminar todas las relaciones de un profesor con asignaturas.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            
        Returns:
            Número de relaciones eliminadas
            
        Note:
            Útil cuando se elimina un profesor (aunque tu sistema usa soft delete).
            
        Example:
            >>> count = profesor_asignatura_repository.delete_all_by_profesor(db, 1)
            >>> print(f"Eliminadas {count} relaciones")
            Eliminadas 5 relaciones
        """
        result = db.query(ProfesorAsignatura)\
            .filter(ProfesorAsignatura.profesor_id == profesor_id)\
            .delete()
        
        db.flush()
        return result


# Singleton instance
profesor_asignatura_repository = ProfesorAsignaturaRepository()