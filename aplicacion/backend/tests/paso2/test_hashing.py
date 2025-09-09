from datetime import datetime, time, timezone
from core.conflictos.types import (
    ResultadoDeteccion
)
from constants.enums import TipoConflicto, SeveridadConflicto
from core.conflictos.hashing import generar_hash_conflicto


def _conflict_prof(s1: int, s2: int, prof: int):
    return ResultadoDeteccion(
        tipo=TipoConflicto.SOLAPAMIENTO_PROFESOR,
        severidad=SeveridadConflicto.ALTA,
        sesion_id=s1,
        sesion_2_id=s2,
        profesor_id=prof,
        descripcion="",
        hash_deteccion="",
        datos_contexto={"temporal_data": {"demo": True}}
    )

def test_hash_determinista_y_longitud():
    r = _conflict_prof(2, 5, 99)
    h1 = generar_hash_conflicto(r)
    h2 = generar_hash_conflicto(r)
    assert h1 == h2
    assert len(h1) >= 16  # por configuración actual ~20 hex

def test_hash_invariante_al_orden_de_sesiones():
    r1 = _conflict_prof(2, 5, 99)
    r2 = _conflict_prof(5, 2, 99)
    assert generar_hash_conflicto(r1) == generar_hash_conflicto(r2)

def test_hash_cambia_si_profesor_cambia():
    r1 = _conflict_prof(2, 5, 99)
    r2 = _conflict_prof(2, 5, 100)
    assert generar_hash_conflicto(r1) != generar_hash_conflicto(r2)

def test_hash_cambia_por_tipo_distinto():
    a = ResultadoDeteccion(
        tipo=TipoConflicto.SOLAPAMIENTO_AULA,
        severidad=SeveridadConflicto.CRITICA,
        sesion_id=10,
        sesion_2_id=11,
        aula_id=3,
        descripcion="",
        hash_deteccion="",
        datos_contexto={}
    )
    b = ResultadoDeteccion(
        tipo=TipoConflicto.VIOLACION_RESTRICCION,
        severidad=SeveridadConflicto.MEDIA,
        sesion_id=10,
        restriccion_id=77,
        descripcion="",
        hash_deteccion="",
        datos_contexto={}
    )
    assert generar_hash_conflicto(a) != generar_hash_conflicto(b)
