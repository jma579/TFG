"""
Módulo para la detección de conflictos temporales en horarios académicos.

Conflictos de lógica de negocio implementados:
1. Solape de profesor: mismo profesor en dos sesiones simultáneas
2. Solape de aula: misma aula ocupada por dos sesiones simultáneas  
3. Solape de asignatura: misma asignatura en dos lugares diferentes simultáneamente
   (con excepción para laboratorios simultáneos válidos)

Nota: Las validaciones transaccionales (duración, horarios válidos, etc.) 
están cubiertas por los schemas de Pydantic y no se incluyen aquí.
"""

from datetime import time, datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import logging

# SQLAlchemy imports
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Imports de modelos
from models.sesion import Sesion
from models.asignatura import Asignatura
from models.profesor import Profesor
from models.aula import Aula

# Imports de schemas
from schemas.sesion import SesionCreate, SesionOut

# Imports de enums
from constants.enums import DiaSemanaEnum, TipoAulaEnum

# Configuración de logging
logger = logging.getLogger(__name__)

# Nota: Las constantes de duración (DURACION_MINIMA_SESION, DURACION_MAXIMA_SESION) 
# fueron eliminadas ya que esas validaciones están cubiertas por los schemas de Pydantic


@dataclass
class ConflictoTemporal:
    """Estructura para representar un conflicto temporal detectado"""
    tipo: str
    severidad: str
    mensaje: str
    sesion_conflictiva: Optional[SesionOut] = None
    detalles: Optional[Dict[str, Any]] = None
    sugerencias: List[str] = field(default_factory=list)




# ========================================
# FUNCIONES DE DETECCIÓN DE CONFLICTOS
# ========================================


def detectar_solape_profesor(db: Session, sesion: SesionCreate) -> List[ConflictoTemporal]:
    """
    Detecta si un profesor tiene conflictos de horario.
    
    Verifica que el mismo profesor no esté asignado a dos sesiones
    que coinciden parcial o totalmente en franja horaria el mismo día.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados
    """
    conflictos = []
    
    try:
        # Buscar todas las sesiones del mismo profesor en el mismo día
        sesiones_existentes = db.query(Sesion).filter(
            Sesion.profesor_id == sesion.profesor_id,
            Sesion.dia == sesion.dia.value  # Usar .value para convertir enum a string
        ).all()
        
        for sesion_existente in sesiones_existentes:
            if horarios_se_solapan(
                sesion.hora_inicio, sesion.hora_fin,
                sesion_existente.hora_inicio, sesion_existente.hora_fin
            ):
                # Obtener información adicional del profesor para el mensaje
                profesor = db.query(Profesor).filter(Profesor.id == sesion.profesor_id).first()
                profesor_nombre = profesor.nombre if profesor else f"ID {sesion.profesor_id}"
                
                conflicto = ConflictoTemporal(
                    tipo="solape_profesor",
                    severidad="critico",
                    mensaje=f"El profesor {profesor_nombre} ya tiene clase el {sesion.dia} "
                           f"de {sesion_existente.hora_inicio} a {sesion_existente.hora_fin}",
                    sesion_conflictiva=SesionOut.model_validate(sesion_existente),
                    detalles={
                        "profesor_id": sesion.profesor_id,
                        "profesor_nombre": profesor_nombre,
                        "dia": sesion.dia,
                        "horario_conflictivo": f"{sesion_existente.hora_inicio}-{sesion_existente.hora_fin}"
                    },
                    sugerencias=[
                        "Cambiar el horario de la nueva sesión",
                        "Asignar un profesor diferente",
                        "Modificar el horario de la sesión existente"
                    ]
                )
                conflictos.append(conflicto)
                
    except Exception as e:
        logger.error(f"Error al detectar solape de profesor: {e}")
        conflictos.append(ConflictoTemporal(
            tipo="error_validacion",
            severidad="critico", 
            mensaje=f"Error interno al validar conflictos de profesor: {str(e)}"
        ))
    
    return conflictos


