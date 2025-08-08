from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.aula import Aula
from schemas.aula import AulaCreate, AulaUpdate
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

def create_aula(db: Session, aula: AulaCreate) -> Tuple[Aula | None, str | None]:
    """
    Crea una nueva aula con validación de unicidad del nombre.
    Retorna (aula_creada, mensaje_error)
    """
    try:
        # Verificar si ya existe una aula con el mismo nombre
        existente = db.query(Aula).filter_by(nombre=aula.nombre.upper()).first()
        if existente:
            return None, f"Ya existe un aula con el nombre '{aula.nombre}'"
        
        nueva_aula = Aula(**aula.model_dump())
        db.add(nueva_aula)
        db.commit()
        db.refresh(nueva_aula)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Aula creada - ID: {nueva_aula.id}, Nombre: {nueva_aula.nombre}")
        else:
            logger.info(f"Nueva aula creada - ID: {nueva_aula.id}")
        
        return nueva_aula, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear aula"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear aula"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear aula"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_aulas(db: Session, skip: int = 0, limit: int = 100) -> list[Aula]:
    """Obtiene aulas con paginación"""
    try:
        return db.query(Aula).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener aulas: {e}")
        else:
            logger.error("Error al obtener aulas")
        return []

def get_aula_by_id(db: Session, aula_id: int) -> Aula | None:
    """Obtiene un aula por ID"""
    try:
        return db.query(Aula).filter(Aula.id == aula_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener aula {aula_id}: {e}")
        else:
            logger.error("Error al obtener aula")
        return None

def update_aula(db: Session, aula_id: int, datos: AulaUpdate) -> Tuple[Aula | None, str | None]:
    """
    Actualiza un aula existente.
    Retorna (aula_actualizada, mensaje_error)
    """
    try:
        db_aula = get_aula_by_id(db, aula_id)
        if not db_aula:
            return None, "Aula no encontrada"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Validar unicidad del nombre si se está actualizando
        if 'nombre' in update_data:
            existente = db.query(Aula).filter(
                Aula.nombre == update_data['nombre'].upper(),
                Aula.id != aula_id
            ).first()
            if existente:
                return None, f"Ya existe otra aula con el nombre '{update_data['nombre']}'"
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_aula, key, value)
        
        db.commit()
        db.refresh(db_aula)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Aula actualizada - ID: {aula_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Aula actualizada - ID: {aula_id}")
        
        return db_aula, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar aula"
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
        error_msg = "Error inesperado al actualizar aula"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_aula(db: Session, aula_id: int) -> Tuple[bool, str | None]:
    """
    Elimina un aula de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_aula = get_aula_by_id(db, aula_id)
        if not db_aula:
            return False, "Aula no encontrada"
        
        db.delete(db_aula)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Aula eliminada - ID: {aula_id}")
        else:
            logger.info(f"Aula eliminada - ID: {aula_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar aula - Puede tener dependencias"
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
        error_msg = "Error inesperado al eliminar aula"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

def get_aulas_by_tipo(db: Session, tipo: str) -> list[Aula]:
    """Obtiene todas las aulas de un tipo específico"""
    try:
        return db.query(Aula).filter(Aula.tipo == tipo).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener aulas del tipo '{tipo}': {e}")
        else:
            logger.error("Error al obtener aulas por tipo")
        return []
