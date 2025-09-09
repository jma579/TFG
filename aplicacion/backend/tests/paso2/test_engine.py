from datetime import timezone, datetime
from core.conflictos.engine import ConflictDetectionEngine
from core.conflictos.types import ParametrosDeteccion, SeveridadConflicto, TipoConflicto

def test_engine_primitives_to_results_y_hashing_y_dedup():
    eng = ConflictDetectionEngine()
    params = ParametrosDeteccion()

    # primitivas simuladas (IDs ordenados)
    prof_overlaps = [(2, 5, 99)]
    aula_overlaps = [(3, 4, 88)]
    violations     = [(10, 77)]

    resultados = eng._primitives_to_results(prof_overlaps, aula_overlaps, violations, params)
    assert len(resultados) == 3

    # aplicar hashing centralizado
    resultados = eng._apply_hashing(resultados)
    hashes = [r.hash_deteccion for r in resultados]
    assert all(h and isinstance(h, str) for h in hashes)
    assert len(set(hashes)) == 3  # todos distintos

    # deduplicación (inyectamos duplicado manualmente)
    dup = resultados[0]
    resultados_dedup = eng._deduplicate_by_hash(resultados + [dup])
    assert len(resultados_dedup) == 3

def test_engine_filtrado_por_severidad_minima():
    eng = ConflictDetectionEngine()
    # Construimos resultados via primitives
    prof_overlaps = [(2, 5, 99)]   # ALTA
    aula_overlaps = [(3, 4, 88)]   # CRITICA
    violations     = [(10, 77)]    # MEDIA
    res = eng._primitives_to_results(prof_overlaps, aula_overlaps, violations, ParametrosDeteccion())
    res = eng._apply_hashing(res)

    # severidad mínima = ALTA → excluye MEDIA
    filtrados = eng._apply_filters(res, ParametrosDeteccion(severidad_minima=SeveridadConflicto.ALTA))
    assert all(r.severidad in (SeveridadConflicto.ALTA, SeveridadConflicto.CRITICA) for r in filtrados)
    assert any(r.tipo == TipoConflicto.SOLAPAMIENTO_AULA for r in filtrados)
