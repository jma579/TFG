from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_
from models.sesion import Sesion
from models.asignatura import Asignatura
from models.profesor import Profesor
from models.aula import Aula
from schemas.sesion import SesionCreate, SesionUpdate
import logging
from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass, asdict
from config import settings
from core.deteccion_conflictos import detectar_todos_los_conflictos

logger = logging.getLogger(__name__)


# ========================================
# CLASES DE DATOS
# ========================================

@dataclass
class ResultadoValidacion:
    """Resultado de validación con conflictos detectados (dataclasses serializables)"""
    es_valido: bool
    conflictos: Dict[str, List[Any]]
    total_conflictos: int
    conflictos_criticos: List[Any]
    mensaje: str

@dataclass 
class ResultadoOperacion:
    """Resultado de operación CRUD con información detallada (conflictos serializables)"""
    exitoso: bool
    entidad: Optional[Sesion]
    mensaje: str
    conflictos: Optional[Dict[str, List[Any]]] = None
    total_conflictos: int = 0
    conflictos_criticos: Optional[List[Any]] = None
    forzado: bool = False


# ========================================
# FUNCIONES CRUD PRINCIPALES (CREATE, READ, UPDATE, DELETE)
# ========================================

def create_sesion(db: Session, sesion: SesionCreate, forzar_creacion: bool = False) -> ResultadoOperacion:
    """
    Crea una nueva sesión con validación completa de conflictos.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a crear
        forzar_creacion: Si True, crear aunque haya conflictos críticos
    
    Returns:
        ResultadoOperacion: Resultado estructurado con:
            - exitoso: bool - Si la operación fue exitosa
            - entidad: Sesion | None - La sesión creada (si exitoso)
            - mensaje: str - Mensaje descriptivo del resultado
            - conflictos: Dict[str, List[Any]] | None - Conflictos serializables por categoría
            - total_conflictos: int - Número total de conflictos
            - conflictos_criticos: List[Any] | None - Lista de conflictos críticos serializables
            - forzado: bool - Si la creación fue forzada pese a conflictos críticos
    """
    try:
        # Validación completa (entidades + conflictos)
        resultado_validacion = validar_sesion_completa(db, sesion)
        
        # Si hay conflictos críticos y no forzamos, aborta
        if not resultado_validacion.es_valido and not forzar_creacion:
            logger.warning(f"Creación de sesión bloqueada: {resultado_validacion.mensaje}")
            return ResultadoOperacion(
                exitoso=False,
                entidad=None,
                mensaje=resultado_validacion.mensaje,
                conflictos=serializar_conflictos(resultado_validacion.conflictos),
                total_conflictos=resultado_validacion.total_conflictos,
                conflictos_criticos=[asdict(c) for c in resultado_validacion.conflictos_criticos] if resultado_validacion.conflictos_criticos else None,
                forzado=False
            )
        
        # Crear la sesión en base de datos
        nueva_sesion = Sesion(**sesion.model_dump())
        db.add(nueva_sesion)
        db.commit()
        db.refresh(nueva_sesion)
        
        # Determinar mensaje y logging (solo log warnings si hay conflictos)
        fue_forzada = forzar_creacion and len(resultado_validacion.conflictos_criticos) > 0
        
        if resultado_validacion.total_conflictos > 0:
            if fue_forzada:
                mensaje = f"Sesión creada FORZADAMENTE con {len(resultado_validacion.conflictos_criticos)} conflictos críticos ignorados"
                logger.warning(f"SESIÓN FORZADA ID {nueva_sesion.id}: {len(resultado_validacion.conflictos_criticos)} conflictos críticos ignorados")
            else:
                mensaje = f"Sesión creada con {resultado_validacion.total_conflictos} conflictos no críticos detectados"
                logger.warning(f"Sesión ID {nueva_sesion.id} creada con {resultado_validacion.total_conflictos} conflictos no críticos")
        else:
            mensaje = f"Sesión creada exitosamente sin conflictos (ID: {nueva_sesion.id})"
        
        # Logging detallado en DEBUG
        if settings.DEBUG:
            logger.info(
                f"Sesión creada - ID: {nueva_sesion.id}, "
                f"Asignatura: {sesion.asignatura_id}, Profesor: {sesion.profesor_id}, "
                f"Aula: {sesion.aula_id}, Día: {sesion.dia_semana}, "
                f"Conflictos: {resultado_validacion.total_conflictos}, Forzada: {fue_forzada}"
            )
        else:
            logger.info(f"Nueva sesión creada - ID: {nueva_sesion.id}")
        
        return ResultadoOperacion(
            exitoso=True,
            entidad=nueva_sesion,
            mensaje=mensaje,
            conflictos=serializar_conflictos(resultado_validacion.conflictos) if resultado_validacion.total_conflictos > 0 else None,
            total_conflictos=resultado_validacion.total_conflictos,
            conflictos_criticos=[asdict(c) for c in resultado_validacion.conflictos_criticos] if resultado_validacion.conflictos_criticos else None,
            forzado=fue_forzada
        )
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad en la base de datos"
        if settings.DEBUG:
            logger.error(f"{error_msg} al crear sesión: {e}")
        else:
            logger.error(f"{error_msg} al crear sesión")
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje=error_msg,
            forzado=False
        )
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos"
        if settings.DEBUG:
            logger.error(f"{error_msg} al crear sesión: {e}")
        else:
            logger.error(f"{error_msg} al crear sesión")
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje=error_msg,
            forzado=False
        )
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al crear sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje="Error interno del servidor",
            forzado=False
        )

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

