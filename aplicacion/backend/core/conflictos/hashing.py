"""
Módulo de Hashing para Deduplicación de Conflictos.

Este módulo genera identificadores únicos (hashes) para los conflictos detectados.
El objetivo es evitar duplicados cuando el mismo conflicto se detecta desde
perspectivas diferentes (ej: Sesión A vs Sesión B y Sesión B vs Sesión A).
"""
import hashlib
from core.conflictos.types import ResultadoDeteccion
from constants.enums import TipoConflicto

def generar_hash_conflicto(resultado: ResultadoDeteccion) -> str:
    """
    Genera un hash único y determinista para un conflicto.
    
    Args:
        resultado: Objeto ResultadoDeteccion con los datos del conflicto.
        
    Returns:
        str: Hash SHA-256 en formato hexadecimal.
    """
    if not resultado.tipo:
        raise ValueError("El resultado debe tener un tipo de conflicto definido.")

    # Delegación a estrategias específicas según el tipo
    if resultado.tipo == TipoConflicto.SOLAPAMIENTO_AULA:
        return _hash_recurso_compartido(resultado, recurso_id=resultado.aula_id)
        
    elif resultado.tipo == TipoConflicto.SOLAPAMIENTO_PROFESOR:
        return _hash_recurso_compartido(resultado, recurso_id=resultado.profesor_id)
        
    elif resultado.tipo == TipoConflicto.SOLAPAMIENTO_GRUPO:
        return _hash_solapamiento_grupo(resultado)
        
    elif resultado.tipo == TipoConflicto.INTERFERENCIA_CONCILIACION:
        # La conciliación es un conflicto "unario" (afecta a 1 profesor en 1 sesión)
        return _hash_unario(resultado, recurso_id=resultado.profesor_id)
        
    else:
        return _hash_generico(resultado)


# -----------------------------------------------------------------------------
# Funciones Helper Privadas
# -----------------------------------------------------------------------------

def _get_sorted_session_ids(r: ResultadoDeteccion) -> str:
    """
    Devuelve los IDs de las sesiones ordenados para garantizar consistencia.
    Ejemplo: Si tenemos ID 5 y ID 2, devuelve "2-5".
    Esto asegura que A vs B genere el mismo hash que B vs A.
    """
    # Usamos 0 si sesion_2_id es None (caso raro en solapamientos)
    ids = sorted([r.sesion_id, r.sesion_2_id or 0])
    return f"{ids[0]}-{ids[1]}"

def _hash_recurso_compartido(r: ResultadoDeteccion, recurso_id: int) -> str:
    """
    Genera hash para conflictos donde dos sesiones pelean por un recurso (Aula/Profe).
    Formato: TIPO:ID_MENOR-ID_MAYOR:RECURSO_ID
    """
    if recurso_id is None:
        return _hash_generico(r)
        
    raw_key = f"{r.tipo.value}:{_get_sorted_session_ids(r)}:{recurso_id}"
    return hashlib.sha256(raw_key.encode()).hexdigest()

def _hash_solapamiento_grupo(r: ResultadoDeteccion) -> str:
    """
    Genera hash para conflictos de grupos (Alumnos).
    Incluye la asignatura para diferenciar contextos (aunque los IDs de sesión ya suelen ser únicos).
    Formato: TIPO:ID_MENOR-ID_MAYOR:ASIGNATURA_ID
    """
    asig_id = r.asignatura_id or 0
    raw_key = f"{r.tipo.value}:{_get_sorted_session_ids(r)}:{asig_id}"
    return hashlib.sha256(raw_key.encode()).hexdigest()

def _hash_unario(r: ResultadoDeteccion, recurso_id: int) -> str:
    """
    Genera hash para conflictos que involucran una sola entidad principal (ej: Conciliación).
    Formato: TIPO:SESION_ID:RECURSO_ID
    """
    # Aquí no ordenamos sesiones porque solo hay una principal que causa el problema
    raw_key = f"{r.tipo.value}:{r.sesion_id}:{recurso_id}"
    return hashlib.sha256(raw_key.encode()).hexdigest()

def _hash_generico(r: ResultadoDeteccion) -> str:
    """
    Estrategia de respaldo por si faltan datos específicos.
    Usa la descripción como parte del hash.
    """
    raw_key = f"{r.tipo.value}:{r.sesion_id}:{r.sesion_2_id}:{r.descripcion}"
    return hashlib.sha256(raw_key.encode()).hexdigest()