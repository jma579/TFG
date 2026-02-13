"""
Repositorio de persistencia para la entidad Sesion.

Responsabilidades:
- CRUD de sesiones.
- Búsqueda por filtros.

"""

from typing import Optional, Tuple, List, Dict, Any, Union
from sqlalchemy.orm import Session, joinedload

from database.models import Sesion, ProfesorSesion, GrupoDocente, Asignatura, Mencion, ProgramaAsignatura
from constants.enums import Periodo


class SesionRepository:
    """
    Gestor de persistencia para la entidad Sesion y sus relaciones.
    """

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
    
    def get_sesiones_for_engine(self, db: Session) -> List[Sesion]:
        """Recupera todas las sesiones con los JOINS necesarios para el motor."""
        return db.query(Sesion).options(
            joinedload(Sesion.profesores_sesiones),
            joinedload(Sesion.aula),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.programa_asignaturas)
                .joinedload(ProgramaAsignatura.mencion),
            joinedload(Sesion.grupo_docente)
                .joinedload(GrupoDocente.asignatura)
                .joinedload(Asignatura.programa_asignaturas)
                .joinedload(ProgramaAsignatura.programa)
        ).all()

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        programa_id: Optional[int] = None,
        curso: Optional[int] = None,
        periodo: Optional[Periodo] = None,
        aula_id: Optional[int] = None,
        mencion_id: Optional[int] = None
    ) -> Tuple[List[Sesion], int]:
        """Recupera sesiones con filtros avanzados. """
        query = db.query(Sesion).join(Sesion.grupo_docente).join(GrupoDocente.asignatura)

        if programa_id or curso or mencion_id:
            query = query.join(Asignatura.programa_asignaturas)
            
            if programa_id:
                query = query.filter(ProgramaAsignatura.programa_id == programa_id)
            if curso:
                query = query.filter(ProgramaAsignatura.curso == curso)
            if mencion_id:
                query = query.filter(ProgramaAsignatura.mencion_id == mencion_id)

        if periodo:
            query = query.filter(Asignatura.periodo == periodo)

        if aula_id:
            query = query.filter(Sesion.aula_id == aula_id)

        query = query.options(
            joinedload(Sesion.aula),
            joinedload(Sesion.grupo_docente).joinedload(GrupoDocente.asignatura),
            joinedload(Sesion.profesores_sesiones).joinedload(ProfesorSesion.profesor)
        ).distinct()

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total


    def create(self, db: Session, data: Union[dict, Any]) -> Sesion:
        """Crea una sesión. Los profesores se deben añadir posteriormente o mediante lógica en el service."""
        if hasattr(data, "model_dump"):
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
    
    def delete_by_schedule_params(
        self, 
        db: Session, 
        programa_id: int, 
        curso: int, 
        cuatrimestre: int, 
        mencion: Optional[str] = None
    ) -> int:
        """
        Borra sesiones filtrando por la jerarquía de Programa -> Asignatura -> Grupo -> Sesion.
        """
        periodo_enum = Periodo.PRIMER_CUATRIMESTRE if cuatrimestre == 1 else Periodo.SEGUNDO_CUATRIMESTRE
        query = db.query(Sesion).join(GrupoDocente).join(Asignatura).join(ProgramaAsignatura)
        
        filters = [
            ProgramaAsignatura.programa_id == programa_id,
            ProgramaAsignatura.curso == curso,     
            Asignatura.periodo == periodo_enum
        ]

        if mencion:
            query = query.join(ProgramaAsignatura.mencion)
            filters.append(Mencion.nombre == mencion)
        else:
            filters.append(ProgramaAsignatura.mencion_id.is_(None))

        ids_to_delete = [s.id for s in query.filter(*filters).all()]
        
        if not ids_to_delete:
            return 0

        count = db.query(Sesion).filter(Sesion.id.in_(ids_to_delete)).delete(synchronize_session=False)
        
        db.flush() 
        return count


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
        """Reemplazo completo de la lista de profesores de una sesión."""
        db.query(ProfesorSesion).filter(ProfesorSesion.sesion_id == sesion_id).delete()
        
        for p in profesores_data:
            self.add_profesor(
                db, 
                sesion_id=sesion_id, 
                profesor_id=p['profesor_id'],
                rol_en_sesion=p.get('rol_en_sesion')
            )
        db.flush()


sesion_repository = SesionRepository()