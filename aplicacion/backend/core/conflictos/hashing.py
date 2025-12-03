"""
Generación de hashes únicos para conflictos.
Asegura idempotencia en la detección de conflictos.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, time
from typing import Any, Dict, List, Tuple

from core.conflictos.types import (
    ResultadoDeteccion, 
    SesionRef, 
    RestriccionRef, 
    SlotSemanal, 
    Intervalo
)

from constants.enums import TipoConflicto

# ============================================================================
# Configuración Global
# ============================================================================

DEFAULT_HASH_VERSION = "v1"
DEFAULT_HASH_LENGTH = 20  # 20 hex chars (~80 bits) para mayor robustez con muchos conflictos

# ============================================================================
# Funciones de Normalización Temporal
# ============================================================================

def _format_time(t: time) -> str:
    """Formatea time a string consistente."""
    return f"{t.hour:02d}:{t.minute:02d}"

def _format_datetime(dt: datetime) -> str:
    """Formatea datetime a string consistente."""
    return dt.strftime("%Y%m%dT%H%M")

def _normalize_slot(slot: SlotSemanal) -> Dict[str, Any]:
    """Normaliza SlotSemanal a diccionario consistente."""
    return {
        "dia": slot.dia_semana,
        "inicio": _format_time(slot.hora_inicio),
        "fin": _format_time(slot.hora_fin)
    }

def _normalize_intervalo(intervalo: Intervalo) -> Dict[str, Any]:
    """Normaliza Intervalo a diccionario consistente."""
    return {
        "inicio": _format_datetime(intervalo.inicio),
        "fin": _format_datetime(intervalo.fin)
    }

def _extract_temporal_data(sesion: SesionRef) -> Dict[str, Any]:
    """
    Extrae datos temporales de una sesión.
    
    Raises:
        ValueError: Si la sesión no tiene datos temporales válidos
    """
    if sesion.slot is not None:
        return {"tipo": "slot", "data": _normalize_slot(sesion.slot)}
    elif sesion.intervalo is not None:
        return {"tipo": "intervalo", "data": _normalize_intervalo(sesion.intervalo)}
    else:
        raise ValueError(f"SesionRef {sesion.id} debe tener slot o intervalo")

def _extract_temporal_data_restriccion(restriccion: RestriccionRef) -> Dict[str, Any]:
    """
    Extrae datos temporales de una restricción.
    
    Raises:
        ValueError: Si la restricción no tiene datos temporales válidos
    """
    if restriccion.slot is not None:
        return {"tipo": "slot", "data": _normalize_slot(restriccion.slot)}
    elif restriccion.intervalo is not None:
        return {"tipo": "intervalo", "data": _normalize_intervalo(restriccion.intervalo)}
    else:
        raise ValueError(f"RestriccionRef {restriccion.id} debe tener slot o intervalo")

# ============================================================================
# Utilidades de Hash
# ============================================================================

def _sorted_ids(*ids: int) -> Tuple[int, ...]:
    """Ordena IDs de forma consistente."""
    return tuple(sorted(ids))

def _to_stable_json(obj: Any) -> str:
    """Convierte objeto a JSON de forma consistente."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def _calculate_hash(data: str, length: int = DEFAULT_HASH_LENGTH) -> str:
    """Calcula hash SHA256 de longitud especificada."""
    hash_obj = hashlib.sha256(data.encode('utf-8'))
    return hash_obj.hexdigest()[:length]

def _build_hash_components(components: List[str], version: str = DEFAULT_HASH_VERSION) -> str:
    """Construye string base para hash a partir de componentes."""
    # Insertar versión al principio para compatibilidad futura
    all_components = [version] + components
    return "|".join(all_components)

# ============================================================================
# Funciones Específicas de Hash (Internas)
# ============================================================================

