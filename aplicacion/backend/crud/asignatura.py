from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_
from models.asignatura import Asignatura, AsignaturaGrado, AsignaturaMencion
from models.grado import Grado
from models.mencion import Mencion
from schemas.asignatura import (
    AsignaturaCreate,
    AsignaturaUpdate,
    AsignaturaGradoCreate,
    AsignaturaMencionCreate
)
import logging
from typing import Optional, Tuple
from config import settings

logger = logging.getLogger(__name__)

# ---------- ASIGNATURA ----------

def create_asignatura(db: Session, asignatura: AsignaturaCreate) -> Tuple[Asignatura | None, str | None]:
    """
    Crea una nueva asignatura con validaciones básicas de integridad.
    Retorna (asignatura_creada, mensaje_error)
    """
    try:
        nueva = Asignatura(**asignatura.model_dump())
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Asignatura creada - ID: {nueva.id}, Nombre: {nueva.nombre}")
        else:
            logger.info(f"Nueva asignatura creada - ID: {nueva.id}")
        
        return nueva, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al crear asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def get_asignaturas(db: Session, skip: int = 0, limit: int = 100) -> list[Asignatura]:
    """Obtiene asignaturas con paginación"""
    try:
        return db.query(Asignatura).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener asignaturas: {e}")
        else:
            logger.error("Error al obtener asignaturas")
        return []

def get_asignatura_by_id(db: Session, asignatura_id: int) -> Asignatura | None:
    """Obtiene una asignatura por ID"""
    try:
        return db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener asignatura {asignatura_id}: {e}")
        else:
            logger.error("Error al obtener asignatura")
        return None

def update_asignatura(db: Session, asignatura_id: int, datos: AsignaturaUpdate) -> Tuple[Asignatura | None, str | None]:
    """
    Actualiza una asignatura existente.
    Retorna (asignatura_actualizada, mensaje_error)
    """
    try:
        db_asig = get_asignatura_by_id(db, asignatura_id)
        if not db_asig:
            return None, "Asignatura no encontrada"
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_asig, key, value)
        
        db.commit()
        db.refresh(db_asig)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Asignatura actualizada - ID: {asignatura_id}, Campos: {list(update_data.keys())}")
        else:
            logger.info(f"Asignatura actualizada - ID: {asignatura_id}")
        
        return db_asig, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar asignatura"
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
        error_msg = "Error inesperado al actualizar asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_asignatura(db: Session, asignatura_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una asignatura de la base de datos.
    Retorna (exito, mensaje_error)
    """
    try:
        db_asig = get_asignatura_by_id(db, asignatura_id)
        if not db_asig:
            return False, "Asignatura no encontrada"
        
        db.delete(db_asig)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Asignatura eliminada - ID: {asignatura_id}")
        else:
            logger.info(f"Asignatura eliminada - ID: {asignatura_id}")
        
        return True, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al eliminar asignatura - Puede tener dependencias"
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
        error_msg = "Error inesperado al eliminar asignatura"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return False, "Error interno del servidor"

# ---------- ASIGNATURA-GRADO ----------

def _validate_asignatura_grado_entities(db: Session, data: AsignaturaGradoCreate) -> Tuple[bool, str]:
    """Valida que asignatura y grado existan"""
    if not db.query(Asignatura).filter(Asignatura.id == data.asignatura_id).first():
        return False, f"No existe asignatura con ID {data.asignatura_id}"
    
    if not db.query(Grado).filter(Grado.id == data.grado_id).first():
        return False, f"No existe grado con ID {data.grado_id}"
    
    return True, ""

def create_asignatura_grado(db: Session, data: AsignaturaGradoCreate) -> Tuple[AsignaturaGrado | None, str | None]:
    """
    Crea una relación asignatura-grado con validaciones de integridad.
    Retorna (relacion_creada, mensaje_error)
    """
    try:
        # Validar que no exista ya la relación
        exists = db.query(AsignaturaGrado).filter_by(
            asignatura_id=data.asignatura_id,
            grado_id=data.grado_id
        ).first()
        if exists:
            return None, "La relación asignatura-grado ya existe"
        
        # Validar integridad referencial
        entities_valid, entities_error = _validate_asignatura_grado_entities(db, data)
        if not entities_valid:
            return None, entities_error

        rel = AsignaturaGrado(**data.model_dump())
        db.add(rel)
        db.commit()
        db.refresh(rel)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación asignatura-grado creada - ID: {rel.id}")
        else:
            logger.info(f"Nueva relación asignatura-grado creada")
        
        return rel, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear relación asignatura-grado"
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
        error_msg = "Error inesperado al crear relación asignatura-grado"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_asignatura_grado(db: Session, rel_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una relación asignatura-grado.
    Retorna (exito, mensaje_error)
    """
    try:
        rel = db.query(AsignaturaGrado).filter(AsignaturaGrado.id == rel_id).first()
        if not rel:
            return False, "Relación no encontrada"
        
        db.delete(rel)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación asignatura-grado eliminada - ID: {rel_id}")
        else:
            logger.info("Relación asignatura-grado eliminada")
        
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

