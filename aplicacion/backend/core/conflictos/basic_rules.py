"""
Reglas Básicas de Detección (Capa Matemática Pura).

Este módulo contiene los algoritmos geométricos y temporales.
NO accede a base de datos.
NO decide severidades.
Solo responde: "¿X choca con Y?"
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Set
from collections import defaultdict
from datetime import datetime, date, timedelta, time

from core.conflictos.types import SesionRef

# -----------------------------------------------------------------------------
# Definición de Primitivas de Retorno (Tuplas crudas)
# -----------------------------------------------------------------------------
# (sesion1, sesion2, profesor_id)
SolapamientoProfesor = Tuple[SesionRef, SesionRef, int]

# (sesion1, sesion2, aula_id)
SolapamientoAula = Tuple[SesionRef, SesionRef, int]

# (sesion1, sesion2, asignatura_id_comun (o 0), motivo)
SolapamientoGrupo = Tuple[SesionRef, SesionRef, int, str]

# (sesion, profesor_id, motivo)
InterferenciaConciliacion = Tuple[SesionRef, int, str]


# -----------------------------------------------------------------------------
# 1. MOTOR MATEMÁTICO TEMPORAL
# -----------------------------------------------------------------------------

def sesiones_se_solapan_temporalmente(s1: SesionRef, s2: SesionRef) -> bool:
    """
    Compara dos sesiones. Devuelve True si sus intervalos de tiempo se intersectan.
    Maneja comparación Semanal vs Semanal (la más común).
    """
    # Caso A: Ambas semanales
    if s1.slot and s2.slot:
        if s1.slot.dia_semana != s2.slot.dia_semana:
            return False
        return _solapamiento_horas(
            s1.slot.hora_inicio, s1.slot.hora_fin,
            s2.slot.hora_inicio, s2.slot.hora_fin
        )

    # Caso B: Ambas fechadas (Exámenes, eventos únicos)
    if s1.intervalo and s2.intervalo:
        return (s1.intervalo.inicio < s2.intervalo.fin and 
                s2.intervalo.inicio < s1.intervalo.fin)

    # Caso C: Mixto (Por simplicidad, en esta versión devolvemos False)
    return False

def _solapamiento_horas(inicio1: time, fin1: time, inicio2: time, fin2: time) -> bool:
    """
    Fórmula de intersección: max(inicioA, inicioB) < min(finA, finB)
    """
    return inicio1 < fin2 and inicio2 < fin1


# -----------------------------------------------------------------------------
# 2. REGLAS DE RECURSOS FÍSICOS Y HUMANOS
# -----------------------------------------------------------------------------

def detectar_solapamientos_profesor(sesiones: List[SesionRef]) -> List[SolapamientoProfesor]:
    """
    Detecta si un profesor está asignado a dos sesiones simultáneas.
    """
    conflictos = []
    # Indexar: Profesor -> [Sesiones]
    mapa = defaultdict(list)
    for s in sesiones:
        for pid in s.profesor_ids:
            mapa[pid].append(s)
            
    # Comparar pares dentro del mismo profesor
    for pid, lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    conflictos.append((s1, s2, pid))
    return conflictos

def detectar_solapamientos_aula(sesiones: List[SesionRef]) -> List[SolapamientoAula]:
    """
    Detecta si un aula tiene dos sesiones simultáneas.
    """
    conflictos = []
    mapa = defaultdict(list)
    for s in sesiones:
        if s.aula_id is not None:
            mapa[s.aula_id].append(s)
            
    for aid, lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    conflictos.append((s1, s2, aid))
    return conflictos


# -----------------------------------------------------------------------------
# 3. REGLAS DE GRUPOS DOCENTES (ALUMNOS)
# -----------------------------------------------------------------------------

def detectar_solapamientos_grupos(sesiones: List[SesionRef]) -> List[SolapamientoGrupo]:
    """
    Detecta conflictos de alumno (ubicuidad).
    Cubre:
    1. Misma Asignatura: Teoría vs Práctica, o Grupo A vs Grupo A.
    2. Diferente Asignatura (mismo curso): Coherencia del plan de estudios.
    """
    conflictos = []
    
    # Agrupamos por CURSO para reducir complejidad (O(N^2) dentro del curso)
    mapa_curso = defaultdict(list)
    for s in sesiones:
        # Si no tiene curso definido (0), lo agrupamos aparte
        mapa_curso[s.curso].append(s)
        
    for curso, lista in mapa_curso.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                
                # 1. Filtro Temporal Rápido
                if not sesiones_se_solapan_temporalmente(s1, s2):
                    continue
                
                # 2. Filtro de Menciones (Si son disjuntas, no hay conflicto)
                # Si ambas tienen menciones definidas y NO comparten ninguna -> Poblaciones distintas
                if s1.mencion_ids and s2.mencion_ids:
                    set1 = set(s1.mencion_ids)
                    set2 = set(s2.mencion_ids)
                    if not set1.intersection(set2):
                        continue # Ej: Mates (Mención A) vs Física (Mención B) -> OK

                es_misma_asignatura = (s1.asignatura_id == s2.asignatura_id)
                es_conflicto = False
                motivo = ""

                # --- CASO A: MISMA ASIGNATURA ---
                if es_misma_asignatura:
                    # Regla: Teoría (Grupo único) choca con todo lo de su asignatura
                    tipo1, tipo2 = s1.tipo_grupo.upper(), s2.tipo_grupo.upper()
                    
                    if "TEORIA" in tipo1 or "TEORIA" in tipo2:
                        es_conflicto = True
                        motivo = "Incompatibilidad interna: Teoría se solapa con otra sesión."
                    else:
                        # Si son prácticas/labos, solo choca si es el MISMO código (A vs A)
                        # A vs B es un desdoble válido.
                        if s1.grupo_codigo == s2.grupo_codigo:
                            es_conflicto = True
                            motivo = f"Solapamiento de subgrupo idéntico ({s1.grupo_codigo})."
                
                # --- CASO B: DIFERENTE ASIGNATURA (Mismo Curso) ---
                else:
                    # Aquí asumimos que asignaturas del mismo curso/plan no deben solaparse
                    # salvo que sean optativas de menciones distintas (ya filtrado arriba)
                    es_conflicto = True
                    motivo = "Incoherencia del Plan de Estudios (Asignaturas del mismo nivel solapadas)."

                if es_conflicto:
                    asig_comun = s1.asignatura_id if es_misma_asignatura else 0
                    conflictos.append((s1, s2, asig_comun, motivo))

    return conflictos


# -----------------------------------------------------------------------------
# 4. REGLAS DE CONCILIACIÓN DOCENTE
# -----------------------------------------------------------------------------

def detectar_interferencias_conciliacion(
    sesiones: List[SesionRef],
    mapa_conciliacion: Dict[int, str], # {profesor_id: tipo_conciliacion}
    hora_apertura: time,
    hora_cierre: time,
    margen_normal: int,
    margen_mixto: int
) -> List[InterferenciaConciliacion]:
    """
    Verifica si las sesiones respetan los derechos de conciliación.
    Compara directamente horarios sin usar restricciones virtuales.
    """
    conflictos = []
    
    # Helpers para sumar horas a un objeto time
    def sumar_h(t: time, h: int) -> time:
        return (datetime.combine(date.today(), t) + timedelta(hours=h)).time()
    
    def restar_h(t: time, h: int) -> time:
        return (datetime.combine(date.today(), t) - timedelta(hours=h)).time()

    # Pre-cálculo de límites
    limite_entrada = sumar_h(hora_apertura, margen_normal)      # 08:00 + 2h = 10:00
    limite_salida = restar_h(hora_cierre, margen_normal)        # 21:00 - 2h = 19:00
    
    limite_mix_am = sumar_h(hora_apertura, margen_mixto)        # 08:00 + 1h = 09:00
    limite_mix_pm = restar_h(hora_cierre, margen_mixto)         # 21:00 - 1h = 20:00

    for s in sesiones:
        if not s.slot: continue # Solo aplica a horarios semanales definidos
        
        inicio = s.slot.hora_inicio
        fin = s.slot.hora_fin
        
        for pid in s.profesor_ids:
            tipo = mapa_conciliacion.get(pid)
            if not tipo: continue # Profe sin conciliación
            
            motivo = None
            
            if tipo == "entrada_tardia":
                if inicio < limite_entrada:
                    motivo = f"Clase inicia a las {inicio}, violando margen de entrada ({limite_entrada})."
            
            elif tipo == "salida_temprana":
                if fin > limite_salida:
                    motivo = f"Clase termina a las {fin}, violando margen de salida ({limite_salida})."
            
            elif tipo == "mixta":
                if inicio < limite_mix_am:
                    motivo = f"Violación margen entrada mixto ({inicio} < {limite_mix_am})."
                elif fin > limite_mix_pm:
                    motivo = f"Violación margen salida mixto ({fin} > {limite_mix_pm})."
            
            if motivo:
                conflictos.append((s, pid, motivo))

    return conflictos


# -----------------------------------------------------------------------------
# FACHADA PRINCIPAL (Punto de entrada)
# -----------------------------------------------------------------------------

def detectar_todos_los_conflictos_basicos(
    sesiones: List[SesionRef],
    mapa_conciliacion: Dict[int, str],
    hora_apertura: time,
    hora_cierre: time,
    margen_normal: int,
    margen_mixto: int
):
    """
    Ejecuta todas las reglas matemáticas en orden.
    """
    # 1. Aulas
    s_aula = detectar_solapamientos_aula(sesiones)
    
    # 2. Profesores
    s_prof = detectar_solapamientos_profesor(sesiones)
    
    # 3. Grupos
    s_grupo = detectar_solapamientos_grupos(sesiones)
    
    # 4. Conciliación
    s_conciliacion = detectar_interferencias_conciliacion(
        sesiones, mapa_conciliacion, 
        hora_apertura, hora_cierre, margen_normal, margen_mixto
    )
    
    return s_aula, s_prof, s_grupo, s_conciliacion