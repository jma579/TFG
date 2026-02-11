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

from database.models import Sesion, ProfesorSesion, GrupoDocente, Asignatura, Mencion, ProgramaAsignatura
from modules.docencia.schemas.sesion import SesionCreate, SesionUpdate
from constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana, Periodo


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
    
    def get_sesiones_for_engine(self, db: Session) -> List[Sesion]:
        """
        Recupera todas las sesiones con los JOINS necesarios para el motor.
        Implementa la nueva lógica contextual de menciones.
        """
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
        """
        Recupera sesiones con filtros avanzados. 
        Cruza con Asignatura y ProgramaAsignatura para filtrar por contexto académico.
        """
        # Partimos de Sesion -> GrupoDocente -> Asignatura
        query = db.query(Sesion).join(Sesion.grupo_docente).join(GrupoDocente.asignatura)

        # Filtro Académico Contextual (Programa, Curso, Mención)
        # Usamos la nueva tabla ProgramaAsignatura para todo el contexto del Grado/Máster
        if programa_id or curso or mencion_id:
            query = query.join(Asignatura.programa_asignaturas)
            
            if programa_id:
                query = query.filter(ProgramaAsignatura.programa_id == programa_id)
            if curso:
                query = query.filter(ProgramaAsignatura.curso == curso)
            if mencion_id:
                query = query.filter(ProgramaAsignatura.mencion_id == mencion_id)

        # Filtro por Periodo (Cuatrimestre / Anual)
        if periodo:
            query = query.filter(Asignatura.periodo == periodo)

        # Filtro por Aula
        if aula_id:
            query = query.filter(Sesion.aula_id == aula_id)

        # Optimizaciones de carga (Eager Loading)
        query = query.options(
            joinedload(Sesion.aula),
            joinedload(Sesion.grupo_docente).joinedload(GrupoDocente.asignatura),
            joinedload(Sesion.profesores_sesiones).joinedload(ProfesorSesion.profesor)
        ).distinct()

        total = query.count()
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

        # 1. Mapeo según Periodo en models.py: PRIMERO para cuatri 1, SEGUNDO para cuatri 2
        periodo_enum = Periodo.PRIMER_CUATRIMESTRE if cuatrimestre == 1 else Periodo.SEGUNDO_CUATRIMESTRE

        # 2. Construir la consulta base
        # En tu models.py, Asignatura tiene el atributo 'curso'
        query = db.query(Sesion).join(GrupoDocente).join(Asignatura).join(ProgramaAsignatura)
        
        filters = [
            ProgramaAsignatura.programa_id == programa_id,
            ProgramaAsignatura.curso == curso,     
            Asignatura.periodo == periodo_enum
        ]

        # 3. Filtro por mención
        if mencion:
            query = query.join(ProgramaAsignatura.mencion)
            filters.append(Mencion.nombre == mencion)
        else:
            # PROTECCIÓN: Si no pasan mención, borramos SOLO las asignaturas del tronco general
            filters.append(ProgramaAsignatura.mencion_id.is_(None))

        # 4. Obtener IDs y ejecutar borrado
        ids_to_delete = [s.id for s in query.filter(*filters).all()]
        
        if not ids_to_delete:
            return 0

        # Al borrar Sesion, se limpian las relaciones N:M por las FKs definidas
        count = db.query(Sesion).filter(Sesion.id.in_(ids_to_delete)).delete(synchronize_session=False)
        
        db.flush() 
        return count

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