from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.profesor import Profesor, ProfesorAsignatura
from models.asignatura import Asignatura
from schemas.profesor import (
    ProfesorCreate, ProfesorUpdate,
    ProfesorAsignaturaCreate, ProfesorAsignaturaUpdate
)
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

# ---------- PROFESOR ----------

def create_profesor(db: Session, profesor: ProfesorCreate) -> Tuple[Profesor | None, str | None]:
    """
    Crea un nuevo profesor con validación de unicidad del nombre.
    Retorna (profesor_creado, mensaje_error)
    """
    try:
        # Verificar que no exista ya un profesor con el mismo nombre
        existente = db.query(Profesor).filter(Profesor.nombre == profesor.nombre.title()).first()
        if existente:
            return None, f"Ya existe un profesor con el nombre '{profesor.nombre}'"
        
        nuevo = Profesor(**profesor.model_dump())
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Profesor creado - ID: {nuevo.id}, Nombre: {nuevo.nombre}")
        else:
            logger.info(f"Nuevo profesor creado - ID: {nuevo.id}")
        
        return nuevo, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear profesor"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear profesor"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear profesor"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_profesores(db: Session, skip: int = 0, limit: int = 100) -> list[Profesor]:
    """Obtiene profesores con paginación"""
    try:
        return db.query(Profesor).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener profesores: {e}")
        else:
            logger.error("Error al obtener profesores")
        return []

def get_profesor_by_id(db: Session, profesor_id: int) -> Profesor | None:
    """Obtiene un profesor por ID"""
    try:
        return db.query(Profesor).filter(Profesor.id == profesor_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener profesor {profesor_id}: {e}")
        else:
            logger.error("Error al obtener profesor")
        return None

def update_profesor(db: Session, profesor_id: int, datos: ProfesorUpdate) -> Tuple[Profesor | None, str | None]:
    """
    Actualiza un profesor existente.
    Retorna (profesor_actualizado, mensaje_error)
    """
    try:
        db_prof = get_profesor_by_id(db, profesor_id)
        if not db_prof:
            return None, "Profesor no encontrado"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar unicidad del nombre si se está actualizando
        if 'nombre' in update_data:
            existente = db.query(Profesor).filter(
                Profesor.nombre == update_data['nombre'].title(),
                Profesor.id != profesor_id
            ).first()
            if existente:
                return None, f"Ya existe otro profesor con el nombre '{update_data['nombre']}'"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_prof, key, value)
        
        db.commit()
        db.refresh(db_prof)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Profesor actualizado - ID: {profesor_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Profesor actualizado - ID: {profesor_id}")
        
        return db_prof, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar profesor"
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
        error_msg = "Error inesperado al actualizar profesor"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_profesor(db: Session, profesor_id: int) -> Tuple[bool, str | None]:
    """
    Elimina un profesor de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_prof = get_profesor_by_id(db, profesor_id)
        if not db_prof:
            return False, "Profesor no encontrado"
        
        db.delete(db_prof)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Profesor eliminado - ID: {profesor_id}")
        else:
            logger.info(f"Profesor eliminado - ID: {profesor_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar profesor - Puede tener dependencias"
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
        error_msg = "Error inesperado al eliminar profesor"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

# ---------- PROFESOR-ASIGNATURA ----------

def _validate_profesor_asignatura_entities(db: Session, rel: ProfesorAsignaturaCreate) -> Tuple[bool, str]:
    """Valida que profesor y asignatura existan"""
    if not db.query(Profesor).filter(Profesor.id == rel.profesor_id).first():
        return False, f"No existe profesor con ID {rel.profesor_id}"
    
    if not db.query(Asignatura).filter(Asignatura.id == rel.asignatura_id).first():
        return False, f"No existe asignatura con ID {rel.asignatura_id}"
    
    return True, ""

def create_profesor_asignatura(db: Session, rel: ProfesorAsignaturaCreate) -> Tuple[ProfesorAsignatura | None, str | None]:
    """
    Crea una relación profesor-asignatura con validaciones de integridad.
    Retorna (relacion_creada, mensaje_error)
    """
    try:
        # Validar que no exista ya la relación
        existe = db.query(ProfesorAsignatura).filter_by(
            profesor_id=rel.profesor_id,
            asignatura_id=rel.asignatura_id
        ).first()
        if existe:
            return None, "La relación profesor-asignatura ya existe"
        
        # Validar integridad referencial
        entities_valid, entities_error = _validate_profesor_asignatura_entities(db, rel)
        if not entities_valid:
            return None, entities_error

        nueva_rel = ProfesorAsignatura(**rel.model_dump())
        db.add(nueva_rel)
        db.commit()
        db.refresh(nueva_rel)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación profesor-asignatura creada - ID: {nueva_rel.id}")
        else:
            logger.info(f"Nueva relación profesor-asignatura creada")
        
        return nueva_rel, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear relación profesor-asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear relación"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear relación profesor-asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_profesor_asignatura(db: Session, rel_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una relación profesor-asignatura.
    Retorna (exito, mensaje_error)
    """
    try:
        rel = db.query(ProfesorAsignatura).filter(ProfesorAsignatura.id == rel_id).first()
        if not rel:
            return False, "Relación no encontrada"
        
        db.delete(rel)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación profesor-asignatura eliminada - ID: {rel_id}")
        else:
            logger.info("Relación profesor-asignatura eliminada")
        
        return True, None
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al eliminar relación"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al eliminar relación"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

def get_profesores_by_asignatura_id(db: Session, asignatura_id: int) -> list[Profesor]:
    """Obtiene todos los profesores de una asignatura específica"""
    try:
        return db.query(Profesor)\
            .join(ProfesorAsignatura)\
            .filter(ProfesorAsignatura.asignatura_id == asignatura_id)\
            .all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener profesores de la asignatura {asignatura_id}: {e}")
        else:
            logger.error("Error al obtener profesores por asignatura")
        return []