def update_sesion(db: Session, sesion_id: int, datos: SesionUpdate, forzar_actualizacion: bool = False) -> ResultadoOperacion:
    """
    Actualiza una sesión existente con validación completa de conflictos.
    
    Args:
        db: Sesión de base de datos
        sesion_id: ID de la sesión a actualizar
        datos: Datos de actualización
        forzar_actualizacion: Si True, actualizar aunque haya conflictos críticos
    
    Returns:
        ResultadoOperacion: Resultado estructurado con:
            - exitoso: bool - Si la operación fue exitosa
            - entidad: Sesion | None - La sesión actualizada (si exitoso)
            - mensaje: str - Mensaje descriptivo del resultado
            - conflictos: Dict[str, List[Any]] | None - Conflictos serializables por categoría
            - total_conflictos: int - Número total de conflictos
            - conflictos_criticos: List[Any] | None - Lista de conflictos críticos serializables
            - forzado: bool - Si la actualización fue forzada pese a conflictos críticos
    """
    try:
        db_sesion = get_sesion_by_id(db, sesion_id)
        if not db_sesion:
            return ResultadoOperacion(
                exitoso=False,
                entidad=None,
                mensaje="Sesión no encontrada",
                forzado=False
            )
        
        # Obtener solo los campos que se van a actualizar
        update_data = datos.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return ResultadoOperacion(
                exitoso=True,
                entidad=db_sesion,
                mensaje="No hay cambios para aplicar",
                forzado=False
            )
        
        # Crear SesionCreate temporal para validación (con datos actuales + cambios)
        datos_actuales = {
            "asignatura_id": db_sesion.asignatura_id,
            "profesor_id": db_sesion.profesor_id,
            "aula_id": db_sesion.aula_id,
            "dia_semana": db_sesion.dia_semana,
            "inicio": db_sesion.inicio,
            "fin": db_sesion.fin,
            "tipo_clase": db_sesion.tipo_clase
        }
        datos_actuales.update(update_data)  # Aplicar cambios
        sesion_temp = SesionCreate(**datos_actuales)
        
        # Validación completa (ignorando la sesión actual)
        resultado_validacion = validar_sesion_completa(db, sesion_temp, sesion_id_ignorar=sesion_id)
        
        if not resultado_validacion.es_valido and not forzar_actualizacion:
            logger.warning(f"Actualización de sesión {sesion_id} bloqueada: {resultado_validacion.mensaje}")
            return ResultadoOperacion(
                exitoso=False,
                entidad=None,
                mensaje=resultado_validacion.mensaje,
                conflictos=serializar_conflictos(resultado_validacion.conflictos),
                total_conflictos=resultado_validacion.total_conflictos,
                conflictos_criticos=[asdict(c) for c in resultado_validacion.conflictos_criticos] if resultado_validacion.conflictos_criticos else None,
                forzado=False
            )
        
        # Aplicar actualizaciones
        for key, value in update_data.items():
            setattr(db_sesion, key, value)
        
        db.commit()
        db.refresh(db_sesion)
        
        # Determinar mensaje y logging (solo log warnings si hay conflictos)
        fue_forzada = forzar_actualizacion and len(resultado_validacion.conflictos_criticos) > 0
        
        if resultado_validacion.total_conflictos > 0:
            if fue_forzada:
                mensaje = f"Sesión {sesion_id} actualizada FORZADAMENTE con {len(resultado_validacion.conflictos_criticos)} conflictos críticos ignorados"
                logger.warning(f"ACTUALIZACIÓN FORZADA ID {sesion_id}: {len(resultado_validacion.conflictos_criticos)} conflictos críticos ignorados")
            else:
                mensaje = f"Sesión {sesion_id} actualizada con {resultado_validacion.total_conflictos} conflictos no críticos detectados"
                logger.warning(f"Sesión ID {sesion_id} actualizada con {resultado_validacion.total_conflictos} conflictos no críticos")
        else:
            mensaje = f"Sesión {sesion_id} actualizada exitosamente sin conflictos"
        
        # Logging detallado
        if settings.DEBUG:
            logger.info(f"Sesión actualizada - ID: {sesion_id}, Campos: {list(update_data.keys())}, Conflictos: {resultado_validacion.total_conflictos}, Forzada: {fue_forzada}")
        else:
            logger.info(f"Sesión actualizada - ID: {sesion_id}")
        
        return ResultadoOperacion(
            exitoso=True,
            entidad=db_sesion,
            mensaje=mensaje,
            conflictos=serializar_conflictos(resultado_validacion.conflictos) if resultado_validacion.total_conflictos > 0 else None,
            total_conflictos=resultado_validacion.total_conflictos,
            conflictos_criticos=[asdict(c) for c in resultado_validacion.conflictos_criticos] if resultado_validacion.conflictos_criticos else None,
            forzado=fue_forzada
        )
        
    except IntegrityError as e:
        db.rollback()
        error_msg = "Error de integridad al actualizar sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje=error_msg,
            forzado=False
        )
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = "Error de base de datos al actualizar"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje=error_msg,
            forzado=False
        )
        
    except Exception as e:
        db.rollback()
        error_msg = "Error inesperado al actualizar sesión"
        if settings.DEBUG:
            logger.error(f"{error_msg}: {e}")
        else:
            logger.error(error_msg)
        return ResultadoOperacion(
            exitoso=False,
            entidad=None,
            mensaje="Error interno del servidor",
            forzado=False
        )

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
    """Obtiene todas las sesiones asignadas a un profesor específico"""
    return db.query(Sesion).filter(Sesion.profesor_id == profesor_id).all()

