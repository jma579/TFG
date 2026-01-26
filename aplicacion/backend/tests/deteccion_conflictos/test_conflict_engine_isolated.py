import pytest
from datetime import datetime, time, date
from typing import List

# Importamos las definiciones y reglas del Core
from core.conflictos.types import (
    SesionRef, 
    SlotSemanal, 
    Intervalo
)
from core.conflictos.basic_rules import (
    sesiones_se_solapan_temporalmente,
    detectar_solapamientos_aula,
    detectar_solapamientos_profesor,
    detectar_solapamientos_grupos
)

# ============================================================================
# HELPERS / FIXTURES
# ============================================================================

def make_sesion_semanal(
    id: int, 
    dia: int, 
    h_ini: str, 
    h_fin: str, 
    profesores: List[int], 
    aula_id: int = 1,
    asignatura_id: int = 100,
    grupo_id: int = 10
) -> SesionRef:
    """Helper para crear sesiones semanales rápidas"""
    # Convertir strings "08:00" a objetos time
    t_ini = datetime.strptime(h_ini, "%H:%M").time()
    t_fin = datetime.strptime(h_fin, "%H:%M").time()
    
    return SesionRef(
        id=id,
        aula_id=aula_id,
        profesor_ids=profesores,
        asignatura_id=asignatura_id,
        grupo_id=grupo_id,
        tipo_recurrencia="SEMANAL",
        slot=SlotSemanal(dia_semana=dia, hora_inicio=t_ini, hora_fin=t_fin)
    )

def make_sesion_fechada(
    id: int, 
    dt_ini: str, 
    dt_fin: str, 
    profesores: List[int], 
    aula_id: int = 1,
    asignatura_id: int = 100,
    grupo_id: int = 10
) -> SesionRef:
    """Helper para crear sesiones fechadas (exámenes, eventos)"""
    # Convertir strings ISO a datetime
    d_ini = datetime.fromisoformat(dt_ini)
    d_fin = datetime.fromisoformat(dt_fin)
    
    return SesionRef(
        id=id,
        aula_id=aula_id,
        profesor_ids=profesores,
        asignatura_id=asignatura_id,
        grupo_id=grupo_id,
        tipo_recurrencia="FECHADA",
        intervalo=Intervalo(inicio=d_ini, fin=d_fin)
    )

# ============================================================================
# TESTS DE LÓGICA TEMPORAL (MATEMÁTICA)
# ============================================================================

def test_solapamiento_semanal_vs_semanal():
    # Caso 1: Mismo día, horas solapadas -> True
    # Lunes 10:00-12:00 vs Lunes 11:00-13:00
    s1 = make_sesion_semanal(1, 0, "10:00", "12:00", [])
    s2 = make_sesion_semanal(2, 0, "11:00", "13:00", [])
    assert sesiones_se_solapan_temporalmente(s1, s2) is True

    # Caso 2: Mismo día, horas contiguas (fin == inicio) -> False
    # Lunes 10:00-12:00 vs Lunes 12:00-14:00
    s3 = make_sesion_semanal(3, 0, "12:00", "14:00", [])
    assert sesiones_se_solapan_temporalmente(s1, s3) is False

    # Caso 3: Distinto día -> False
    # Lunes vs Martes
    s4 = make_sesion_semanal(4, 1, "10:00", "12:00", [])
    assert sesiones_se_solapan_temporalmente(s1, s4) is False


def test_solapamiento_mixto_semanal_vs_fechada():
    """Prueba crítica: Clase recurrente vs Examen puntual"""
    
    # Clase: Todos los Lunes de 10:00 a 12:00
    clase_lunes = make_sesion_semanal(1, 0, "10:00", "12:00", [])
    
    # Examen 1: Un Lunes específico (2023-10-02 es Lunes) a las 10:30 -> CONFLICTO
    examen_conflicto = make_sesion_fechada(2, "2023-10-02T10:30:00", "2023-10-02T12:30:00", [])
    
    # Examen 2: Un Martes específico (2023-10-03 es Martes) a las 10:30 -> OK
    examen_ok_dia = make_sesion_fechada(3, "2023-10-03T10:30:00", "2023-10-03T12:30:00", [])
    
    # Examen 3: Un Lunes específico pero por la tarde (15:00) -> OK
    examen_ok_hora = make_sesion_fechada(4, "2023-10-02T15:00:00", "2023-10-02T17:00:00", [])

    assert sesiones_se_solapan_temporalmente(clase_lunes, examen_conflicto) is True
    assert sesiones_se_solapan_temporalmente(clase_lunes, examen_ok_dia) is False
    assert sesiones_se_solapan_temporalmente(clase_lunes, examen_ok_hora) is False