def detectar_solape_aula(db: Session, sesion: SesionCreate) -> List[ConflictoTemporal]:
    """
    Detecta si un aula tiene conflictos de ocupación.
    
    Verifica que la misma aula no esté asignada a dos sesiones
    que se pisan en horario.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados
    """
    conflictos = []
    
    try:
        # Buscar todas las sesiones en la misma aula el mismo día
        sesiones_existentes = db.query(Sesion).filter(
            Sesion.aula_id == sesion.aula_id,
            Sesion.dia == sesion.dia.value  # Usar .value para convertir enum a string
        ).all()
        
        for sesion_existente in sesiones_existentes:
            if horarios_se_solapan(
                sesion.hora_inicio, sesion.hora_fin,
                sesion_existente.hora_inicio, sesion_existente.hora_fin
            ):
                # Obtener información adicional del aula para el mensaje
                aula = db.query(Aula).filter(Aula.id == sesion.aula_id).first()
                aula_nombre = aula.nombre if aula else f"ID {sesion.aula_id}"
                
                conflicto = ConflictoTemporal(
                    tipo="solape_aula",
                    severidad="critico",
                    mensaje=f"El aula {aula_nombre} ya está ocupada el {sesion.dia} "
                           f"de {sesion_existente.hora_inicio} a {sesion_existente.hora_fin}",
                    sesion_conflictiva=SesionOut.model_validate(sesion_existente),
                    detalles={
                        "aula_id": sesion.aula_id,
                        "aula_nombre": aula_nombre,
                        "dia": sesion.dia,
                        "horario_conflictivo": f"{sesion_existente.hora_inicio}-{sesion_existente.hora_fin}"
                    },
                    sugerencias=[
                        "Cambiar a otra aula disponible",
                        "Modificar el horario de la nueva sesión", 
                        "Reprogramar la sesión existente"
                    ]
                )
                conflictos.append(conflicto)
                
    except Exception as e:
        logger.error(f"Error al detectar solape de aula: {e}")
        conflictos.append(ConflictoTemporal(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al validar conflictos de aula: {str(e)}"
        ))
    
    return conflictos


def detectar_solape_asignatura(db: Session, sesion: SesionCreate) -> List[ConflictoTemporal]:
    """
    Detecta si una asignatura tiene conflictos de programación simultánea.
    
    Verifica que la misma asignatura no se imparta en dos lugares diferentes
    a la vez, excepto para sesiones de laboratorio simultáneas con profesor
    distinto en cada sesión y cada sesión en aula diferente.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista de conflictos encontrados
    """
    conflictos = []
    
    try:
        # Buscar otras sesiones de la misma asignatura en el mismo día
        sesiones_existentes = db.query(Sesion).filter(
            Sesion.asignatura_id == sesion.asignatura_id,
            Sesion.dia == sesion.dia.value  # Usar .value para convertir enum a string
        ).all()
        
        for sesion_existente in sesiones_existentes:
            if horarios_se_solapan(
                sesion.hora_inicio, sesion.hora_fin,
                sesion_existente.hora_inicio, sesion_existente.hora_fin
            ):
                # Verificar si es una excepción válida (laboratorios simultáneos)
                es_excepcion_valida = verificar_excepcion_laboratorio(db, sesion, sesion_existente)
                
                if not es_excepcion_valida:
                    # Obtener información adicional de la asignatura
                    asignatura = db.query(Asignatura).filter(Asignatura.id == sesion.asignatura_id).first()
                    asignatura_nombre = asignatura.nombre if asignatura else f"ID {sesion.asignatura_id}"
                    
                    conflicto = ConflictoTemporal(
                        tipo="solape_asignatura",
                        severidad="alto",
                        mensaje=f"La asignatura {asignatura_nombre} ya tiene otra sesión programada el {sesion.dia} "
                               f"de {sesion_existente.hora_inicio} a {sesion_existente.hora_fin}",
                        sesion_conflictiva=SesionOut.model_validate(sesion_existente),
                        detalles={
                            "asignatura_id": sesion.asignatura_id,
                            "asignatura_nombre": asignatura_nombre,
                            "dia": sesion.dia,
                            "horario_conflictivo": f"{sesion_existente.hora_inicio}-{sesion_existente.hora_fin}"
                        },
                        sugerencias=[
                            "Verificar si es intencional (diferentes grupos)",
                            "Cambiar el horario de una de las sesiones",
                            "Confirmar que se trata de sesiones de laboratorio válidas"
                        ]
                    )
                    conflictos.append(conflicto)
                    
    except Exception as e:
        logger.error(f"Error al detectar solape de asignatura: {e}")
        conflictos.append(ConflictoTemporal(
            tipo="error_validacion",
            severidad="critico",
            mensaje=f"Error interno al validar conflictos de asignatura: {str(e)}"
        ))
    
    return conflictos


# Función eliminada: detectar_duracion_fuera_limite
# Razón: Las validaciones de duración están cubiertas por los schemas de Pydantic
# Los schemas ya validan: duración mínima (60 min), máxima (120 min) e incrementos válidos


