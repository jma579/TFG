from datetime import datetime, time, timezone, timedelta
from core.conflictos.types import SesionRef, RestriccionRef, SlotSemanal, Intervalo
from core.conflictos.basic_rules import (
    sesiones_se_solapan_temporalmente,
    sesion_viola_restriccion_temporal,
    agrupar_sesiones_por_profesor,
    agrupar_sesiones_por_aula,
    detectar_solapamientos_profesor,
    detectar_solapamientos_aula,
    detectar_violaciones_restriccion,
)

def _slot(d, hi, mi, hf, mf):
    return SlotSemanal(dia_semana=d, hora_inicio=time(hi, mi), hora_fin=time(hf, mf))

def _intervalo(y, m, d, hi, mi, hf, mf):
    return Intervalo(
        inicio=datetime(y, m, d, hi, mi, tzinfo=timezone.utc),
        fin=datetime(y, m, d, hf, mf, tzinfo=timezone.utc),
    )

def test_solape_slot_vs_slot_true_y_false():
    s1 = SesionRef(id=1, aula_id=10, profesor_ids=[1], tipo_recurrencia="SEMANAL", slot=_slot(0, 8, 0, 10, 0))
    s2 = SesionRef(id=2, aula_id=11, profesor_ids=[2], tipo_recurrencia="SEMANAL", slot=_slot(0, 9, 0, 11, 0))
    s3 = SesionRef(id=3, aula_id=11, profesor_ids=[2], tipo_recurrencia="SEMANAL", slot=_slot(1, 9, 0, 11, 0))
    assert sesiones_se_solapan_temporalmente(s1, s2) is True
    assert sesiones_se_solapan_temporalmente(s1, s3) is False  # distinto día
    # contiguos no solapan
    s4 = SesionRef(id=4, aula_id=10, profesor_ids=[1], tipo_recurrencia="SEMANAL", slot=_slot(0, 10, 0, 12, 0))
    assert sesiones_se_solapan_temporalmente(s1, s4) is False

def test_solape_intervalo_vs_intervalo():
    a = SesionRef(id=1, aula_id=10, profesor_ids=[1], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,8,0,10,0))
    b = SesionRef(id=2, aula_id=11, profesor_ids=[2], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,9,0,11,0))
    c = SesionRef(id=3, aula_id=11, profesor_ids=[2], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,10,0,12,0))
    assert sesiones_se_solapan_temporalmente(a, b) is True
    assert sesiones_se_solapan_temporalmente(a, c) is False  # contiguo: fin==inicio

def test_agrupacion_por_profesor_soporta_varios_profesores_en_una_sesion():
    s1 = SesionRef(id=1, aula_id=10, profesor_ids=[1,2], tipo_recurrencia="SEMANAL", slot=_slot(0,8,0,9,0))
    s2 = SesionRef(id=2, aula_id=10, profesor_ids=[2],   tipo_recurrencia="SEMANAL", slot=_slot(0,9,0,10,0))
    grupos = agrupar_sesiones_por_profesor([s1, s2])
    assert set(grupos.keys()) == {1, 2}
    assert any(s.id == 1 for s in grupos[1])
    assert any(s.id == 1 for s in grupos[2]) and any(s.id == 2 for s in grupos[2])

def test_agrupacion_por_aula_basica():
    s1 = SesionRef(id=1, aula_id=10, profesor_ids=[1], tipo_recurrencia="SEMANAL", slot=_slot(0,8,0,9,0))
    s2 = SesionRef(id=2, aula_id=10, profesor_ids=[2], tipo_recurrencia="SEMANAL", slot=_slot(0,9,0,10,0))
    s3 = SesionRef(id=3, aula_id=11, profesor_ids=[3], tipo_recurrencia="SEMANAL", slot=_slot(0,9,0,10,0))
    grupos = agrupar_sesiones_por_aula([s1, s2, s3])
    assert set(grupos.keys()) == {10, 11}
    assert len(grupos[10]) == 2 and len(grupos[11]) == 1

def test_detectar_solapamientos_profesor_devuelve_ids_ordenados_sin_duplicados():
    # profesor 9 está en s1 y s2 con solape; además s3 no solapa
    s1 = SesionRef(id=5, aula_id=10, profesor_ids=[9], tipo_recurrencia="SEMANAL", slot=_slot(0,8,0,10,0))
    s2 = SesionRef(id=2, aula_id=11, profesor_ids=[9], tipo_recurrencia="SEMANAL", slot=_slot(0,9,0,11,0))
    s3 = SesionRef(id=7, aula_id=11, profesor_ids=[9], tipo_recurrencia="SEMANAL", slot=_slot(0,11,0,12,0))
    res = detectar_solapamientos_profesor([s1, s2, s3])
    assert len(res) == 1
    (sid1, sid2, prof) = res[0]
    assert (sid1, sid2) == tuple(sorted((5, 2)))
    assert prof == 9

def test_detectar_solapamientos_aula_devuelve_ids_ordenados_sin_duplicados():
    s1 = SesionRef(id=5, aula_id=99, profesor_ids=[1], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,8,0,10,0))
    s2 = SesionRef(id=2, aula_id=99, profesor_ids=[2], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,9,0,11,0))
    s3 = SesionRef(id=7, aula_id=98, profesor_ids=[2], tipo_recurrencia="FECHADA", intervalo=_intervalo(2025,1,1,9,0,11,0))
    res = detectar_solapamientos_aula([s1, s2, s3])
    assert len(res) == 1
    (sid1, sid2, aula_id) = res[0]
    assert (sid1, sid2) == tuple(sorted((5, 2)))
    assert aula_id == 99

def test_violacion_restriccion_verifica_ambito_y_solape():
    # Restricción de PROFESOR afecta a prof id=3 con slot solapado
    s = SesionRef(id=1, aula_id=10, profesor_ids=[3], tipo_recurrencia="SEMANAL", slot=_slot(2, 9, 0, 11, 0))
    r_prof = RestriccionRef(id=50, ambito="PROFESOR", profesor_id=3, slot=_slot(2, 10, 0, 12, 0))
    r_aula = RestriccionRef(id=51, ambito="AULA", aula_id=10, slot=_slot(3, 10, 0, 12, 0))
    assert sesion_viola_restriccion_temporal(s, r_prof) is True   # mismo día, solapa con el prof 3
    assert sesion_viola_restriccion_temporal(s, r_aula) is False  # día distinto → no solapa
    # Además: restricción de aula en mismo día
    r_aula2 = RestriccionRef(id=52, ambito="AULA", aula_id=10, slot=_slot(2, 10, 0, 12, 0))
    assert sesion_viola_restriccion_temporal(s, r_aula2) is True

def test_detectar_violaciones_restriccion_devuelve_pares_id():
    s = SesionRef(id=1, aula_id=10, profesor_ids=[3], tipo_recurrencia="SEMANAL", slot=_slot(2, 9, 0, 11, 0))
    r = RestriccionRef(id=50, ambito="PROFESOR", profesor_id=3, slot=_slot(2, 10, 0, 12, 0))
    res = detectar_violaciones_restriccion([s], [r])
    assert res == [(1, 50)]
