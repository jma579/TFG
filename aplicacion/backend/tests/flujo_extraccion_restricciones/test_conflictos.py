"""
Tests unitarios para la detección matemática de conflictos de restricciones.
"""

from datetime import time
from core.conflictos.types import SesionRef, RestriccionRef, SlotSemanal
from core.conflictos.basic_rules import detectar_incumplimiento_restricciones


def test_detectar_incumplimiento_restricciones_con_solape():
    """Prueba que el motor detecta correctamente un solapamiento horario."""
    
    # 1. Creamos una restricción: Profesor 100 no puede los Lunes (0) de 09:00 a 11:00
    slot_restriccion = SlotSemanal(dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    restriccion = RestriccionRef(id=1, profesor_id=100, slot=slot_restriccion)

    # 2. Creamos una sesión infractora: Profesor 100 da clase los Lunes de 10:00 a 12:00
    slot_sesion = SlotSemanal(dia_semana=0, hora_inicio=time(10, 0), hora_fin=time(12, 0))
    sesion = SesionRef(
        id=10, 
        asignatura_id=1, 
        grupo_id=1, 
        profesor_ids=[100], 
        tipo_recurrencia="SEMANAL",
        slot=slot_sesion
    )

    # 3. Ejecutamos la regla matemática
    conflictos = detectar_incumplimiento_restricciones([sesion], [restriccion])

    # 4. Verificaciones
    assert len(conflictos) == 1, "Debería haber detectado 1 conflicto"
    
    # Comprobamos que la tupla de retorno contiene los datos correctos
    s_infractora, r_incumplida, prof_id = conflictos[0]
    assert s_infractora.id == 10
    assert r_incumplida.id == 1
    assert prof_id == 100


def test_detectar_incumplimiento_restricciones_sin_falsos_positivos():
    """Prueba que el motor ignora sesiones válidas que no chocan con la restricción."""
    
    # Restricción: Profesor 100, Lunes de 09:00 a 11:00
    slot_restriccion = SlotSemanal(dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    restriccion = RestriccionRef(id=1, profesor_id=100, slot=slot_restriccion)

    # Caso 1: Mismo día, pero empieza justo cuando acaba la restricción (11:00 a 13:00)
    slot_s1 = SlotSemanal(dia_semana=0, hora_inicio=time(11, 0), hora_fin=time(13, 0))
    sesion1 = SesionRef(id=11, asignatura_id=1, grupo_id=1, profesor_ids=[100], tipo_recurrencia="SEMANAL", slot=slot_s1)

    # Caso 2: Misma hora (09:00 a 11:00), pero distinto día (Martes = 1)
    slot_s2 = SlotSemanal(dia_semana=1, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    sesion2 = SesionRef(id=12, asignatura_id=1, grupo_id=1, profesor_ids=[100], tipo_recurrencia="SEMANAL", slot=slot_s2)
    
    # Caso 3: Mismo día y hora de la restricción, pero es un profesor diferente (ID 999)
    slot_s3 = SlotSemanal(dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    sesion3 = SesionRef(id=13, asignatura_id=1, grupo_id=1, profesor_ids=[999], tipo_recurrencia="SEMANAL", slot=slot_s3)

    # Ejecutamos la regla con todas las sesiones trampa a la vez
    conflictos = detectar_incumplimiento_restricciones([sesion1, sesion2, sesion3], [restriccion])

    # Verificación
    assert len(conflictos) == 0, "No debería haber detectado ningún conflicto"