def get_sesiones_by_asignatura(db: Session, asignatura_id: int) -> list[Sesion]:
    """Obtiene todas las sesiones de una asignatura específica"""
    return db.query(Sesion).filter(Sesion.asignatura_id == asignatura_id).all()

def get_sesiones_by_aula(db: Session, aula_id: int) -> list[Sesion]:
    """Obtiene todas las sesiones que se imparten en un aula específica"""
    return db.query(Sesion).filter(Sesion.aula_id == aula_id).all()


# ========================================
# FUNCIONES AUXILIARES
# ========================================

# 1. SERIALIZACIÓN (más utilizada)
def serializar_conflictos(conflictos: Optional[Dict[str, List[Any]]]) -> Optional[Dict[str, List[dict]]]:
    """
    Convierte una estructura de conflictos (dataclass o dict) a dict puro serializable.
    
    Args:
        conflictos: Dict con categorías y listas de conflictos (dataclass o dict)
    
    Returns:
        Dict serializable para JSON o None si input vacío
    """
    if not conflictos:
        return None
    return {
        cat: [asdict(c) if hasattr(c, "__dataclass_fields__") else c for c in lista]
        for cat, lista in conflictos.items()
    }


# 2. VALIDACIÓN COMPLETA (core del sistema)
def validar_sesion_completa(db: Session, sesion: SesionCreate, sesion_id_ignorar: Optional[int] = None) -> ResultadoValidacion:
    """
    Función de validación completa que incluye validación de entidades y detección de conflictos.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
        sesion_id_ignorar: ID de sesión a excluir (útil para updates)
    
    Returns:
        ResultadoValidacion: Resultado completo de la validación
    """
    try:
        # 1. Validar integridad referencial de entidades
        es_valido, mensaje = _validate_sesion_entities(db, sesion)
        if not es_valido:
            return ResultadoValidacion(
                es_valido=False,
                conflictos={},
                total_conflictos=0,
                conflictos_criticos=[],
                mensaje=mensaje
            )
        
        # 2. Detectar conflictos usando el sistema modular
        conflictos = detectar_todos_los_conflictos(db, sesion, sesion_id_ignorar)
        
        # 3. Análisis de conflictos críticos
        conflictos_criticos = []
        for categoria, lista_conflictos in conflictos.items():
            for conflicto in lista_conflictos:
                if hasattr(conflicto, 'severidad') and conflicto.severidad == "critico":
                    conflictos_criticos.append(conflicto)
        
        # 4. Calcular estadísticas
        total_conflictos = sum(len(v) for v in conflictos.values())
        es_valido = len(conflictos_criticos) == 0
        
        # 5. Generar mensaje descriptivo
        if es_valido:
            if total_conflictos > 0:
                mensaje = f"Validación completada con {total_conflictos} conflictos no críticos"
            else:
                mensaje = "Validación completada sin conflictos"
        else:
            mensaje = f"{len(conflictos_criticos)} conflictos críticos detectados que impiden la operación"
        
        return ResultadoValidacion(
            es_valido=es_valido,
            conflictos=conflictos,
            total_conflictos=total_conflictos,
            conflictos_criticos=conflictos_criticos,
            mensaje=mensaje
        )
        
    except Exception as e:
        logger.error(f"Error en validación completa de sesión: {e}")
        return ResultadoValidacion(
            es_valido=False,
            conflictos={},
            total_conflictos=0,
            conflictos_criticos=[],
            mensaje=f"Error interno en validación: {str(e)}"
        )


# 3. VALIDACIÓN DE INTEGRIDAD REFERENCIAL (helper interno)
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