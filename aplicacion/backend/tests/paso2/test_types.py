import pytest
from datetime import datetime, time, timezone
from core.conflictos.types import (
    Intervalo, SlotSemanal, SesionRef, RestriccionRef,
    ParametrosDeteccion, ResultadoDeteccion
)
from constants.enums import TipoConflicto, SeveridadConflicto


def test_intervalo_valida_orden():
    start = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    itv = Intervalo(inicio=start, fin=end)
    assert itv.inicio < itv.fin

def test_intervalo_invalido_lanza_error():
    start = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        Intervalo(inicio=start, fin=end)

def test_slot_semanal_valores_validos():
    s = SlotSemanal(dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
    assert s.dia_semana == 0

def test_slot_semanal_dia_invalido():
    with pytest.raises(ValueError):
        SlotSemanal(dia_semana=7, hora_inicio=time(9, 0), hora_fin=time(11, 0))

def test_slot_semanal_orden_horas():
    with pytest.raises(ValueError):
        SlotSemanal(dia_semana=2, hora_inicio=time(12, 0), hora_fin=time(12, 0))

def test_sesion_ref_campos_minimos_y_lista_profesores():
    s = SesionRef(
        id=1,
        aula_id=10,
        profesor_ids=[5, 5, 3],
        tipo_recurrencia="SEMANAL",
        slot=SlotSemanal(dia_semana=1, hora_inicio=time(8, 0), hora_fin=time(9, 0)),
    )
    # La limpieza es “básica”: no obliga a deduplicar, pero al menos permite lista vacía
    assert isinstance(s.profesor_ids, list)

def test_restriccion_ref_campos_basicos():
    r = RestriccionRef(
        id=7, ambito="AULA", aula_id=10,
        slot=SlotSemanal(dia_semana=1, hora_inicio=time(8, 0), hora_fin=time(10, 0))
    )
    assert r.ambito == "AULA"

def test_parametros_deteccion_defaults():
    p = ParametrosDeteccion()
    assert p.incluir_solapamientos_profesor is True
    assert p.severidad_minima == SeveridadConflicto.BAJA

def test_resultado_deteccion_minimo_valido():
    r = ResultadoDeteccion(
        tipo=TipoConflicto.SOLAPAMIENTO_AULA,
        severidad=SeveridadConflicto.ALTA,
        sesion_id=1,
        descripcion="demo",
        hash_deteccion="pending"
    )
    assert r.tipo == TipoConflicto.SOLAPAMIENTO_AULA
