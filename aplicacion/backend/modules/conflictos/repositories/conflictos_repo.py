"""
Repositorio de persistencia para la entidad Conflicto.

Responsabilidades:
- Sincronización (Wipe & Replace) de resultados del motor con la BD.
- Búsqueda filtrada de conflictos.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, select

from database.models import Conflicto, Sesion, GrupoDocente, Asignatura, ProgramaAsignatura
from core.conflictos.types import ResultadoDeteccion
from constants.enums import EstadoConflicto


class ConflictosRepository:
    """
    Gestor de persistencia para Conflictos.
    Actúa como adaptador entre el Core (ResultadoDeteccion) y el ORM.
    """

    def get_by_id(self, db: Session, id: int) -> Optional[Conflicto]:
        return db.query(Conflicto).filter(Conflicto.id == id).first()

    def search(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        tipo=None,
        severidad=None,
        estado=None,
        profesor_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        sesion_id: Optional[int] = None,
    ) -> Tuple[List[Conflicto], int]:
        """Busca conflictos aplicando filtros dinámicos."""
        query = db.query(Conflicto)

        def cargar_ramas_sesion(entidad_sesion):
            return [
                entidad_sesion.joinedload(Sesion.aula),
                entidad_sesion.joinedload(Sesion.grupo_docente)
                    .joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.programa_asignaturas)
                    .joinedload(ProgramaAsignatura.programa),
                entidad_sesion.joinedload(Sesion.grupo_docente)
                    .joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.programa_asignaturas)
                    .joinedload(ProgramaAsignatura.mencion)
            ]

        query = db.query(Conflicto).options(
            *cargar_ramas_sesion(joinedload(Conflicto.sesion)),
            *cargar_ramas_sesion(joinedload(Conflicto.sesion_2)),
            joinedload(Conflicto.aula),
            joinedload(Conflicto.profesor)
        )

        if tipo: query = query.filter(Conflicto.tipo == tipo)
        if severidad: query = query.filter(Conflicto.severidad == severidad)
        if estado: query = query.filter(Conflicto.estado == estado)
        if profesor_id: query = query.filter(Conflicto.profesor_id == profesor_id)
        if aula_id: query = query.filter(Conflicto.aula_id == aula_id)
        
        if sesion_id:
            query = query.filter(
                or_(Conflicto.sesion_id == sesion_id, Conflicto.sesion_2_id == sesion_id)
            )

        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def sync_conflictos_for_sesion(
        self,
        db: Session,
        sesion_id: int,
        resultados_engine: List[ResultadoDeteccion]
    ) -> List[Conflicto]:
        """
        Sincroniza los conflictos de una sesión (Estrategia Wipe & Replace).
        
        1. Elimina conflictos previos donde la sesión es la principal O secundaria.
        2. Inserta los nuevos detectados por el motor.
        """
        db.query(Conflicto).filter(
            or_(
                Conflicto.sesion_id == sesion_id,
                Conflicto.sesion_2_id == sesion_id
            )
        ).delete(synchronize_session='fetch')

        conflictos_orm = []

        for res in resultados_engine:
            nuevo_conflicto = Conflicto(
                tipo=res.tipo,
                severidad=res.severidad,
                estado=EstadoConflicto.POR_REVISAR,
                descripcion=res.descripcion,
                hash_deteccion=res.hash_deteccion,
                
                sesion_id=res.sesion_id,
                sesion_2_id=res.sesion_2_id,
                profesor_id=res.profesor_id,
                aula_id=res.aula_id,
                restriccion_id=res.restriccion_id
            )
            conflictos_orm.append(nuevo_conflicto)

        if conflictos_orm:
            db.add_all(conflictos_orm)
            
        return conflictos_orm
    
    def delete(self, db: Session, id: int) -> bool:
        """Elimina un conflicto específico por su ID."""
        eliminados = db.query(Conflicto).filter(Conflicto.id == id).delete()
        return eliminados > 0

    def delete_by_sesion_fisico(self, db: Session, sesion_id: int):
        """Elimina físicamente todos los conflictos relacionados con una sesión."""
        db.query(Conflicto).filter(
            or_(
                Conflicto.sesion_id == sesion_id,
                Conflicto.sesion_2_id == sesion_id
            )
        ).delete(synchronize_session='fetch')
        db.flush()

    def delete_by_asignatura(self, db: Session, asignatura_id: int):
        """
        Elimina masivamente todos los conflictos donde participe cualquier sesión
        de la asignatura indicada (ya sea como principal o secundaria).
        """
        sq_sesiones = db.query(Sesion.id)\
            .join(GrupoDocente)\
            .filter(GrupoDocente.asignatura_id == asignatura_id)\
            .subquery()

        db.query(Conflicto).filter(
            or_(
                Conflicto.sesion_id.in_(select(sq_sesiones)),
                Conflicto.sesion_2_id.in_(select(sq_sesiones))
            )
        ).delete(synchronize_session=False) 
        
        db.flush()
        

conflictos_repository = ConflictosRepository()