"""
Repositorio para operaciones de base de datos de Sesion.

Responsabilidades:
- Acceso directo a la tabla sesiones
- Queries básicas (CRUD)
- Búsquedas y filtros (por grupo, aula, profesor, modalidad, recurrencia)
- NO contiene lógica de detección de conflictos (va en motor de conflictos)
- Retorna modelos SQLAlchemy (Sesion)

Métodos:
- get_by_id: Obtener sesión por ID
- get_multi: Listar con filtros y paginación
- get_by_grupo_docente: Todas las sesiones de un grupo
- get_by_aula: Todas las sesiones en un aula
- get_by_profesor: Todas las sesiones de un profesor
- get_by_fecha_range: Sesiones puntuales en un rango de fechas
- create: Crear nueva sesión
- update: Actualizar sesión existente
- delete: Eliminar sesión (DELETE físico)
- add_profesor: Asignar profesor a sesión
- remove_profesor: Desasignar profesor de sesión
- update_profesores: Reemplazar lista completa de profesores
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, time

from database.models import Sesion, Profesor, ProfesorSesion
from backend.modules.docencia.schemas.sesion import SesionCreate, SesionUpdate
from backend.constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana


class SesionRepository:
    """
    Repositorio para operaciones de base de datos de Sesion.
    
    Patrón Repository: Encapsula el acceso a datos y queries complejas.
    """
    
    def get_by_id(self, db: Session, id: int) -> Optional[Sesion]:
        """
        Obtener sesión por ID con profesores cargados (eager loading).
        
        Args:
            db: Sesión de base de datos
            id: ID único de la sesión
            
        Returns:
            Sesion si existe, None si no
        """
        return db.query(Sesion)\
            .options(joinedload(Sesion.profesores))\
            .filter(Sesion.id == id)\
            .first()
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        grupo_docente_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        modalidad: Optional[ModalidadSesion] = None,
        tipo_recurrencia: Optional[TipoRecurrencia] = None,
        dia_semana: Optional[DiaSemana] = None
    ) -> Tuple[List[Sesion], int]:
        """
        Listar sesiones con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros a retornar
            grupo_docente_id: Filtrar por grupo docente específico
            aula_id: Filtrar por aula específica
            modalidad: Filtrar por modalidad (PRESENCIAL, ONLINE, HIBRIDA)
            tipo_recurrencia: Filtrar por tipo de recurrencia
            dia_semana: Filtrar por día de la semana (solo para recurrentes)
            
        Returns:
            Tupla (lista_sesiones, total_sin_paginar)
        """
        # Query base con eager loading de profesores
        query = db.query(Sesion).options(joinedload(Sesion.profesores))
        
        # Aplicar filtros
        if grupo_docente_id is not None:
            query = query.filter(Sesion.grupo_docente_id == grupo_docente_id)
        
        if aula_id is not None:
            query = query.filter(Sesion.aula_id == aula_id)
        
        if modalidad is not None:
            query = query.filter(Sesion.modalidad == modalidad)
        
        if tipo_recurrencia is not None:
            query = query.filter(Sesion.tipo_recurrencia == tipo_recurrencia)
        
        if dia_semana is not None:
            query = query.filter(Sesion.dia_semana == dia_semana)
        
        # Contar total ANTES de paginar
        total = query.count()
        
        # Ordenar por tipo_recurrencia, luego por dia_semana/inicio
        query = query.order_by(
            Sesion.tipo_recurrencia,
            Sesion.dia_semana,
            Sesion.hora_inicio,
            Sesion.inicio
        )
        
        # Aplicar paginación
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    
    def get_by_grupo_docente(
        self,
        db: Session,
        grupo_docente_id: int
    ) -> List[Sesion]:
        """
        Obtener todas las sesiones de un grupo docente.
        
        Args:
            db: Sesión de base de datos
            grupo_docente_id: ID del grupo docente
            
        Returns:
            Lista de sesiones del grupo
        """
        return db.query(Sesion)\
            .options(joinedload(Sesion.profesores))\
            .filter(Sesion.grupo_docente_id == grupo_docente_id)\
            .order_by(Sesion.dia_semana, Sesion.hora_inicio)\
            .all()
    
    
    def get_by_aula(
        self,
        db: Session,
        aula_id: int
    ) -> List[Sesion]:
        """
        Obtener todas las sesiones programadas en un aula.
        
        Args:
            db: Sesión de base de datos
            aula_id: ID del aula
            
        Returns:
            Lista de sesiones en el aula
        """
        return db.query(Sesion)\
            .options(joinedload(Sesion.profesores))\
            .filter(Sesion.aula_id == aula_id)\
            .order_by(Sesion.dia_semana, Sesion.hora_inicio)\
            .all()
    
    
    def get_by_profesor(
        self,
        db: Session,
        profesor_id: int
    ) -> List[Sesion]:
        """
        Obtener todas las sesiones donde un profesor está asignado.
        
        Args:
            db: Sesión de base de datos
            profesor_id: ID del profesor
            
        Returns:
            Lista de sesiones del profesor
        """
        return db.query(Sesion)\
            .join(ProfesorSesion)\
            .options(joinedload(Sesion.profesores))\
            .filter(ProfesorSesion.profesor_id == profesor_id)\
            .order_by(Sesion.dia_semana, Sesion.hora_inicio)\
            .all()
    
    
    def get_by_fecha_range(
        self,
        db: Session,
        inicio: datetime,
        fin: datetime
    ) -> List[Sesion]:
        """
        Obtener sesiones puntuales en un rango de fechas.
        
        Args:
            db: Sesión de base de datos
            inicio: Fecha/hora de inicio del rango
            fin: Fecha/hora de fin del rango
            
        Returns:
            Lista de sesiones puntuales en el rango
        """
        return db.query(Sesion)\
            .options(joinedload(Sesion.profesores))\
            .filter(
                Sesion.tipo_recurrencia == TipoRecurrencia.PUNTUAL,
                Sesion.inicio >= inicio,
                Sesion.fin <= fin
            )\
            .order_by(Sesion.inicio)\
            .all()
    
    
    def create(self, db: Session, obj_in: SesionCreate) -> Sesion:
        """
        Crear nueva sesión (sin profesores, se añaden después).
        
        Args:
            db: Sesión de base de datos
            obj_in: Datos de la sesión a crear (SesionCreate schema)
            
        Returns:
            Sesion creada con ID asignado
            
        Nota:
            - No valida FK ni conflictos (debe hacerse en service layer)
            - No asigna profesores aquí (usar add_profesor o update_profesores)
            - Commit se hace en el service
        """
        # Convertir schema Pydantic a dict (excluir profesores)
        sesion_data = obj_in.model_dump(exclude={'profesores'})
        
        # Crear instancia del modelo
        db_sesion = Sesion(**sesion_data)
        
        # Añadir a sesión
        db.add(db_sesion)
        db.flush()  # Asignar ID sin hacer commit
        db.refresh(db_sesion)
        
        return db_sesion
    
    
    def update(
        self,
        db: Session,
        db_obj: Sesion,
        obj_in: SesionUpdate
    ) -> Sesion:
        """
        Actualizar sesión existente.
        
        Args:
            db: Sesión de base de datos
            db_obj: Sesion existente de la DB
            obj_in: Datos a actualizar (SesionUpdate schema)
            
        Returns:
            Sesion actualizada
            
        Nota:
            - Solo actualiza campos proporcionados (exclude_unset=True)
            - No actualiza profesores aquí (usar update_profesores)
            - No valida FK ni conflictos (debe hacerse en service layer)
        """
        # Obtener datos a actualizar (solo campos proporcionados, excluir profesores)
        update_data = obj_in.model_dump(exclude_unset=True, exclude={'profesores'})
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.flush()
        db.refresh(db_obj)
        
        return db_obj
    
    
    def delete(self, db: Session, id: int) -> Optional[Sesion]:
        """
        Eliminar sesión (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene campo 'activo', por lo que
        se hace DELETE físico de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID de la sesión a eliminar
            
        Returns:
            Sesion eliminada si existía, None si no
        """
        sesion = self.get_by_id(db, id)
        
        if sesion:
            db.delete(sesion)
            db.flush()
        
        return sesion
    
    
    # ============================================================
    #  MÉTODOS PARA GESTIÓN DE PROFESORES (Relación M:N)
    # ============================================================
    
    def add_profesor(
        self,
        db: Session,
        sesion_id: int,
        profesor_id: int,
        rol_en_sesion: Optional[str] = None
    ) -> ProfesorSesion:
        """
        Asignar un profesor a una sesión.
        
        Args:
            db: Sesión de base de datos
            sesion_id: ID de la sesión
            profesor_id: ID del profesor a asignar
            rol_en_sesion: Rol del profesor en la sesión (opcional)
            
        Returns:
            ProfesorSesion creada
            
        Nota:
            - No valida que sesion_id y profesor_id existan (debe hacerse en service)
            - Si la relación ya existe, puede lanzar IntegrityError
        """
        profesor_sesion = ProfesorSesion(
            sesion_id=sesion_id,
            profesor_id=profesor_id,
            rol_en_sesion=rol_en_sesion
        )
        
        db.add(profesor_sesion)
        db.flush()
        
        return profesor_sesion
    
    
    def remove_profesor(
        self,
        db: Session,
        sesion_id: int,
        profesor_id: int
    ) -> bool:
        """
        Desasignar un profesor de una sesión.
        
        Args:
            db: Sesión de base de datos
            sesion_id: ID de la sesión
            profesor_id: ID del profesor a desasignar
            
        Returns:
            True si se eliminó, False si no existía
        """
        result = db.query(ProfesorSesion)\
            .filter(
                ProfesorSesion.sesion_id == sesion_id,
                ProfesorSesion.profesor_id == profesor_id
            )\
            .delete()
        
        db.flush()
        
        return result > 0
    
    
    def update_profesores(
        self,
        db: Session,
        sesion_id: int,
        profesores: List[dict]
    ) -> None:
        """
        Reemplazar la lista completa de profesores de una sesión.
        
        Args:
            db: Sesión de base de datos
            sesion_id: ID de la sesión
            profesores: Lista de dicts con profesor_id y rol_en_sesion
                Ejemplo: [
                    {"profesor_id": 10, "rol_en_sesion": "Docente"},
                    {"profesor_id": 20, "rol_en_sesion": "Ayudante"}
                ]
        
        Nota:
            - Elimina todas las asignaciones actuales
            - Crea las nuevas asignaciones
            - No valida que los profesor_id existan (debe hacerse en service)
        """
        # Eliminar todas las asignaciones actuales
        db.query(ProfesorSesion)\
            .filter(ProfesorSesion.sesion_id == sesion_id)\
            .delete()
        
        # Crear nuevas asignaciones
        for prof in profesores:
            self.add_profesor(
                db,
                sesion_id=sesion_id,
                profesor_id=prof['profesor_id'],
                rol_en_sesion=prof.get('rol_en_sesion')
            )
        
        db.flush()
    
    
    def get_profesores_by_sesion(
        self,
        db: Session,
        sesion_id: int
    ) -> List[ProfesorSesion]:
        """
        Obtener todas las asignaciones profesor-sesion de una sesión.
        
        Args:
            db: Sesión de base de datos
            sesion_id: ID de la sesión
            
        Returns:
            Lista de ProfesorSesion con datos del profesor cargados
        """
        return db.query(ProfesorSesion)\
            .options(joinedload(ProfesorSesion.profesor))\
            .filter(ProfesorSesion.sesion_id == sesion_id)\
            .all()


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

sesion_repository = SesionRepository()
"""
Instancia singleton del repositorio de Sesion.

Uso:
    from backend.modules.docencia.repositories.sesion_repo import sesion_repository
    
    sesion = sesion_repository.get_by_id(db, 1)
"""