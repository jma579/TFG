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

from database.models import Sesion, ProfesorSesion, GrupoDocente, Asignatura, AsignaturaMencion, Mencion
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
        dia_semana: Optional[DiaSemana] = None,
        modalidad: Optional[ModalidadSesion] = None,
        tipo_recurrencia: Optional[TipoRecurrencia] = None,
        curso: Optional[int] = None,
        mencion_id: Optional[int] = None,
        mencion_nombre: Optional[str] = None
    ) -> Tuple[List[Sesion], int]:
        """Listar sesiones con filtros múltiples."""
        query = db.query(Sesion)
        
        need_grupo_join = (curso is not None) or (mencion_id is not None) or (mencion_nombre is not None)
        if need_grupo_join:
            query = query.join(Sesion.grupo_docente)
        
        need_mencion_join = (mencion_id is not None) or (mencion_nombre is not None)
        if need_mencion_join:
            query = query.join(GrupoDocente.asignatura)\
                         .join(Asignatura.asignatura_menciones)

        # Si filtramos por NOMBRE, necesitamos un salto más hasta la tabla Mencion
        if mencion_nombre:
             query = query.join(AsignaturaMencion.mencion)

        # --- Aplicación de Filtros ---
        if grupo_docente_id:
            query = query.filter(Sesion.grupo_docente_id == grupo_docente_id)
        if aula_id:
            query = query.filter(Sesion.aula_id == aula_id)
        if dia_semana:
            query = query.filter(Sesion.dia_semana == dia_semana)
        if modalidad:
            query = query.filter(Sesion.modalidad == modalidad)
        if tipo_recurrencia:
            query = query.filter(Sesion.tipo_recurrencia == tipo_recurrencia)
        if profesor_id:
            query = query.join(Sesion.profesores_sesiones).filter(
                ProfesorSesion.profesor_id == profesor_id
            )
        
        # Filtros jerárquicos
        if curso is not None:
            query = query.filter(GrupoDocente.curso == curso)
        
        if mencion_id is not None:
            query = query.filter(AsignaturaMencion.mencion_id == mencion_id)
            
        if mencion_nombre is not None:
            # ilike para que sea insensible a mayúsculas/minúsculas (robusto)
            query = query.filter(Mencion.nombre.ilike(mencion_nombre))

        # DISTINCT es vital cuando hacemos joins de 1:N (asignatura -> menciones)
        # para evitar que una sesión salga duplicada si la asignatura tiene varias menciones.
        query = query.distinct()

        total = query.count()
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