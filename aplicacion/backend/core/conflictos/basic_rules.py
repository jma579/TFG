"""
Reglas básicas de detección de conflictos académicos.

Este módulo contiene funciones puras para detectar los conflictos fundamentales:
- Detección de solapamientos de profesores
- Detección de solapamientos de aulas  
- Validación de restricciones temporales básicas

Las funciones devuelven primitivas de detección que el engine convertirá 
a ResultadoDeteccion con hashing y deduplicación.

Las reglas avanzadas y arquitectura de registry se implementarán en Fase 4.1.4.
"""

from __future__ import annotations
from typing import List, Dict, Tuple
from collections import defaultdict

from core.conflictos.types import SesionRef, RestriccionRef, Intervalo, SlotSemanal

# ============================================================================
# TIPOS DE DATOS PARA DETECCIÓN
# ============================================================================

# Primitivas de detección que devuelven las funciones (usando IDs para determinismo)
SolapamientoProfesor = Tuple[int, int, int]  # (sesion_id1, sesion_id2, profesor_id) - IDs ordenados
SolapamientoAula = Tuple[int, int, int]      # (sesion_id1, sesion_id2, aula_id) - IDs ordenados  
ViolacionRestriccion = Tuple[int, int]       # (sesion_id/profesor_id, restriccion_id) - determinista

# ============================================================================
# UTILIDADES TEMPORALES
# ============================================================================

def sesiones_se_solapan_temporalmente(s1: SesionRef, s2: SesionRef) -> bool:
    """
    Determina si dos sesiones se solapan en tiempo.
    
    Solo soporta casos simples para Fase 2.1.3:
    - Ambas semanales (slot vs slot)
    - Ambas fechadas (intervalo vs intervalo)
    
    Args:
        s1, s2: Sesiones a comparar
        
    Returns:
        True si se solapan temporalmente
        
    Raises:
        ValueError: Si las sesiones no tienen datos temporales válidos
    """
    # Caso 1: Ambas semanales (slot vs slot)
    if s1.slot and s2.slot:
        slot1, slot2 = s1.slot, s2.slot

        # Mismo día de la semana
        if slot1.dia_semana != slot2.dia_semana:
            return False
            
        # Solapamiento de intervalos: inicio < fin_otro && inicio_otro < fin
        return (slot1.hora_inicio < slot2.hora_fin and 
                slot2.hora_inicio < slot1.hora_fin)
    
    # Caso 2: Ambas fechadas (intervalo vs intervalo)  
    elif s1.intervalo and s2.intervalo:
        int1, int2 = s1.intervalo, s2.intervalo

        # Solapamiento de intervalos: inicio < fin_otro && inicio_otro < fin
        return (int1.inicio < int2.fin and int2.inicio < int1.fin)
    
    #TODO: Eliminar este aspecto en un futuro
    # Caso 3: Mixtas - no soportado en Fase 2.1.3
    else:
        raise ValueError(f"Comparación mixta no soportada: s1={type(s1.slot)}, s2={type(s2.slot)}")


def sesion_viola_restriccion_temporal(sesion: SesionRef, restriccion: RestriccionRef) -> bool:
    """
    Determina si una sesión viola una restricción temporal.
    
    Primero verifica ámbito (AULA/PROFESOR), luego solapamiento temporal.
    
    Args:
        sesion: Sesión a verificar
        restriccion: Restricción a aplicar
        
    Returns:
        True si hay violación
    """
    # 1. Verificar ámbito - ¿la restricción aplica a esta sesión?
    if restriccion.ambito == "AULA":
        if restriccion.aula_id != sesion.aula_id:
            return False  # No aplica a esta aula
            
    elif restriccion.ambito == "PROFESOR":
        if not restriccion.profesor_id or restriccion.profesor_id not in sesion.profesor_ids:
            return False  # No aplica a ningún profesor de esta sesión
    
    # 2. Verificar solapamiento temporal
    # Caso 1: Restricción semanal vs sesión semanal 
    if restriccion.slot and sesion.slot:
        r_slot, s_slot = restriccion.slot, sesion.slot

        # Mismo día de la semana
        if r_slot.dia_semana != s_slot.dia_semana:
            return False
            
        # Solapamiento de intervalos
        return (r_slot.hora_inicio < s_slot.hora_fin and 
                s_slot.hora_inicio < r_slot.hora_fin)
    
    # Caso 2: Restricción fechada vs sesión fechada
    elif restriccion.intervalo and sesion.intervalo:
        r_int, s_int = restriccion.intervalo, sesion.intervalo

        # Solapamiento de intervalos
        return (r_int.inicio < s_int.fin and s_int.inicio < r_int.fin)
    
    # Caso 3: Tipos incompatibles - no hay violación
    else:
        return False


def agrupar_sesiones_por_profesor(sesiones: List[SesionRef]) -> Dict[int, List[SesionRef]]:
    """
    Agrupa sesiones por profesor para detección eficiente O(n).
    
    IMPORTANTE: Una sesión puede aparecer en múltiples grupos si tiene varios profesores.
    
    Args:
        sesiones: Lista de sesiones
        
    Returns:
        Diccionario {profesor_id: [sesiones_del_profesor]}
    """
    grupos = defaultdict(list)
    for sesion in sesiones:
        if sesion.profesor_ids:  # Corregido: usar profesor_ids (lista)
            for profesor_id in sesion.profesor_ids:
                grupos[profesor_id].append(sesion)
    return dict(grupos)