def get_asignaturas_by_grado_id(db: Session, grado_id: int) -> list[Asignatura]:
    """Obtiene todas las asignaturas de un grado específico"""
    try:
        return db.query(Asignatura)\
            .join(AsignaturaGrado)\
            .filter(AsignaturaGrado.grado_id == grado_id)\
            .all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener asignaturas del grado {grado_id}: {e}")
        else:
            logger.error("Error al obtener asignaturas por grado")
        return []

# ---------- ASIGNATURA-MENCION ----------

def _validate_asignatura_mencion_entities(db: Session, data: AsignaturaMencionCreate) -> Tuple[bool, str]:
    """Valida que asignatura y mención existan"""
    if not db.query(Asignatura).filter(Asignatura.id == data.asignatura_id).first():
        return False, f"No existe asignatura con ID {data.asignatura_id}"
    
    if not db.query(Mencion).filter(Mencion.id == data.mencion_id).first():
        return False, f"No existe mención con ID {data.mencion_id}"
    
    return True, ""

def create_asignatura_mencion(db: Session, data: AsignaturaMencionCreate) -> Tuple[AsignaturaMencion | None, str | None]:
    """
    Crea una relación asignatura-mención con validaciones de integridad.
    Retorna (relacion_creada, mensaje_error)
    """
    try:
        # Validar que no exista ya la relación
        exists = db.query(AsignaturaMencion).filter_by(
            asignatura_id=data.asignatura_id,
            mencion_id=data.mencion_id
        ).first()
        if exists:
            return None, "La relación asignatura-mención ya existe"
        
        # Validar integridad referencial
        entities_valid, entities_error = _validate_asignatura_mencion_entities(db, data)
        if not entities_valid:
            return None, entities_error

        rel = AsignaturaMencion(**data.model_dump())
        db.add(rel)
        db.commit()
        db.refresh(rel)
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación asignatura-mención creada - ID: {rel.id}")
        else:
            logger.info(f"Nueva relación asignatura-mención creada")
        
        return rel, None
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al crear relación asignatura-mención"
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
        error_msg = "Error inesperado al crear relación asignatura-mención"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return None, "Error interno del servidor"

def delete_asignatura_mencion(db: Session, rel_id: int) -> Tuple[bool, str | None]:
    """
    Elimina una relación asignatura-mención.
    Retorna (exito, mensaje_error)
    """
    try:
        rel = db.query(AsignaturaMencion).filter(AsignaturaMencion.id == rel_id).first()
        if not rel:
            return False, "Relación no encontrada"
        
        db.delete(rel)
        db.commit()
        
        # Logging
        if settings.DEBUG:
            logger.info(f"Relación asignatura-mención eliminada - ID: {rel_id}")
        else:
            logger.info("Relación asignatura-mención eliminada")
        
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

def get_asignaturas_by_mencion_id(db: Session, mencion_id: int) -> list[Asignatura]:
    """Obtiene todas las asignaturas de una mención específica"""
    try:
        return db.query(Asignatura)\
            .join(AsignaturaMencion)\
            .filter(AsignaturaMencion.mencion_id == mencion_id)\
            .all()
    except SQLAlchemyError as e:
        if settings.DEBUG:
            logger.error(f"Error al obtener asignaturas de la mención {mencion_id}: {e}")
        else:
            logger.error("Error al obtener asignaturas por mención")
        return []