def _hash_solapamiento_profesor(resultado: ResultadoDeteccion) -> str:
    """Hash para conflictos de solapamiento de profesor."""
    # Validar que tenemos las dos sesiones
    if resultado.sesion_2_id is None:
        raise ValueError("Solapamiento de profesor requiere sesion_2_id")
    
    # Ordenar IDs de sesión para consistencia
    sesion_a, sesion_b = _sorted_ids(resultado.sesion_id, resultado.sesion_2_id)
    
    # Componentes del hash
    components = [
        "PROF",  # Namespace corto
        str(resultado.profesor_id) if resultado.profesor_id else "NULL",
        str(sesion_a),
        str(sesion_b)
    ]
    
    # Agregar información temporal si está disponible en datos_contexto
    if "temporal_data" in resultado.datos_contexto:
        components.append(_to_stable_json(resultado.datos_contexto["temporal_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

def _hash_solapamiento_aula(resultado: ResultadoDeteccion) -> str:
    """Hash para conflictos de solapamiento de aula."""
    # Validar que tenemos las dos sesiones
    if resultado.sesion_2_id is None:
        raise ValueError("Solapamiento de aula requiere sesion_2_id")
    
    # Ordenar IDs de sesión para consistencia
    sesion_a, sesion_b = _sorted_ids(resultado.sesion_id, resultado.sesion_2_id)
    
    # Componentes del hash
    components = [
        "AULA",  # Namespace corto
        str(resultado.aula_id) if resultado.aula_id else "NULL",
        str(sesion_a),
        str(sesion_b)
    ]
    
    # Agregar información temporal si está disponible
    if "temporal_data" in resultado.datos_contexto:
        components.append(_to_stable_json(resultado.datos_contexto["temporal_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

def _hash_violacion_restriccion(resultado: ResultadoDeteccion) -> str:
    """Hash para conflictos de violación de restricción."""
    # Validar que tenemos restricción
    if resultado.restriccion_id is None:
        raise ValueError("Violación de restricción requiere restriccion_id")
    
    # Componentes del hash
    components = [
        "RSTR",  # Namespace corto
        str(resultado.restriccion_id),
        str(resultado.sesion_id)
    ]
    
    # Agregar información temporal y de ámbito si está disponible
    if "restriccion_data" in resultado.datos_contexto:
        components.append(_to_stable_json(resultado.datos_contexto["restriccion_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

def _hash_generico(resultado: ResultadoDeteccion) -> str:
    """Hash genérico para otros tipos de conflictos."""
    # Componentes básicos
    components = [
        resultado.tipo.value
    ]
    
    # Manejar sesiones: Si hay dos sesiones, usar par ordenado; si no, solo una
    if resultado.sesion_2_id is not None:
        # Conflicto binario: usar par ordenado
        sesion_a, sesion_b = _sorted_ids(resultado.sesion_id, resultado.sesion_2_id)
        components.extend([str(sesion_a), str(sesion_b)])
    else:
        # Conflicto unario: usar solo la sesión principal
        components.append(str(resultado.sesion_id))
    
    # Agregar campos opcionales si existen
    if resultado.profesor_id is not None:
        components.append(f"PROF:{resultado.profesor_id}")
        
    if resultado.aula_id is not None:
        components.append(f"AULA:{resultado.aula_id}")
        
    if resultado.restriccion_id is not None:
        components.append(f"RESTR:{resultado.restriccion_id}")
    
    # Agregar datos de contexto relevantes
    if resultado.datos_contexto:
        # Solo incluir claves que afecten la unicidad del conflicto
        relevant_context = {
            k: v for k, v in resultado.datos_contexto.items() 
            if k in ["temporal_data", "restriccion_data", "capacidad_data"]
        }
        if relevant_context:
            components.append(_to_stable_json(relevant_context))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

# ============================================================================
# API Principal
# ============================================================================

def generar_hash_conflicto(resultado: ResultadoDeteccion) -> str:
    """
    Genera un hash único para un conflicto detectado.
    
    El hash se basa en:
    - Tipo de conflicto
    - IDs de sesiones involucradas (ordenados consistentemente)
    - IDs de recursos involucrados (profesor, aula, restricción)
    - Información temporal relevante (si está disponible en datos_contexto)
    
    Args:
        resultado: ResultadoDeteccion con la información del conflicto
        
    Returns:
        str: Hash único del conflicto
        
    Raises:
        ValueError: Si el resultado no tiene información suficiente para generar hash
    """
    # Validar entrada
    if not resultado.tipo:
        raise ValueError("ResultadoDeteccion debe tener tipo definido")
    
    # Delegar a función específica según el tipo
    if resultado.tipo == TipoConflicto.SOLAPAMIENTO_PROFESOR:
        return _hash_solapamiento_profesor(resultado)
    elif resultado.tipo == TipoConflicto.SOLAPAMIENTO_AULA:
        return _hash_solapamiento_aula(resultado)
    elif resultado.tipo == TipoConflicto.VIOLACION_RESTRICCION:
        return _hash_violacion_restriccion(resultado)
    else:
        # Para otros tipos de conflicto, usar hash genérico
        return _hash_generico(resultado)

# ============================================================================
# Builders para Deduplicación Temprana (para el Motor)
# ============================================================================

def hash_solapamiento_profesor(sesion1: SesionRef, sesion2: SesionRef, profesor_id: int) -> str:
    """
    Genera hash de solapamiento de profesor ANTES de crear ResultadoDeteccion.
    
    Permite deduplicación temprana en el motor de conflictos.
    
    Args:
        sesion1, sesion2: Sesiones que se solapan
        profesor_id: ID del profesor afectado
        
    Returns:
        str: Hash que tendría el conflicto
        
    Raises:
        ValueError: Si las sesiones no tienen datos temporales válidos
    """
    # Ordenar IDs para consistencia
    sesion_a, sesion_b = _sorted_ids(sesion1.id, sesion2.id)
    
    # Extraer y ordenar datos temporales
    contexto_temporal = crear_contexto_temporal_sesiones(sesion1, sesion2)
    
    # Componentes del hash
    components = [
        "PROF",
        str(profesor_id),
        str(sesion_a),
        str(sesion_b)
    ]
    
    # Agregar información temporal
    if "temporal_data" in contexto_temporal:
        components.append(_to_stable_json(contexto_temporal["temporal_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

def hash_solapamiento_aula(sesion1: SesionRef, sesion2: SesionRef, aula_id: int) -> str:
    """
    Genera hash de solapamiento de aula ANTES de crear ResultadoDeteccion.
    
    Permite deduplicación temprana en el motor de conflictos.
    
    Args:
        sesion1, sesion2: Sesiones que se solapan
        aula_id: ID del aula afectada
        
    Returns:
        str: Hash que tendría el conflicto
        
    Raises:
        ValueError: Si las sesiones no tienen datos temporales válidos
    """
    # Ordenar IDs para consistencia
    sesion_a, sesion_b = _sorted_ids(sesion1.id, sesion2.id)
    
    # Extraer y ordenar datos temporales
    contexto_temporal = crear_contexto_temporal_sesiones(sesion1, sesion2)
    
    # Componentes del hash
    components = [
        "AULA",
        str(aula_id),
        str(sesion_a),
        str(sesion_b)
    ]
    
    # Agregar información temporal
    if "temporal_data" in contexto_temporal:
        components.append(_to_stable_json(contexto_temporal["temporal_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

def hash_violacion_restriccion(sesion: SesionRef, restriccion: RestriccionRef) -> str:
    """
    Genera hash de violación de restricción ANTES de crear ResultadoDeteccion.
    
    Permite deduplicación temprana en el motor de conflictos.
    
    Args:
        sesion: Sesión que viola la restricción
        restriccion: Restricción violada
        
    Returns:
        str: Hash que tendría el conflicto
        
    Raises:
        ValueError: Si sesión y restricción no tienen datos temporales válidos
    """
    # Crear contexto de restricción
    contexto_restriccion = crear_contexto_restriccion(sesion, restriccion)
    
    # Componentes del hash
    components = [
        "RSTR",
        str(restriccion.id),
        str(sesion.id)
    ]
    
    # Agregar información temporal y de ámbito
    if "restriccion_data" in contexto_restriccion:
        components.append(_to_stable_json(contexto_restriccion["restriccion_data"]))
    
    hash_base = _build_hash_components(components)
    return _calculate_hash(hash_base)

# ============================================================================
# Funciones Auxiliares para el Motor de Conflictos
# ============================================================================

def crear_contexto_temporal_sesiones(sesion1: SesionRef, sesion2: SesionRef) -> Dict[str, Any]:
    """
    Crea contexto temporal para conflictos entre dos sesiones.
    
    Los datos se ordenan por ID de sesión para garantizar hash consistente
    independientemente del orden de llamada (A,B) vs (B,A).
    
    Útil para pasar al ResultadoDeteccion.datos_contexto antes de generar hash.
    """
    try:
        # Extraer datos temporales
        temporal1 = _extract_temporal_data(sesion1)
        temporal2 = _extract_temporal_data(sesion2)
        
        # Ordenar por ID para consistencia canónica
        items = sorted([
            (sesion1.id, temporal1),
            (sesion2.id, temporal2)
        ], key=lambda x: x[0])
        
        # Crear estructura ordenada
        return {
            "temporal_data": [
                {"id": items[0][0], "temporal": items[0][1]},
                {"id": items[1][0], "temporal": items[1][1]}
            ]
        }
    except ValueError:
        # Si no podemos extraer datos temporales, devolver contexto vacío
        return {}

def crear_contexto_restriccion(sesion: SesionRef, restriccion: RestriccionRef) -> Dict[str, Any]:
    """
    Crea contexto para conflictos de violación de restricción.
    
    Útil para pasar al ResultadoDeteccion.datos_contexto antes de generar hash.
    """
    try:
        temporal_sesion = _extract_temporal_data(sesion)
        temporal_restriccion = _extract_temporal_data_restriccion(restriccion)
        
        return {
            "restriccion_data": {
                "sesion": temporal_sesion,
                "restriccion": temporal_restriccion,
                "ambito": restriccion.ambito,
                "es_blanda": restriccion.es_blanda
            }
        }
    except ValueError:
        # Si no podemos extraer datos temporales, devolver contexto básico
        return {
            "restriccion_data": {
                "ambito": restriccion.ambito,
                "es_blanda": restriccion.es_blanda
            }
        }

# ============================================================================
# Validaciones
# ============================================================================

def validar_consistencia_temporal(sesion1: SesionRef, sesion2: SesionRef) -> bool:
    """
    Valida que dos sesiones tengan tipos temporales compatibles para comparación.
    
    Returns:
        bool: True si son compatibles, False si no
    """
    try:
        temp1 = _extract_temporal_data(sesion1)
        temp2 = _extract_temporal_data(sesion2)
        return temp1["tipo"] == temp2["tipo"]
    except ValueError:
        return False

def validar_consistencia_restriccion(sesion: SesionRef, restriccion: RestriccionRef) -> bool:
    """
    Valida que sesión y restricción tengan tipos temporales compatibles.
    
    Returns:
        bool: True si son compatibles, False si no
    """
    try:
        temp_sesion = _extract_temporal_data(sesion)
        temp_restriccion = _extract_temporal_data_restriccion(restriccion)
        return temp_sesion["tipo"] == temp_restriccion["tipo"]
    except ValueError:
        return False
