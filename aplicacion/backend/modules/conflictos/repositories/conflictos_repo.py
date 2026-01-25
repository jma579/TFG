"""
Repositorio de persistencia para la entidad Conflicto.

Responsabilidades:
- Sincronización (Wipe & Replace) de resultados del motor con la BD.
- Búsqueda filtrada de conflictos.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from database.models import Conflicto, Sesion, GrupoDocente, Asignatura, ProgramaAsignatura, AsignaturaMencion
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
        """
        Busca conflictos aplicando filtros dinámicos.
        Carga Eager (joinedload) profunda para mostrar Titulación, Mención y Periodo en el Frontend.
        """
        query = db.query(Conflicto)

        def cargar_ramas_sesion(entidad_sesion):
            return [
                # 1. Aula
                entidad_sesion.joinedload(Sesion.aula),
                
                # 2. Asignatura -> Menciones (Rama A)
                entidad_sesion.joinedload(Sesion.grupo_docente)
                    .joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),

                # 3. Asignatura -> Programas (Rama B - Separada)
                entidad_sesion.joinedload(Sesion.grupo_docente)
                    .joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.programa_asignaturas)
                    .joinedload(ProgramaAsignatura.programa)
            ]

        query = db.query(Conflicto).options(
            # Cargamos relaciones de la Sesión 1
            *cargar_ramas_sesion(joinedload(Conflicto.sesion)),
            
            # Cargamos relaciones de la Sesión 2
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
        
        Args:
            db: Sesión SQLAlchemy
            sesion_id: ID de la sesión que se ha modificado/creado
            resultados_engine: Lista de DTOs provenientes del motor
            
        Returns:
            Lista de objetos Conflicto (ORM) recién creados.
        """
        # 1. WIPE: Eliminar conflictos previos (BIDIRECCIONAL)
        db.query(Conflicto).filter(
            or_(
                Conflicto.sesion_id == sesion_id,
                Conflicto.sesion_2_id == sesion_id
            )
        ).delete(synchronize_session='fetch')

        conflictos_orm = []

        # 2. REPLACE: Mapear DTO -> ORM
        for res in resultados_engine:
            nuevo_conflicto = Conflicto(
                tipo=res.tipo,
                severidad=res.severidad,
                estado=EstadoConflicto.POR_REVISAR,
                descripcion=res.descripcion,
                hash_deteccion=res.hash_deteccion,
                
                # Relaciones
                sesion_id=res.sesion_id,
                sesion_2_id=res.sesion_2_id,
                profesor_id=res.profesor_id,
                aula_id=res.aula_id,
                restriccion_id=res.restriccion_id
            )
            conflictos_orm.append(nuevo_conflicto)

        # 3. Persistir (sin commit)
        if conflictos_orm:
            db.add_all(conflictos_orm)
            # db.flush() se hace en el servicio para evitar locks aquí
            
        return conflictos_orm

    def delete_by_sesion_fisico(self, db: Session, sesion_id: int):
        """Elimina físicamente todos los conflictos relacionados con una sesión."""
        db.query(Conflicto).filter(
            or_(
                Conflicto.sesion_id == sesion_id,
                Conflicto.sesion_2_id == sesion_id
            )
        ).delete(synchronize_session='fetch')
        db.flush()


# Instancia singleton
conflictos_repository = ConflictosRepository()