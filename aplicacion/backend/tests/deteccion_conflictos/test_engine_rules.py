import pytest
from datetime import time, datetime
from typing import List

# Ajusta los imports según tu estructura de carpetas real
from core.conflictos.engine import ConflictDetectionEngine
from core.conflictos.types import SesionRef, SlotSemanal
from constants.enums import (
    TipoConflicto, 
    SeveridadConflicto, 
    TipoConciliacion,
    HORA_APERTURA_CENTRO,
    HORA_CIERRE_CENTRO
)

# ============================================================================
#  HELPERS PARA GENERAR DATOS DE PRUEBA
# ============================================================================

def create_slot(dia: int, start_h: int, end_h: int) -> SlotSemanal:
    return SlotSemanal(
        dia_semana=dia,
        hora_inicio=time(start_h, 0),
        hora_fin=time(end_h, 0)
    )

def create_session(
    id: int, 
    profesores: List[int], 
    aula_id: int = None, 
    asignatura_id: int = 100,
    grupo_id: int = 10,
    curso: int = 1,
    tipo_grupo: str = "TEORIA",
    codigo_grupo: str = "UNICO",
    menciones: List[int] = None,
    dia: int = 0, # 0 = Lunes
    start: int = 9, 
    end: int = 11
) -> SesionRef:
    return SesionRef(
        id=id,
        aula_id=aula_id,
        profesor_ids=profesores,
        asignatura_id=asignatura_id,
        grupo_id=grupo_id,
        curso=curso,
        tipo_grupo=tipo_grupo,
        grupo_codigo=codigo_grupo,
        mencion_ids=menciones or [],
        tipo_recurrencia="SEMANAL",
        slot=create_slot(dia, start, end),
        intervalo=None
    )

@pytest.fixture
def engine():
    return ConflictDetectionEngine()

# ============================================================================
#  TESTS
# ============================================================================

def test_solapamiento_aula_critico(engine):
    # Curso 1 vs Curso 2 para evitar conflicto de grupos y probar solo Aula
    s1 = create_session(id=1, profesores=[1], aula_id=101, curso=1, start=9, end=11)
    s2 = create_session(id=2, profesores=[2], aula_id=101, curso=2, start=10, end=12)

    resultados = engine._execute_detection([s1, s2], {})
    
    assert len(resultados) == 1
    c = resultados[0]
    assert c.tipo == TipoConflicto.SOLAPAMIENTO_AULA
    assert c.severidad == SeveridadConflicto.CRITICO
    assert c.aula_id == 101

def test_solapamiento_profesor_critico_unico_docente(engine):
    # Curso 1 vs Curso 2 para aislar la prueba de Profesor
    s1 = create_session(id=1, profesores=[99], curso=1, start=9, end=11)
    s2 = create_session(id=2, profesores=[99], curso=2, start=9, end=11)

    resultados = engine._execute_detection([s1, s2], {})

    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.SOLAPAMIENTO_PROFESOR
    assert resultados[0].severidad == SeveridadConflicto.CRITICO

def test_solapamiento_profesor_no_bloqueante_codocencia(engine):
    # Curso 1 vs Curso 2
    s1 = create_session(id=1, profesores=[99, 100], curso=1, start=9, end=11)
    s2 = create_session(id=2, profesores=[99], curso=2, start=9, end=11)

    resultados = engine._execute_detection([s1, s2], {})

    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.SOLAPAMIENTO_PROFESOR
    assert resultados[0].severidad == SeveridadConflicto.NO_BLOQUEANTE

def test_solapamiento_grupo_mismo_subgrupo(engine):
    # Aquí SÍ queremos probar el grupo, así que mantenemos mismo curso y asignatura
    s1 = create_session(id=1, profesores=[], asignatura_id=50, tipo_grupo="PRACTICA", codigo_grupo="A", start=9, end=11)
    s2 = create_session(id=2, profesores=[], asignatura_id=50, tipo_grupo="PRACTICA", codigo_grupo="A", start=10, end=12)

    resultados = engine._execute_detection([s1, s2], {})
    
    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.SOLAPAMIENTO_GRUPO

def test_no_conflicto_desdoble_valido(engine):
    s1 = create_session(id=1, profesores=[], asignatura_id=50, tipo_grupo="PRACTICA", codigo_grupo="A", start=9, end=11)
    s2 = create_session(id=2, profesores=[], asignatura_id=50, tipo_grupo="PRACTICA", codigo_grupo="B", start=9, end=11)

    resultados = engine._execute_detection([s1, s2], {})
    assert len(resultados) == 0

def test_coherencia_plan_mismo_curso(engine):
    # Asig 100 y Asig 200, ambas de curso 1 -> Conflicto de Plan
    s1 = create_session(id=1, profesores=[], asignatura_id=100, curso=1, start=9, end=11)
    s2 = create_session(id=2, profesores=[], asignatura_id=200, curso=1, start=10, end=12)

    resultados = engine._execute_detection([s1, s2], {})

    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.SOLAPAMIENTO_GRUPO

def test_menciones_disjuntas_no_conflicto(engine):
    # Menciones distintas evitan el conflicto
    s1 = create_session(id=1, profesores=[], asignatura_id=100, curso=4, menciones=[1], start=9, end=11)
    s2 = create_session(id=2, profesores=[], asignatura_id=200, curso=4, menciones=[2], start=9, end=11)

    resultados = engine._execute_detection([s1, s2], {})
    assert len(resultados) == 0

def test_conciliacion_entrada_tardia(engine):
    s1 = create_session(id=1, profesores=[500], start=9, end=11)
    mapa_conciliacion = {500: TipoConciliacion.ENTRADA_TARDIA.value}

    resultados = engine._execute_detection([s1], mapa_conciliacion)

    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.INTERFERENCIA_CONCILIACION
    assert resultados[0].profesor_id == 500

def test_conciliacion_respetada(engine):
    s1 = create_session(id=1, profesores=[500], start=11, end=13)
    mapa_conciliacion = {500: TipoConciliacion.ENTRADA_TARDIA.value}
    
    resultados = engine._execute_detection([s1], mapa_conciliacion)
    assert len(resultados) == 0

def test_conciliacion_mixta_salida(engine):
    s1 = create_session(id=1, profesores=[600], start=19, end=21)
    mapa_conciliacion = {600: TipoConciliacion.MIXTA.value}
    
    resultados = engine._execute_detection([s1], mapa_conciliacion)

    assert len(resultados) == 1
    assert resultados[0].tipo == TipoConflicto.INTERFERENCIA_CONCILIACION

def test_deduplicacion_y_hashing(engine):
    # Curso 1 vs Curso 2 para evitar conflicto de grupo extra
    s1 = create_session(id=1, profesores=[], aula_id=99, curso=1, start=9, end=11)
    s2 = create_session(id=2, profesores=[], aula_id=99, curso=2, start=9, end=11)

    resultados = engine._execute_detection([s1, s2], {})
    
    assert len(resultados) == 1
    hash_original = resultados[0].hash_deteccion
    assert hash_original is not None

    resultados_inv = engine._execute_detection([s2, s1], {})
    assert len(resultados_inv) == 1
    assert resultados_inv[0].hash_deteccion == hash_original

def test_limites_temporales_estrictos(engine):
    # Curso 1 vs Curso 2
    s1 = create_session(id=1, aula_id=1, profesores=[], curso=1, start=9, end=10)
    s2 = create_session(id=2, aula_id=1, profesores=[], curso=2, start=10, end=11)

    resultados = engine._execute_detection([s1, s2], {})
    assert len(resultados) == 0