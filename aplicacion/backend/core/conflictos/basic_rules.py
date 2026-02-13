"""
Reglas Básicas de Detección (Capa Matemática Pura).

Este módulo contiene los algoritmos geométricos y temporales.
NO accede a base de datos. NO decide severidades.
Solo responde: "¿X choca con Y?"
"""

from typing import List, Tuple, Dict
from collections import defaultdict
from datetime import datetime, date, timedelta, time

from core.conflictos.types import SesionRef

# Definición de Primitivas de Retorno (Tuplas crudas)
SolapamientoProfesor = Tuple[SesionRef, SesionRef, int] # (Sesión A, Sesión B, Profesor ID)
SolapamientoAula = Tuple[SesionRef, SesionRef, int] # (Sesión A, Sesión B, Aula ID)
SolapamientoGrupo = Tuple[SesionRef, SesionRef, int, str] # (Sesión A, Sesión B, Asignatura ID común o 0, Motivo específico) 
InterferenciaConciliacion = Tuple[SesionRef, int, str] # (Sesión, Profesor ID, Motivo específico)


# Motor Matemático Temporal

def sesiones_se_solapan_temporalmente(s1: SesionRef, s2: SesionRef) -> bool:
    """
    Compara dos sesiones. Devuelve True si sus intervalos de tiempo se intersectan.
    """
    if s1.slot and s2.slot:
        if s1.slot.dia_semana != s2.slot.dia_semana:
            return False
        return _solapamiento_horas(
            s1.slot.hora_inicio, s1.slot.hora_fin,
            s2.slot.hora_inicio, s2.slot.hora_fin
        )

    if s1.intervalo and s2.intervalo:
        return (s1.intervalo.inicio < s2.intervalo.fin and 
                s2.intervalo.inicio < s1.intervalo.fin)

    return False


def _solapamiento_horas(inicio1: time, fin1: time, inicio2: time, fin2: time) -> bool:
    """Fórmula de intersección: max(inicioA, inicioB) < min(finA, finB)"""
    return inicio1 < fin2 and inicio2 < fin1


# Reglas de Recursos Físicos y Humanos

def detectar_solapamientos_profesor(sesiones: List[SesionRef]) -> List[SolapamientoProfesor]:
    """Detecta si un profesor está asignado a dos sesiones simultáneas."""
    conflictos = []
    mapa = defaultdict(list)
    
    for s in sesiones:
        for pid in s.profesor_ids:
            mapa[(pid, s.periodo)].append(s)
            
    for (pid, _), lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    conflictos.append((s1, s2, pid))
    
    return conflictos


def detectar_solapamientos_aula(sesiones: List[SesionRef]) -> List[SolapamientoAula]:
    """Detecta si un aula tiene dos sesiones simultáneas."""
    conflictos = []
    mapa = defaultdict(list)
    
    for s in sesiones:
        if s.aula_id is not None:
            mapa[(s.aula_id, s.periodo)].append(s)
            
    for (aid, _), lista in mapa.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                if sesiones_se_solapan_temporalmente(s1, s2):
                    conflictos.append((s1, s2, aid))
    
    return conflictos


# Reglas de Grupos Docentes (Alumnos)

def detectar_solapamientos_grupos(sesiones: List[SesionRef]) -> List[SolapamientoGrupo]:
    """
    Detecta conflictos de alumno (ubicuidad).
    Cubre:
    1. Misma Asignatura: Teoría vs Práctica, o Grupo A vs Grupo A.
    2. Diferente Asignatura (mismo curso): Coherencia del plan de estudios.
    """
    conflictos = []
    mapa_curso = defaultdict(list)
    
    for s in sesiones:
        mapa_curso[(s.curso, s.periodo)].append(s)
        
    for _, lista in mapa_curso.items():
        for i in range(len(lista)):
            for j in range(i + 1, len(lista)):
                s1, s2 = lista[i], lista[j]
                
                if not sesiones_se_solapan_temporalmente(s1, s2):
                    continue
                
                if s1.mencion_ids and s2.mencion_ids:
                    set1 = set(s1.mencion_ids)
                    set2 = set(s2.mencion_ids)
                    if not set1.intersection(set2):
                        continue

                es_misma_asignatura = (s1.asignatura_id == s2.asignatura_id)
                es_conflicto = False
                motivo = ""

                if es_misma_asignatura:
                    tipo1, tipo2 = s1.tipo_grupo.upper(), s2.tipo_grupo.upper()
                    
                    if "TEORIA" in tipo1 or "TEORIA" in tipo2:
                        es_conflicto = True
                        motivo = "Incompatibilidad interna: Teoría se solapa con otra sesión."
                    else:
                        if s1.grupo_codigo == s2.grupo_codigo:
                            es_conflicto = True
                            motivo = f"Solapamiento de subgrupo idéntico ({s1.grupo_codigo})."
                else:
                    es_conflicto = True
                    motivo = "Incoherencia del Plan de Estudios (Asignaturas del mismo nivel solapadas)."

                if es_conflicto:
                    asig_comun = s1.asignatura_id if es_misma_asignatura else 0
                    conflictos.append((s1, s2, asig_comun, motivo))

    return conflictos


# Reglas de Conciliación Docente

def detectar_interferencias_conciliacion(
    sesiones: List[SesionRef],
    mapa_conciliacion: Dict[int, str],
    hora_apertura: time,
    hora_cierre: time,
    margen_normal: int,
    margen_mixto: int
) -> List[InterferenciaConciliacion]:
    """Verifica si las sesiones respetan los derechos de conciliación."""
    conflictos = []
    
    def sumar_h(t: time, h: int) -> time:
        return (datetime.combine(date.today(), t) + timedelta(hours=h)).time()
    
    def restar_h(t: time, h: int) -> time:
        return (datetime.combine(date.today(), t) - timedelta(hours=h)).time()

    limite_entrada = sumar_h(hora_apertura, margen_normal)
    limite_salida = restar_h(hora_cierre, margen_normal)
    limite_mix_am = sumar_h(hora_apertura, margen_mixto)
    limite_mix_pm = restar_h(hora_cierre, margen_mixto)

    for s in sesiones:
        if not s.slot:
            continue
        
        inicio = s.slot.hora_inicio
        fin = s.slot.hora_fin
        
        for pid in s.profesor_ids:
            tipo = mapa_conciliacion.get(pid)
            if not tipo:
                continue
            
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


# Fachada Principal

def detectar_todos_los_conflictos_basicos(
    sesiones: List[SesionRef],
    mapa_conciliacion: Dict[int, str],
    hora_apertura: time,
    hora_cierre: time,
    margen_normal: int,
    margen_mixto: int
):
    """Ejecuta todas las reglas matemáticas en orden."""
    s_aula = detectar_solapamientos_aula(sesiones)
    s_prof = detectar_solapamientos_profesor(sesiones)
    s_grupo = detectar_solapamientos_grupos(sesiones)
    s_conciliacion = detectar_interferencias_conciliacion(
        sesiones, mapa_conciliacion, 
        hora_apertura, hora_cierre, margen_normal, margen_mixto
    )
    
    return s_aula, s_prof, s_grupo, s_conciliacion