def agrupar_sesiones_por_aula(sesiones: List[SesionRef]) -> Dict[int, List[SesionRef]]:
    """
    Agrupa sesiones por aula para detección eficiente O(n).
    
    Args:
        sesiones: Lista de sesiones
        
    Returns:
        Diccionario {aula_id: [sesiones_del_aula]}
    """
    grupos = defaultdict(list)
    for sesion in sesiones:
        if sesion.aula_id is not None:
            grupos[sesion.aula_id].append(sesion)
    return dict(grupos)

# ============================================================================
# FUNCIONES DE DETECCIÓN BÁSICA
# ============================================================================

def detectar_solapamientos_profesor(sesiones: List[SesionRef]) -> List[SolapamientoProfesor]:
    """
    Detecta cuando un profesor tiene sesiones simultáneas.
    
    Lógica simple:
    - Agrupa sesiones por profesor
    - Para cada profesor, compara todas sus sesiones por pares
    - Detecta solapamientos temporales
    - Usa deduplicación con IDs ordenados
    
    Args:
        sesiones: Lista de sesiones a analizar
        
    Returns:
        Lista de tuplas (sesion_id1, sesion_id2, profesor_id) con solapamientos
    """
    conflictos_set = set()  # Deduplicación
    grupos_profesor = agrupar_sesiones_por_profesor(sesiones)
    
    for profesor_id, sesiones_profesor in grupos_profesor.items():
        # Comparación por pares O(n²) para cada profesor
        for i in range(len(sesiones_profesor)):
            for j in range(i + 1, len(sesiones_profesor)):
                s1, s2 = sesiones_profesor[i], sesiones_profesor[j]
                
                if sesiones_se_solapan_temporalmente(s1, s2):
                    # IDs ordenados para evitar duplicados A-B / B-A
                    id1, id2 = sorted([s1.id, s2.id])
                    conflictos_set.add((id1, id2, profesor_id))
    
    return list(conflictos_set)


def detectar_solapamientos_aula(sesiones: List[SesionRef]) -> List[SolapamientoAula]:
    """
    Detecta cuando un aula tiene sesiones simultáneas.
    
    Lógica simple:
    - Agrupa sesiones por aula
    - Para cada aula, compara todas sus sesiones por pares
    - Detecta solapamientos temporales
    - Usa deduplicación con IDs ordenados
    
    Args:
        sesiones: Lista de sesiones a analizar
        
    Returns:
        Lista de tuplas (sesion_id1, sesion_id2, aula_id) con solapamientos
    """
    conflictos_set = set()  # Deduplicación
    grupos_aula = agrupar_sesiones_por_aula(sesiones)
    
    for aula_id, sesiones_aula in grupos_aula.items():
        # Comparación por pares O(n²) para cada aula
        for i in range(len(sesiones_aula)):
            for j in range(i + 1, len(sesiones_aula)):
                s1, s2 = sesiones_aula[i], sesiones_aula[j]
                
                if sesiones_se_solapan_temporalmente(s1, s2):
                    # IDs ordenados para evitar duplicados A-B / B-A
                    id1, id2 = sorted([s1.id, s2.id])
                    conflictos_set.add((id1, id2, aula_id))
    
    return list(conflictos_set)


def detectar_violaciones_restriccion(sesiones: List[SesionRef], restricciones: List[RestriccionRef]) -> List[ViolacionRestriccion]:
    """
    Detecta violaciones de restricciones temporales básicas.
    
    Lógica simple:
    - Para cada sesión, verifica contra todas las restricciones
    - Verifica ámbito antes de comparar tiempos
    - Detecta solapamientos temporales con restricciones
    
    Args:
        sesiones: Sesiones a analizar
        restricciones: Restricciones aplicables
        
    Returns:
        Lista de tuplas (sesion_id, restriccion_id) con violaciones
    """
    conflictos_set = set()  # Deduplicación
    
    for sesion in sesiones:
        for restriccion in restricciones:
            if sesion_viola_restriccion_temporal(sesion, restriccion):
                # Usar IDs para determinismo
                conflictos_set.add((sesion.id, restriccion.id))
    
    return list(conflictos_set)


# ============================================================================
# FUNCIÓN DE CONVENIENCIA PRINCIPAL
# ============================================================================

def detectar_todos_los_conflictos_basicos(sesiones: List[SesionRef], restricciones: List[RestriccionRef]) -> Tuple[List[SolapamientoProfesor], List[SolapamientoAula], List[ViolacionRestriccion]]:
    """
    Ejecuta todas las funciones de detección básica.
    
    Esta función orquesta la detección pero no construye ResultadoDeteccion.
    El engine se encargará de convertir estas primitivas de IDs a objetos completos
    con hashing y deduplicación adicional si es necesaria.
    
    Args:
        sesiones: Sesiones a analizar
        restricciones: Restricciones aplicables
        
    Returns:
        Tupla con:
        - solapamientos_profesor: List[(sesion_id1, sesion_id2, profesor_id)]
        - solapamientos_aula: List[(sesion_id1, sesion_id2, aula_id)]  
        - violaciones_restriccion: List[(sesion_id, restriccion_id)]
    """
    solapamientos_profesor = detectar_solapamientos_profesor(sesiones)
    solapamientos_aula = detectar_solapamientos_aula(sesiones)
    violaciones_restriccion = detectar_violaciones_restriccion(sesiones, restricciones)
    
    return solapamientos_profesor, solapamientos_aula, violaciones_restriccion
