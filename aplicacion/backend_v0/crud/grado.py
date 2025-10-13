from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.grado import Grado
from schemas.grado import GradoCreate, GradoUpdate
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

def create_grado(db: Session, grado: GradoCreate) -> Tuple[Grado | None, str | None]:
    """
    Crea un nuevo grado con validación de unicidad del nombre.
    Retorna (grado_creado, mensaje_error)
    """
    try:
        # Evitar duplicados por nombre
        existente = db.query(Grado).filter(Grado.nombre == grado.nombre.title()).first()
        if existente:
            return None, f"Ya existe un grado con el nombre '{grado.nombre}'"
        
        nuevo_grado = Grado(**grado.model_dump())
        db.add(nuevo_grado)
        db.commit()
        db.refresh(nuevo_grado)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Grado creado - ID: {nuevo_grado.id}, Nombre: {nuevo_grado.nombre}")
        else:
            logger.info(f"Nuevo grado creado - ID: {nuevo_grado.id}")
        
        return nuevo_grado, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_grados(db: Session, skip: int = 0, limit: int = 100) -> list[Grado]:
    """Obtiene grados con paginación"""
    try:
        return db.query(Grado).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener grados: {e}")
        else:
            logger.error("Error al obtener grados")
        return []

def get_grado_by_id(db: Session, grado_id: int) -> Grado | None:
    """Obtiene un grado por ID"""
    try:
        return db.query(Grado).filter(Grado.id == grado_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener grado {grado_id}: {e}")
        else:
            logger.error("Error al obtener grado")
        return None

def get_grado_by_nombre(db: Session, nombre: str) -> Grado | None:
    """Obtiene un grado por nombre"""
    try:
        return db.query(Grado).filter(Grado.nombre == nombre.title()).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener grado por nombre '{nombre}': {e}")
        else:
            logger.error("Error al obtener grado por nombre")
        return None

def update_grado(db: Session, grado_id: int, datos: GradoUpdate) -> Tuple[Grado | None, str | None]:
    """
    Actualiza un grado existente.
    Retorna (grado_actualizado, mensaje_error)
    """
    try:
        db_grado = get_grado_by_id(db, grado_id)
        if not db_grado:
            return None, "Grado no encontrado"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar unicidad del nombre si se está actualizando
        if 'nombre' in update_data:
            existente = db.query(Grado).filter(
                Grado.nombre == update_data['nombre'].title(),
                Grado.id != grado_id
            ).first()
            if existente:
                return None, f"Ya existe otro grado con el nombre '{update_data['nombre']}'"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_grado, key, value)
        
        db.commit()
        db.refresh(db_grado)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Grado actualizado - ID: {grado_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Grado actualizado - ID: {grado_id}")
        
        return db_grado, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar grado"
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
        error_msg = "Error inesperado al actualizar grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_grado(db: Session, grado_id: int) -> Tuple[bool, str | None]:
    """
    Elimina un grado de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_grado = get_grado_by_id(db, grado_id)
        if not db_grado:
            return False, "Grado no encontrado"
        
        db.delete(db_grado)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Grado eliminado - ID: {grado_id}")
        else:
            logger.info(f"Grado eliminado - ID: {grado_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar grado - Puede tener dependencias"
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
        error_msg = "Error inesperado al eliminar grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"
