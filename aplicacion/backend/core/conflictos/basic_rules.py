from __future__ import annotations
from typing import List, Tuple
from collections import defaultdict
from datetime import datetime, date

from core.conflictos.types import SesionRef, RestriccionRef

# Primitivas
SolapamientoProfesor = Tuple[int, int, int] # s1, s2, prof_id
SolapamientoAula = Tuple[int, int, int]     # s1, s2, aula_id
SolapamientoGrupo = Tuple[int, int, int]    # s1, s2, asignatura_id (Nueva)
ViolacionRestriccion = Tuple[int, int]

# --- Lógica Temporal Mixta (EL NÚCLEO MATEMÁTICO) ---

def sesiones_se_solapan_temporalmente(s1: SesionRef, s2: SesionRef) -> bool:
    """
    Compara dos sesiones manejando:
    1. Semanal vs Semanal
    2. Fechada vs Fechada
    3. Semanal vs Fechada (La lógica compleja)
    """
    # Caso 1: Semanal vs Semanal
    if s1.slot and s2.slot:
        if s1.slot.dia_semana != s2.slot.dia_semana:
            return False
        return _solapamiento_horas(s1.slot.hora_inicio, s1.slot.hora_fin, 
                                   s2.slot.hora_inicio, s2.slot.hora_fin)

    # Caso 2: Fechada vs Fechada
    if s1.intervalo and s2.intervalo:
        return (s1.intervalo.inicio < s2.intervalo.fin and 
                s2.intervalo.inicio < s1.intervalo.fin)

    # Caso 3: Mixto (Semanal vs Fechada)
    # Identificar cual es cual
    sem = s1 if s1.slot else s2
    fech = s2 if s1.slot else s1
    
    return _solapamiento_semanal_fechada(sem, fech)

def _solapamiento_horas(inicio1, fin1, inicio2, fin2) -> bool:
    return inicio1 < fin2 and inicio2 < fin1

def _solapamiento_semanal_fechada(sem: SesionRef, fech: SesionRef) -> bool:
    """
    Verifica si una sesión fechada cae dentro del patrón de una semanal.
    """
    slot = sem.slot
    intervalo = fech.intervalo
    
    # 1. Verificar coincidencia de día de la semana
    # python weekday(): 0=Lunes, 6=Domingo (Coincide con nuestro slot)
    dia_fecha = intervalo.inicio.weekday()
    
    if dia_fecha != slot.dia_semana:
        return False
        
    # 2. Verificar coincidencia de horas
    # Extraemos la hora del intervalo fechado
    hora_inicio_fech = intervalo.inicio.time()
    hora_fin_fech = intervalo.fin.time()
    
    return _solapamiento_horas(slot.hora_inicio, slot.hora_fin, 
                               hora_inicio_fech, hora_fin_fech)

# --- Reglas de Negocio ---

def detectar_solapamientos_profesor(sesiones: List[SesionRef]) -> List[SolapamientoProfesor]:
    conflictos = set()
    # Agrupar por profesor
    mapa = defaultdict(list)
    for s in sesiones:
        for pid in s.profesor_ids:
            mapa[pid].append(s)
            
    for pid, lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    ids = tuple(sorted((s1.id, s2.id)))
                    conflictos.add((ids[0], ids[1], pid))
    return list(conflictos)

def detectar_solapamientos_aula(sesiones: List[SesionRef]) -> List[SolapamientoAula]:
    conflictos = set()
    mapa = defaultdict(list)
    for s in sesiones:
        if s.aula_id is not None: # Ignorar sesiones sin aula asignada
            mapa[s.aula_id].append(s)
            
    for aid, lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    ids = tuple(sorted((s1.id, s2.id)))
                    conflictos.add((ids[0], ids[1], aid))
    return list(conflictos)

def detectar_solapamientos_grupos(sesiones: List[SesionRef]) -> List[SolapamientoGrupo]:
    """
    Regla #2: Dos sesiones de la misma asignatura no pueden ser simultáneas,
    SALVO que sean de grupos docentes distintos (desdobles).
    """
    conflictos = set()
    # Agrupar por Asignatura
    mapa_asignatura = defaultdict(list)
    for s in sesiones:
        mapa_asignatura[s.asignatura_id].append(s)
        
    for asig_id, lista in mapa_asignatura.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                
                # Si son del mismo grupo docente, SIEMPRE es conflicto si se solapan
                # Si son de grupos distintos (ej: Grupo A y Grupo B de practicas),
                # asumimos que es un desdoble válido y NO es conflicto.
                if s1.grupo_id == s2.grupo_id:
                     if sesiones_se_solapan_temporalmente(s1, s2):
                        ids = tuple(sorted((s1.id, s2.id)))
                        conflictos.add((ids[0], ids[1], asig_id))
                        
    return list(conflictos)

def detectar_todos_los_conflictos_basicos(sesiones, restricciones):
    s_prof = detectar_solapamientos_profesor(sesiones)
    s_aula = detectar_solapamientos_aula(sesiones)
    s_grupo = detectar_solapamientos_grupos(sesiones)
    # Violaciones de restricción irían aquí (omitido por brevedad, usar lógica similar)
    violaciones = [] 
    
    return s_prof, s_aula, s_grupo, violaciones