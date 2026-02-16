"""
Repositorio para la entidad Restriccion.
Capa de Acceso a Datos (DAL).
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import Restriccion
from modules.recursos.schemas.restriccion import RestriccionCreate, RestriccionUpdate


class RestriccionRepository:
    """Gestor de persistencia para restricciones."""


    def get_by_id(self, db: Session, restriccion_id: int) -> Optional[Restriccion]:
        """Obtiene una restricción específica por su ID."""
        return db.query(Restriccion).filter(Restriccion.id == restriccion_id).first()


    def get_by_profesor(self, db: Session, profesor_id: int) -> List[Restriccion]:
        """Obtiene todas las restricciones de un profesor."""
        return db.query(Restriccion)\
            .filter(Restriccion.profesor_id == profesor_id)\
            .order_by(Restriccion.dia_semana, Restriccion.hora_inicio)\
            .all()
    

    def create(self, db: Session, profesor_id: int, restriccion_in: RestriccionCreate) -> Restriccion:
        """Crea una nueva restricción individual en la base de datos."""
        db_obj = Restriccion(
            profesor_id=profesor_id,
            dia_semana=restriccion_in.dia_semana,
            hora_inicio=restriccion_in.hora_inicio,
            hora_fin=restriccion_in.hora_fin
        )
        db.add(db_obj)
        db.flush()
        return db_obj
    
    
    def bulk_create(self, db: Session, restricciones_db: List[Restriccion]) -> None:
        """Inserta una lista de objetos Restriccion de forma masiva. """
        db.add_all(restricciones_db)
        db.flush()


    def update(self, db: Session, db_obj: Restriccion, restriccion_in: RestriccionUpdate) -> Restriccion:
        """Actualiza una restricción existente (PATCH)."""
        update_data = restriccion_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.flush()
        return db_obj


    def delete(self, db: Session, db_obj: Restriccion) -> None:
        """Elimina una restricción de la base de datos."""
        db.delete(db_obj)
        db.flush()


    def delete_all(self, db: Session) -> int:
        """Elimina todas las restricciones del sistema."""
        filas_borradas = db.query(Restriccion).delete()
        db.flush()
        return filas_borradas
    

restriccion_repository = RestriccionRepository()