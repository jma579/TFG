"""
Repository para la tabla intermedia ProgramaAsignatura.

Responsabilidades:
- Asociar asignaturas con programas (relación N:M)
- Gestionar tipo_asignatura y curso en la relación
- Buscar asignaturas de un programa
- Buscar programas de una asignatura
- Verificar existencia de relaciones
- Actualizar tipo y curso de relaciones existentes
- Eliminar relaciones
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import ProgramaAsignatura, Programa, Asignatura
from constants.enums import TipoAsignatura


class ProgramaAsignaturaRepository:
    """
    Repository para gestionar relaciones Programa-Asignatura.
    
    Esta clase maneja la tabla intermedia 'programas_asignaturas' que
    implementa la relación muchos-a-muchos entre Programa y Asignatura,
    incluyendo campos específicos de la relación (tipo_asignatura, curso).
    """
    
    def create(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int,
        curso: int,
        tipo_asignatura: TipoAsignatura
    ) -> ProgramaAsignatura:
        """
        Crear relación Programa-Asignatura con tipo y curso.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            asignatura_id: ID de la asignatura
            curso: Curso académico (1-6)
            tipo_asignatura: Tipo de asignatura (BASICA, OBLIGATORIA, OPTATIVA)
            
        Returns:
            ProgramaAsignatura creada
            
        Raises:
            IntegrityError: Si la relación ya existe (violación UNIQUE constraint)
            
        Example:
            >>> rel = programa_asignatura_repository.create(
            ...     db,
            ...     programa_id=1,
            ...     asignatura_id=5,
            ...     curso=1,
            ...     tipo_asignatura=TipoAsignatura.BASICA
            ... )
            >>> print(rel.curso, rel.tipo_asignatura)
            1 basica
        """
        rel = ProgramaAsignatura(
            programa_id=programa_id,
            asignatura_id=asignatura_id,
            curso=curso,
            tipo_asignatura=tipo_asignatura
        )
        
        db.add(rel)
        db.flush()  # Flush para obtener ID sin hacer commit
        db.refresh(rel)
        return rel
    
    def get_by_programa(
        self,
        db: Session,
        programa_id: int,
        curso: Optional[int] = None,
        tipo_asignatura: Optional[TipoAsignatura] = None
    ) -> List[ProgramaAsignatura]:
        """
        Obtener todas las asignaturas de un programa.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            curso: Filtrar por curso específico (opcional)
            tipo_asignatura: Filtrar por tipo específico (opcional)
            
        Returns:
            Lista de relaciones ProgramaAsignatura con asignaturas cargadas
            
        Note:
            Usa joinedload para cargar las asignaturas en la misma query (eager loading)
            y evitar el problema N+1.
            
        Example:
            >>> # Todas las asignaturas del programa
            >>> relaciones = programa_asignatura_repository.get_by_programa(db, programa_id=1)
            >>> 
            >>> # Solo asignaturas de primer curso
            >>> relaciones = programa_asignatura_repository.get_by_programa(
            ...     db, programa_id=1, curso=1
            ... )
            >>> 
            >>> # Solo asignaturas básicas
            >>> relaciones = programa_asignatura_repository.get_by_programa(
            ...     db, programa_id=1, tipo_asignatura=TipoAsignatura.BASICA
            ... )
        """
        query = db.query(ProgramaAsignatura)\
            .options(joinedload(ProgramaAsignatura.asignatura))\
            .filter(ProgramaAsignatura.programa_id == programa_id)
        
        # Filtros opcionales
        if curso is not None:
            query = query.filter(ProgramaAsignatura.curso == curso)
        
        if tipo_asignatura is not None:
            query = query.filter(ProgramaAsignatura.tipo_asignatura == tipo_asignatura)
        
        return query.all()
    
    def get_by_asignatura(
        self,
        db: Session,
        asignatura_id: int
    ) -> List[ProgramaAsignatura]:
        """
        Obtener todos los programas de una asignatura.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            
        Returns:
            Lista de relaciones ProgramaAsignatura con programas cargados
            
        Note:
            Usa joinedload para cargar los programas en la misma query (eager loading).
            
        Example:
            >>> relaciones = programa_asignatura_repository.get_by_asignatura(db, asignatura_id=5)
            >>> for rel in relaciones:
            ...     print(f"{rel.programa.nombre} - Curso {rel.curso} - {rel.tipo_asignatura}")
            Grado en Matemáticas - Curso 1 - basica
            Grado en Física - Curso 1 - basica
        """
        return db.query(ProgramaAsignatura)\
            .options(joinedload(ProgramaAsignatura.programa))\
            .filter(ProgramaAsignatura.asignatura_id == asignatura_id)\
            .all()
    
    def get_by_programa_and_asignatura(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int
    ) -> Optional[ProgramaAsignatura]:
        """
        Obtener relación específica Programa-Asignatura.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            asignatura_id: ID de la asignatura
            
        Returns:
            ProgramaAsignatura si existe, None si no
            
        Example:
            >>> rel = programa_asignatura_repository.get_by_programa_and_asignatura(db, 1, 5)
            >>> if rel:
            ...     print(f"Curso: {rel.curso}, Tipo: {rel.tipo_asignatura}")
        """
        return db.query(ProgramaAsignatura)\
            .filter(
                ProgramaAsignatura.programa_id == programa_id,
                ProgramaAsignatura.asignatura_id == asignatura_id
            )\
            .first()
    
    def exists(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int
    ) -> bool:
        """
        Verificar si ya existe la relación Programa-Asignatura.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            asignatura_id: ID de la asignatura
            
        Returns:
            True si existe, False si no
            
        Note:
            Útil para evitar intentar crear relaciones duplicadas antes de llamar a create().
            
        Example:
            >>> if not programa_asignatura_repository.exists(db, 1, 5):
            ...     programa_asignatura_repository.create(db, 1, 5, curso=1, tipo_asignatura=TipoAsignatura.BASICA)
        """
        return db.query(ProgramaAsignatura)\
            .filter(
                ProgramaAsignatura.programa_id == programa_id,
                ProgramaAsignatura.asignatura_id == asignatura_id
            )\
            .first() is not None
    
    def update_tipo_curso(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int,
        curso: Optional[int] = None,
        tipo_asignatura: Optional[TipoAsignatura] = None
    ) -> Optional[ProgramaAsignatura]:
        """
        Actualizar tipo_asignatura y/o curso de una relación existente.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            asignatura_id: ID de la asignatura
            curso: Nuevo curso (si se proporciona)
            tipo_asignatura: Nuevo tipo (si se proporciona)
            
        Returns:
            ProgramaAsignatura actualizada si existe, None si no
            
        Note:
            Solo actualiza los campos proporcionados (no None).
            
        Example:
            >>> # Actualizar solo el curso
            >>> rel = programa_asignatura_repository.update_tipo_curso(
            ...     db, programa_id=1, asignatura_id=5, curso=2
            ... )
            >>> 
            >>> # Actualizar solo el tipo
            >>> rel = programa_asignatura_repository.update_tipo_curso(
            ...     db, programa_id=1, asignatura_id=5, 
            ...     tipo_asignatura=TipoAsignatura.OBLIGATORIA
            ... )
            >>> 
            >>> # Actualizar ambos
            >>> rel = programa_asignatura_repository.update_tipo_curso(
            ...     db, programa_id=1, asignatura_id=5, 
            ...     curso=3, tipo_asignatura=TipoAsignatura.OPTATIVA
            ... )
        """
        rel = db.query(ProgramaAsignatura)\
            .filter(
                ProgramaAsignatura.programa_id == programa_id,
                ProgramaAsignatura.asignatura_id == asignatura_id
            )\
            .first()
        
        if not rel:
            return None
        
        # Actualizar solo los campos proporcionados
        if curso is not None:
            rel.curso = curso
        
        if tipo_asignatura is not None:
            rel.tipo_asignatura = tipo_asignatura
        
        db.flush()
        db.refresh(rel)
        return rel
    
    def delete(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int
    ) -> bool:
        """
        Eliminar relación Programa-Asignatura.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            asignatura_id: ID de la asignatura
            
        Returns:
            True si se eliminó, False si no existía
            
        Example:
            >>> deleted = programa_asignatura_repository.delete(db, 1, 5)
            >>> if deleted:
            ...     print("Relación eliminada")
        """
        result = db.query(ProgramaAsignatura)\
            .filter(
                ProgramaAsignatura.programa_id == programa_id,
                ProgramaAsignatura.asignatura_id == asignatura_id
            )\
            .delete()
        
        db.flush()
        return result > 0
    
    def delete_all_by_programa(
        self,
        db: Session,
        programa_id: int
    ) -> int:
        """
        Eliminar todas las relaciones de un programa con asignaturas.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            
        Returns:
            Número de relaciones eliminadas
            
        Note:
            Útil cuando se elimina un programa.
            
        Example:
            >>> count = programa_asignatura_repository.delete_all_by_programa(db, 1)
            >>> print(f"Eliminadas {count} relaciones")
            Eliminadas 50 relaciones
        """
        result = db.query(ProgramaAsignatura)\
            .filter(ProgramaAsignatura.programa_id == programa_id)\
            .delete()
        
        db.flush()
        return result
    
    def delete_all_by_asignatura(
        self,
        db: Session,
        asignatura_id: int
    ) -> int:
        """
        Eliminar todas las relaciones de una asignatura con programas.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            
        Returns:
            Número de relaciones eliminadas
            
        Note:
            Útil cuando se elimina una asignatura o se quiere reemplazar
            completamente su lista de programas.
            
        Example:
            >>> count = programa_asignatura_repository.delete_all_by_asignatura(db, 5)
            >>> print(f"Eliminadas {count} relaciones")
            Eliminadas 3 relaciones
        """
        result = db.query(ProgramaAsignatura)\
            .filter(ProgramaAsignatura.asignatura_id == asignatura_id)\
            .delete()
        
        db.flush()
        return result


# Singleton instance
programa_asignatura_repository = ProgramaAsignaturaRepository()