from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.mencion import Mencion
from models.grado import Grado
from schemas.mencion import MencionCreate, MencionUpdate
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

def _validate_mencion_entities(db: Session, mencion: MencionCreate) -> Tuple[bool, str]:
    """Valida que el grado exista"""
    if not db.query(Grado).filter(Grado.id == mencion.grado_id).first():
        return False, f"No existe grado con ID {mencion.grado_id}"
    return True, ""

def create_mencion(db: Session, mencion: MencionCreate) -> Tuple[Mencion | None, str | None]:
    """
    Crea una nueva mención con validaciones de integridad.
    Retorna (mencion_creada, mensaje_error)
    """
    try:
        # Validar integridad referencial
        entities_valid, entities_error = _validate_mencion_entities(db, mencion)
        if not entities_valid:
            return None, entities_error
        
        # Evitar duplicados por nombre dentro del mismo grado
        existente = db.query(Mencion).filter(
            Mencion.nombre == mencion.nombre.title(),
            Mencion.grado_id == mencion.grado_id
        ).first()
        if existente:
            return None, f"Ya existe una mención con el nombre '{mencion.nombre}' en este grado"
        
        nueva_mencion = Mencion(**mencion.model_dump())
        db.add(nueva_mencion)
        db.commit()
        db.refresh(nueva_mencion)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Mención creada - ID: {nueva_mencion.id}, Nombre: {nueva_mencion.nombre}")
        else:
            logger.info(f"Nueva mención creada - ID: {nueva_mencion.id}")
        
        return nueva_mencion, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_menciones(db: Session, skip: int = 0, limit: int = 100) -> list[Mencion]:
    """Obtiene menciones con paginación"""
    try:
        return db.query(Mencion).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener menciones: {e}")
        else:
            logger.error("Error al obtener menciones")
        return []

def get_mencion_by_id(db: Session, mencion_id: int) -> Mencion | None:
    """Obtiene una mención por ID"""
    try:
        return db.query(Mencion).filter(Mencion.id == mencion_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener mención {mencion_id}: {e}")
        else:
            logger.error("Error al obtener mención")
        return None

def get_menciones_by_grado_id(db: Session, grado_id: int) -> list[Mencion]:
    """Obtiene todas las menciones de un grado específico"""
    try:
        return db.query(Mencion).filter(Mencion.grado_id == grado_id).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener menciones del grado {grado_id}: {e}")
        else:
            logger.error("Error al obtener menciones por grado")
        return []

def update_mencion(db: Session, mencion_id: int, datos: MencionUpdate) -> Tuple[Mencion | None, str | None]:
    """
    Actualiza una mención existente.
    Retorna (mencion_actualizada, mensaje_error)
    """
    try:
        db_mencion = get_mencion_by_id(db, mencion_id)
        if not db_mencion:
            return None, "Mención no encontrada"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar integridad referencial para grado_id si se actualiza
        if 'grado_id' in update_data:
            if not db.query(Grado).filter(Grado.id == update_data['grado_id']).first():
                return None, f"No existe grado con ID {update_data['grado_id']}"
        
        # Validar unicidad de nombre dentro del grado
        if 'nombre' in update_data or 'grado_id' in update_data:
            nuevo_nombre = update_data.get('nombre', db_mencion.nombre)
            nuevo_grado_id = update_data.get('grado_id', db_mencion.grado_id)
            
            existente = db.query(Mencion).filter(
                Mencion.nombre == nuevo_nombre.title(),
                Mencion.grado_id == nuevo_grado_id,
                Mencion.id != mencion_id
            ).first()
            if existente:
                return None, f"Ya existe otra mención con el nombre '{nuevo_nombre}' en este grado"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_mencion, key, value)
        
        db.commit()
        db.refresh(db_mencion)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Mención actualizada - ID: {mencion_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Mención actualizada - ID: {mencion_id}")
        
        return db_mencion, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar mención"
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
        error_msg = "Error inesperado al actualizar mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_mencion(db: Session, mencion_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una mención de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_mencion = get_mencion_by_id(db, mencion_id)
        if not db_mencion:
            return False, "Mención no encontrada"
        
        db.delete(db_mencion)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Mención eliminada - ID: {mencion_id}")
        else:
            logger.info(f"Mención eliminada - ID: {mencion_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar mención - Puede tener dependencias"
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
        error_msg = "Error inesperado al eliminar mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"
