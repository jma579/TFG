from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_
from models.sesion import Sesion
from models.asignatura import Asignatura
from models.profesor import Profesor
from models.aula import Aula
from schemas.sesion import SesionCreate, SesionUpdate
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

def _validate_sesion_entities(db: Session, sesion: SesionCreate) -> Tuple[bool, str]:
    """
    Valida que todas las entidades relacionadas existan (integridad referencial).
    Retorna (es_valido, mensaje_error)
    """
    # Validar asignatura existe
    if not db.query(Asignatura).filter(Asignatura.id == sesion.asignatura_id).first():
        return False, f"No existe asignatura con ID {sesion.asignatura_id}"
    
    # Validar profesor existe
    if not db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first():
        return False, f"No existe profesor con ID {sesion.profesor_id}"
    
    # Validar aula existe
    if not db.query(Aula).filter(Aula.id == sesion.aula_id).first():
        return False, f"No existe aula con ID {sesion.aula_id}"
    
    return True, ""

def create_sesion(db: Session, sesion: SesionCreate) -> Tuple[Sesion | None, str | None]:
    """
    Crea una nueva sesión con validaciones básicas de integridad referencial.
    Retorna (sesion_creada, mensaje_error)
    
    Nota: Las validaciones de lógica de negocio (conflictos de horarios, etc.)
    deben realizarse en la capa de servicios antes de llamar a esta función.
    """
    try:
        # Validar integridad referencial
        entities_valid, entities_error = _validate_sesion_entities(db, sesion)
        if not entities_valid:
            return None, entities_error
        
        # Crear la sesión
        nueva_sesion = Sesion(**sesion.model_dump())
        db.add(nueva_sesion)
        db.commit()
        db.refresh(nueva_sesion)
        
        # Logging según entorno
        if settings.DEBUG:
            logger.info(
                f"Sesión creada - ID: {nueva_sesion.id}, "
                f"Asignatura: {sesion.asignatura_id}, Profesor: {sesion.profesor_id}, "
                f"Aula: {sesion.aula_id}, Día: {sesion.dia}"
            )
        else:
            logger.info(f"Nueva sesión creada - ID: {nueva_sesion.id}")
        
        return nueva_sesion, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad en la base de datos"
        if settings.DEBUG:
            logger.error(f"{error_msg} al crear sesión: {e}")
        else:
            logger.error(f"{error_msg} al crear sesión")
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos"
        if settings.DEBUG:
            logger.error(f"{error_msg} al crear sesión: {e}")
        else:
            logger.error(f"{error_msg} al crear sesión")
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_sesiones(db: Session, skip: int = 0, limit: int = 100) -> list[Sesion]:
    """Obtiene sesiones con paginación"""
    try:
        return db.query(Sesion).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener sesiones: {e}")
        else:
            logger.error("Error al obtener sesiones")
        return []

def get_sesiones_with_relations(db: Session, skip: int = 0, limit: int = 100) -> list[Sesion]:
    """Obtiene sesiones con sus relaciones cargadas (eager loading)"""
    try:
        return db.query(Sesion)\
            .options(
                joinedload(Sesion.asignatura),
                joinedload(Sesion.profesor),
                joinedload(Sesion.aula)
            )\
            .offset(skip)\
            .limit(limit)\
            .all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener sesiones con relaciones: {e}")
        else:
            logger.error("Error al obtener sesiones")
        return []

def get_sesion_by_id(db: Session, sesion_id: int) -> Sesion | None:
    """Obtiene una sesión por ID"""
    try:
        return db.query(Sesion).filter(Sesion.id == sesion_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener sesión {sesion_id}: {e}")
        else:
            logger.error(f"Error al obtener sesión")
        return None

def get_sesion_by_id_with_relations(db: Session, sesion_id: int) -> Sesion | None:
    """Obtiene una sesión por ID con todas sus relaciones"""
    try:
        return db.query(Sesion)\
            .options(
                joinedload(Sesion.asignatura),
                joinedload(Sesion.profesor),
                joinedload(Sesion.aula)
            )\
            .filter(Sesion.id == sesion_id)\
            .first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener sesión {sesion_id} con relaciones: {e}")
        else:
            logger.error("Error al obtener sesión")
        return None

def update_sesion(db: Session, sesion_id: int, datos: SesionUpdate) -> Tuple[Sesion | None, str | None]:
    """
    Actualiza una sesión existente con validaciones básicas de integridad.
    Retorna (sesion_actualizada, mensaje_error)
    
    Nota: Las validaciones de lógica de negocio deben realizarse
    en la capa de servicios antes de llamar a esta función.
    """
    try:
        db_sesion = get_sesion_by_id(db, sesion_id)
        if not db_sesion:
            return None, "Sesión no encontrada"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar integridad referencial para campos modificados
        if 'asignatura_id' in update_data:
            if not db.query(Asignatura).filter(Asignatura.id == update_data['asignatura_id']).first():
                return None, f"No existe asignatura con ID {update_data['asignatura_id']}"
        
        if 'profesor_id' in update_data:
            if not db.query(Profesor).filter(Profesor.id == update_data['profesor_id']).first():
                return None, f"No existe profesor con ID {update_data['profesor_id']}"
        
        if 'aula_id' in update_data:
            if not db.query(Aula).filter(Aula.id == update_data['aula_id']).first():
                return None, f"No existe aula con ID {update_data['aula_id']}"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_sesion, key, value)
        
        db.commit()
        db.refresh(db_sesion)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Sesión actualizada - ID: {sesion_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Sesión actualizada - ID: {sesion_id}")
        
        return db_sesion, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al actualizar"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al actualizar sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_sesion(db: Session, sesion_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una sesión de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_sesion = get_sesion_by_id(db, sesion_id)
        if not db_sesion:
            return False, "Sesión no encontrada"
        
        db.delete(db_sesion)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Sesión eliminada - ID: {sesion_id}")
        else:
            logger.info(f"Sesión eliminada - ID: {sesion_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar sesión - Puede tener dependencias"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al eliminar"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al eliminar sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

def get_sesiones_by_profesor(db: Session, profesor_id: int) -> list[Sesion]:
    return db.query(Sesion).filter(Sesion.profesor_id == profesor_id).all()

def get_sesiones_by_asignatura(db: Session, asignatura_id: int) -> list[Sesion]:
    return db.query(Sesion).filter(Sesion.asignatura_id == asignatura_id).all()

def get_sesiones_by_aula(db: Session, aula_id: int) -> list[Sesion]:
    return db.query(Sesion).filter(Sesion.aula_id == aula_id).all()
