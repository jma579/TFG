"""
Repositorio de persistencia para la entidad Sesion.

Responsabilidades:
- CRUD de sesiones.
- Búsqueda por filtros.

"""

from typing import Optional, Tuple, List, Dict, Any, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, time

from database.models import Sesion, ProfesorSesion
from modules.docencia.schemas.sesion import SesionCreate, SesionUpdate
from constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana


class SesionRepository:
    """
    Gestor de persistencia para la entidad Sesion y sus relaciones.
    """

    # ==========================
    # LECTURA
    # ==========================

    def get_by_id(self, db: Session, id: int) -> Optional[Sesion]:
        """Obtiene una sesión por su ID con sus relaciones cargadas."""
        return db.query(Sesion)\
            .options(
                joinedload(Sesion.profesores_sesiones).joinedload(ProfesorSesion.profesor),
                joinedload(Sesion.aula),
                joinedload(Sesion.grupo_docente)
            )\
            .filter(Sesion.id == id)\
            .first()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        grupo_docente_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        profesor_id: Optional[int] = None,
        dia_semana: Optional[DiaSemana] = None
    ) -> Tuple[List[Sesion], int]:
        """Listar sesiones con filtros múltiples."""
        query = db.query(Sesion)

        if grupo_docente_id:
            query = query.filter(Sesion.grupo_docente_id == grupo_docente_id)
        if aula_id:
            query = query.filter(Sesion.aula_id == aula_id)
        if dia_semana:
            query = query.filter(Sesion.dia_semana == dia_semana)
        if profesor_id:
            # Join explícito para filtrar por relación M:N
            query = query.join(Sesion.profesores_sesiones).filter(
                ProfesorSesion.profesor_id == profesor_id
            )

        total = query.count()
        
        # Ordenar por día y hora para coherencia visual
        # Nota: La ordenación de DiaSemana (Enum) en BD depende del motor, 
        # aquí asumimos orden de inserción o alfabético. Idealmente usar CASE o int.
        query = query.order_by(Sesion.dia_semana, Sesion.hora_inicio)
        
        items = query.offset(skip).limit(limit).all()
        return items, total

    # ==========================
    # ESCRITURA (Sin Commit)
    # ==========================

    def create(self, db: Session, data: Union[dict, Any]) -> Sesion:
        """
        Crea una sesión.
        Nota: Los profesores se deben añadir posteriormente o mediante lógica en el service.
        """
        if hasattr(data, "model_dump"):
            # Excluimos profesores porque es una relación M:N que se gestiona aparte o después
            data_dict = data.model_dump(exclude={'profesores'}, exclude_unset=True)
        elif hasattr(data, "dict"):
            data_dict = data.dict(exclude={'profesores'}, exclude_unset=True)
        else:
            data_dict = data.copy()
            if 'profesores' in data_dict:
                del data_dict['profesores']

        db_sesion = Sesion(**data_dict)
        db.add(db_sesion)
        db.flush()
        db.refresh(db_sesion)
        return db_sesion

    def update(self, db: Session, db_obj: Sesion, data: Union[dict, Any]) -> Sesion:
        """Actualiza campos escalares de la sesión."""
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump(exclude={'profesores'}, exclude_unset=True)
        elif hasattr(data, "dict"):
            data_dict = data.dict(exclude={'profesores'}, exclude_unset=True)
        else:
            data_dict = data

        for field, value in data_dict.items():
            setattr(db_obj, field, value)
        
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        """Elimina físicamente una sesión."""
        obj = self.get_by_id(db, id)
        if not obj:
            return False
        db.delete(obj)
        db.flush()
        return True

    # ==========================
    # GESTIÓN DE PROFESORES
    # ==========================

    def add_profesor(
        self, 
        db: Session, 
        sesion_id: int, 
        profesor_id: int, 
        rol_en_sesion: Optional[str] = None
    ) -> ProfesorSesion:
        """Asigna un profesor a una sesión."""
        relacion = ProfesorSesion(
            sesion_id=sesion_id,
            profesor_id=profesor_id,
            rol_en_sesion=rol_en_sesion
        )
        db.add(relacion)
        db.flush()
        return relacion

    def remove_profesor(self, db: Session, sesion_id: int, profesor_id: int) -> bool:
        """Desvincula un profesor de una sesión."""
        result = db.query(ProfesorSesion).filter(
            ProfesorSesion.sesion_id == sesion_id,
            ProfesorSesion.profesor_id == profesor_id
        ).delete()
        db.flush()
        return result > 0
    
    def update_profesores(
        self, 
        db: Session, 
        sesion_id: int, 
        profesores_data: List[Dict[str, Any]]
    ):
        """
        Reemplazo completo de la lista de profesores de una sesión.
        Útil para el PUT de sesión.
        
        Args:
            profesores_data: Lista de dicts [{'profesor_id': 1, 'rol': 'T'}, ...]
        """
        # 1. Limpiar anteriores
        db.query(ProfesorSesion).filter(ProfesorSesion.sesion_id == sesion_id).delete()
        
        # 2. Insertar nuevos
        for p in profesores_data:
            self.add_profesor(
                db, 
                sesion_id=sesion_id, 
                profesor_id=p['profesor_id'],
                rol_en_sesion=p.get('rol_en_sesion')
            )
        db.flush()


sesion_repository = SesionRepository()