def detectar_todos_conflictos_temporales(db: Session, sesion: SesionCreate) -> List[ConflictoTemporal]:
    """
    Función principal que ejecuta todas las validaciones de conflictos temporales.
    
    Args:
        db: Sesión de base de datos
        sesion: Datos de la sesión a validar
    
    Returns:
        Lista completa de todos los conflictos temporales detectados
    """
    todos_conflictos = []
    
    logger.info(f"Iniciando detección de conflictos temporales para sesión: "
               f"Asignatura {sesion.asignatura_id}, Profesor {sesion.profesor_id}, "
               f"Aula {sesion.aula_id}, {sesion.dia} {sesion.hora_inicio}-{sesion.hora_fin}")
    
    # Ejecutar todas las validaciones de lógica de negocio
    todos_conflictos.extend(detectar_solape_profesor(db, sesion))
    todos_conflictos.extend(detectar_solape_aula(db, sesion))
    todos_conflictos.extend(detectar_solape_asignatura(db, sesion))
    # Nota: detectar_duracion_fuera_limite eliminada - está cubierta por schemas
    
    logger.info(f"Detección completada. {len(todos_conflictos)} conflictos encontrados")
    
    return todos_conflictos




# ========================================
# FUNCIONES AUXILIARES
# ========================================

def horarios_se_solapan(inicio1: time, fin1: time, inicio2: time, fin2: time) -> bool:
    """
    Determina si dos rangos horarios se solapan.
    
    Args:
        inicio1, fin1: Horario del primer rango
        inicio2, fin2: Horario del segundo rango
    
    Returns:
        True si hay solapamiento, False en caso contrario
    
    Lógica: 
    - Dos rangos se solapan si el inicio de uno es antes del fin del otro
    - Si una clase termina exactamente cuando otra empieza, NO hay solapamiento
    - Ejemplo: 08:00-10:00 y 10:00-12:00 → NO se solapan
    - Ejemplo: 08:00-10:30 y 10:00-12:00 → SÍ se solapan
    """
    return inicio1 < fin2 and inicio2 < fin1


def calcular_duracion_minutos(hora_inicio: time, hora_fin: time) -> int:
    """
    Calcula la duración en minutos entre dos horas.
    
    Args:
        hora_inicio: Hora de inicio
        hora_fin: Hora de fin
    
    Returns:
        Duración en minutos
    """
    # Convertir a datetime para hacer la resta
    fecha_base = datetime.now().date()
    inicio_dt = datetime.combine(fecha_base, hora_inicio)
    fin_dt = datetime.combine(fecha_base, hora_fin)
    
    # Si la hora de fin es menor que la de inicio, asumimos que es al día siguiente
    if hora_fin < hora_inicio:
        fin_dt += timedelta(days=1)
    
    diferencia = fin_dt - inicio_dt
    return int(diferencia.total_seconds() / 60)


def verificar_excepcion_laboratorio(db: Session, sesion_nueva: SesionCreate, sesion_existente: Sesion) -> bool:
    """
    Verifica si dos sesiones simultáneas de la misma asignatura son una excepción válida.
    
    Excepción válida: sesiones de laboratorio simultáneas con:
    - Profesor distinto en cada sesión
    - Cada sesión impartida en aula diferente
    - Ambas aulas son de tipo laboratorio
    
    Args:
        db: Sesión de base de datos
        sesion_nueva: Nueva sesión a validar
        sesion_existente: Sesión existente que genera conflicto
    
    Returns:
        True si es una excepción válida, False en caso contrario
    """
    try:
        # Verificar que tienen profesores diferentes
        if sesion_nueva.profesor_id == sesion_existente.profesor_id:
            return False
        
        # Verificar que tienen aulas diferentes
        if sesion_nueva.aula_id == sesion_existente.aula_id:
            return False
        
        # Verificar que ambas aulas son de tipo laboratorio
        aula_nueva = db.query(Aula).filter(Aula.id == sesion_nueva.aula_id).first()
        aula_existente = db.query(Aula).filter(Aula.id == sesion_existente.aula_id).first()
        
        if not aula_nueva or not aula_existente:
            return False
            
        # Verificar que ambas son laboratorios
        tipos_laboratorio = [TipoAulaEnum.LABORATORIO, TipoAulaEnum.INFORMATICA]
        
        if (aula_nueva.tipo in tipos_laboratorio and 
            aula_existente.tipo in tipos_laboratorio):
            logger.info(f"Excepción válida: laboratorios simultáneos de la misma asignatura "
                       f"con profesores y aulas diferentes")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error al verificar excepción de laboratorio: {e}")
        return False
