"""
Repositorio para la relación N:M entre Programa y Asignatura.

Gestiona la tabla intermedia que contiene atributos propios de la relación
como el 'curso' y el 'tipo de asignatura' (Obligatoria, Optativa, etc.).
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import ProgramaAsignatura, Mencion
from constants.enums import TipoAsignatura

class ProgramaAsignaturaRepository:
    """Gestor de persistencia para vinculaciones académicas."""

    def create(
        self,
        db: Session,
        programa_id: int,
        asignatura_id: int,
        curso: int,
        tipo_asignatura: TipoAsignatura,
        mencion_id: Optional[int]=None
    ) -> ProgramaAsignatura:
        """
        Crea una nueva vinculación entre programa y asignatura.
        """
        rel = ProgramaAsignatura(
            programa_id=programa_id,
            asignatura_id=asignatura_id,
            mencion_id=mencion_id,
            curso=curso,
            tipo_asignatura=tipo_asignatura,
        )
        db.add(rel)
        db.flush()
        db.refresh(rel)
        return rel

    def get_by_programa_and_asignatura(
        self, db: Session, programa_id: int, asignatura_id: int
    ) -> Optional[ProgramaAsignatura]:
        """Obtiene una relación específica por su clave compuesta."""
        return db.query(ProgramaAsignatura).filter(
            ProgramaAsignatura.programa_id == programa_id,
            ProgramaAsignatura.asignatura_id == asignatura_id
        ).first()
        
    def get_by_asignatura(self, db: Session, asignatura_id: int) -> List[ProgramaAsignatura]:
        """Obtiene todas las vinculaciones de una asignatura, precargando el programa."""
        return db.query(ProgramaAsignatura)\
            .options(joinedload(ProgramaAsignatura.programa))\
            .filter(ProgramaAsignatura.asignatura_id == asignatura_id)\
            .all()

    def exists(self, db: Session, programa_id: int, asignatura_id: int) -> bool:
        """Verifica si ya existe una vinculación."""
        return db.query(ProgramaAsignatura).filter(
            ProgramaAsignatura.programa_id == programa_id,
            ProgramaAsignatura.asignatura_id == asignatura_id
        ).first() is not None
    
    def update_tipo_curso_mencion( 
        self, 
        db: Session, 
        programa_id: int, 
        asignatura_id: int, 
        curso: Optional[int] = None, 
        tipo_asignatura: Optional[TipoAsignatura] = None,
        mencion_id: Optional[int] = None, # NUEVO
        remove_mencion: bool = False # NUEVO: flag explícito para poner mencion a null
    ) -> Optional[ProgramaAsignatura]:
        """Actualiza el curso, tipo o mención de una relación existente."""
        rel = self.get_by_programa_and_asignatura(db, programa_id, asignatura_id)
        if not rel:
            return None
            
        if curso is not None:
            rel.curso = curso
        if tipo_asignatura is not None:
            rel.tipo_asignatura = tipo_asignatura
        
        # NUEVO: Lógica de actualización de mención
        if remove_mencion:
            rel.mencion_id = None
        elif mencion_id is not None:
            # Validar que la mención pertenece al mismo programa
            mencion = db.query(Mencion).filter(Mencion.id == mencion_id).first()
            if not mencion or mencion.programa_id != programa_id:
                raise ValueError("La mención proporcionada no pertenece al programa de esta vinculación.")
            rel.mencion_id = mencion_id
            
        db.flush()
        db.refresh(rel)
        return rel
        
    def delete_all_by_asignatura(self, db: Session, asignatura_id: int) -> int:
        """
        Elimina todas las vinculaciones de una asignatura.
        Útil para procesos de resincronización completa.
        """
        count = db.query(ProgramaAsignatura).filter(
            ProgramaAsignatura.asignatura_id == asignatura_id
        ).delete()
        db.flush()
        return count


# Instancia única exportada
programa_asignatura_repository = ProgramaAsignaturaRepository()