from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_
from models.restriccion import Restriccion
from models.asignatura import Asignatura
from models.profesor import Profesor
from models.aula import Aula
from schemas.restriccion import RestriccionCreate, RestriccionUpdate
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

def _validate_restriccion_entities(db: Session, restriccion: RestriccionCreate) -> Tuple[bool, str]:
    """Valida que las entidades relacionadas existan (si están especificadas)"""
    if restriccion.asignatura_id:
        if not db.query(Asignatura).filter(Asignatura.id == restriccion.asignatura_id).first():
            return False, f"No existe asignatura con ID {restriccion.asignatura_id}"
    
    if restriccion.profesor_id:
        if not db.query(Profesor).filter(Profesor.id == restriccion.profesor_id).first():
            return False, f"No existe profesor con ID {restriccion.profesor_id}"
    
    if restriccion.aula_id:
        if not db.query(Aula).filter(Aula.id == restriccion.aula_id).first():
            return False, f"No existe aula con ID {restriccion.aula_id}"
    
    return True, ""

def create_restriccion(db: Session, restriccion: RestriccionCreate) -> Tuple[Restriccion | None, str | None]:
    """
    Crea una nueva restricción con validaciones de integridad.
    Retorna (restriccion_creada, mensaje_error)
    """
    try:
        # Validar integridad referencial
        entities_valid, entities_error = _validate_restriccion_entities(db, restriccion)
        if not entities_valid:
            return None, entities_error
        
        # Prevenir duplicados por tipo y entidad
        condiciones = [Restriccion.tipo == restriccion.tipo]

        if restriccion.asignatura_id:
            condiciones.append(Restriccion.asignatura_id == restriccion.asignatura_id)
        if restriccion.profesor_id:
            condiciones.append(Restriccion.profesor_id == restriccion.profesor_id)
        if restriccion.aula_id:
            condiciones.append(Restriccion.aula_id == restriccion.aula_id)

        existente = db.query(Restriccion).filter(and_(*condiciones)).first()
        if existente:
            return None, "Ya existe una restricción similar para estas entidades"

        nueva = Restriccion(**restriccion.model_dump())
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Restricción creada - ID: {nueva.id}, Tipo: {nueva.tipo}")
        else:
            logger.info(f"Nueva restricción creada - ID: {nueva.id}")
        
        return nueva, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear restricción"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear restricción"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear restricción"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_restricciones(db: Session, skip: int = 0, limit: int = 100) -> list[Restriccion]:
    """Obtiene restricciones con paginación"""
    try:
        return db.query(Restriccion).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener restricciones: {e}")
        else:
            logger.error("Error al obtener restricciones")
        return []

def get_restriccion_by_id(db: Session, restriccion_id: int) -> Restriccion | None:
    """Obtiene una restricción por ID"""
    try:
        return db.query(Restriccion).filter(Restriccion.id == restriccion_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener restricción {restriccion_id}: {e}")
        else:
            logger.error("Error al obtener restricción")
        return None

def update_restriccion(db: Session, restriccion_id: int, datos: RestriccionUpdate) -> Tuple[Restriccion | None, str | None]:
    """
    Actualiza una restricción existente.
    Retorna (restriccion_actualizada, mensaje_error)
    """
    try:
        db_restriccion = get_restriccion_by_id(db, restriccion_id)
        if not db_restriccion:
            return None, "Restricción no encontrada"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar integridad referencial para campos modificados
        if 'asignatura_id' in update_data and update_data['asignatura_id']:
            if not db.query(Asignatura).filter(Asignatura.id == update_data['asignatura_id']).first():
                return None, f"No existe asignatura con ID {update_data['asignatura_id']}"
        
        if 'profesor_id' in update_data and update_data['profesor_id']:
            if not db.query(Profesor).filter(Profesor.id == update_data['profesor_id']).first():
                return None, f"No existe profesor con ID {update_data['profesor_id']}"
        
        if 'aula_id' in update_data and update_data['aula_id']:
            if not db.query(Aula).filter(Aula.id == update_data['aula_id']).first():
                return None, f"No existe aula con ID {update_data['aula_id']}"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_restriccion, key, value)
        
        db.commit()
        db.refresh(db_restriccion)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Restricción actualizada - ID: {restriccion_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Restricción actualizada - ID: {restriccion_id}")
        
        return db_restriccion, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar restricción"
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
        error_msg = "Error inesperado al actualizar restricción"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_restriccion(db: Session, restriccion_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una restricción de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_restriccion = get_restriccion_by_id(db, restriccion_id)
        if not db_restriccion:
            return False, "Restricción no encontrada"
        
        db.delete(db_restriccion)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Restricción eliminada - ID: {restriccion_id}")
        else:
            logger.info(f"Restricción eliminada - ID: {restriccion_id}")
        
        return True, None
        
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
        error_msg = "Error inesperado al eliminar restricción"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

def get_restricciones_filtradas(
    db: Session,
    tipo: str | None = None,
    activa: bool | None = None,
    prioridad_minima: int | None = None,
    asignatura_id: int | None = None,
    profesor_id: int | None = None,
    aula_id: int | None = None
) -> list[Restriccion]:
    """Obtiene restricciones aplicando filtros específicos"""
    try:
        query = db.query(Restriccion)

        if tipo:
            query = query.filter(Restriccion.tipo == tipo)
        if activa is not None:
            query = query.filter(Restriccion.activa == activa)
        if prioridad_minima:
            query = query.filter(Restriccion.prioridad >= prioridad_minima)
        if asignatura_id:
            query = query.filter(Restriccion.asignatura_id == asignatura_id)
        if profesor_id:
            query = query.filter(Restriccion.profesor_id == profesor_id)
        if aula_id:
            query = query.filter(Restriccion.aula_id == aula_id)

        return query.all()
        
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener restricciones filtradas: {e}")
        else:
            logger.error("Error al obtener restricciones filtradas")
        return []