# ============================================================================
# TESTS DE REGLAS DE NEGOCIO
# ============================================================================

def test_regla_aula_ocupada():
    """Dos sesiones en la misma aula al mismo tiempo"""
    # Aula 101, Lunes 10-12
    s1 = make_sesion_semanal(1, 0, "10:00", "12:00", [], aula_id=101)
    # Aula 101, Lunes 11-13 (Solapa)
    s2 = make_sesion_semanal(2, 0, "11:00", "13:00", [], aula_id=101)
    # Aula 102 (Distinta), Lunes 10-12
    s3 = make_sesion_semanal(3, 0, "10:00", "12:00", [], aula_id=102)

    conflictos = detectar_solapamientos_aula([s1, s2, s3])
    
    # Debe haber 1 conflicto entre s1 y s2 en aula 101
    assert len(conflictos) == 1
    c = conflictos[0]
    assert c[2] == 101 # El ID del aula conflicto
    assert 1 in (c[0], c[1])
    assert 2 in (c[0], c[1])

def test_regla_profesor_bilocacion():
    """Un profesor en dos sitios a la vez"""
    prof_id = 99
    
    # Sesion 1: Profe 99
    s1 = make_sesion_semanal(1, 0, "10:00", "12:00", [prof_id])
    # Sesion 2: Profe 99 (Solapa)
    s2 = make_sesion_semanal(2, 0, "11:00", "13:00", [prof_id])
    # Sesion 3: Otro Profe (88) a la misma hora -> No pasa nada
    s3 = make_sesion_semanal(3, 0, "10:00", "12:00", [88])

    conflictos = detectar_solapamientos_profesor([s1, s2, s3])

    assert len(conflictos) == 1
    assert conflictos[0][2] == prof_id # Conflicto del profe 99

def test_regla_asignatura_mismo_grupo():
    """Misma asignatura, MISMO grupo -> Conflicto (los alumnos no pueden dividirse)"""
    asig_mates = 500
    grupo_A = 1
    
    s1 = make_sesion_semanal(1, 0, "10:00", "12:00", [], asignatura_id=asig_mates, grupo_id=grupo_A)
    s2 = make_sesion_semanal(2, 0, "10:00", "12:00", [], asignatura_id=asig_mates, grupo_id=grupo_A)
    
    conflictos = detectar_solapamientos_grupos([s1, s2])
    assert len(conflictos) == 1
    assert conflictos[0][2] == asig_mates

def test_regla_asignatura_distinto_grupo_permitido():
    """Misma asignatura, DISTINTO grupo -> OK (Prácticas desdobladas)"""
    asig_mates = 500
    grupo_A = 1
    grupo_B = 2
    
    # Mates Grupo A en Aula 1
    s1 = make_sesion_semanal(1, 0, "10:00", "12:00", [], aula_id=1, asignatura_id=asig_mates, grupo_id=grupo_A)
    # Mates Grupo B en Aula 2 a la misma hora
    s2 = make_sesion_semanal(2, 0, "10:00", "12:00", [], aula_id=2, asignatura_id=asig_mates, grupo_id=grupo_B)
    
    conflictos = detectar_solapamientos_grupos([s1, s2])
    
    # NO debería haber conflicto de grupo, porque son grupos distintos (A y B)
    assert len(conflictos) == 0

    # OJO: Si comprobamos aulas, tampoco debería haber conflicto (Aulas 1 y 2)
    conflictos_aula = detectar_solapamientos_aula([s1, s2])
    assert len(conflictos_aula) == 0