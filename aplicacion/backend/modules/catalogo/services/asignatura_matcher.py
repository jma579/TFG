from typing import Optional, Tuple, Dict, List, Set
from sqlalchemy.orm import Session, joinedload
from rapidfuzz import process, fuzz, utils
import re

# 👇 AÑADIDO: Importamos ProgramaAsignatura
from database.models import Asignatura, AsignaturaAlias, Programa, ProgramaAsignatura

FUZZY_THRESHOLD = 88 

class AsignaturaMatcher:
    """
    Servicio de resolución de entidades inteligente.
    Estrategia: Filtrado en cascada (Programa -> Curso -> Periodo) + Fuzzy Match.
    """

    def __init__(self, db: Session):
        self.db = db
        self._cargar_cache()

    def _cargar_cache(self):
        # Mapa Global
        self._map_lookup: Dict[str, List[Asignatura]] = {}
        
        # Índice Jerárquico: programa_id -> curso (int) -> Set de claves
        self._keys_by_context: Dict[int, Dict[int, Set[str]]] = {}
        
        self._keys_global: Set[str] = set()

        self._programs_cache: List[Programa] = self.db.query(Programa).filter(Programa.activo == True).all()

        # 1. Cargar Asignaturas con relación a Programas y Curso
        asignaturas = (
            self.db.query(Asignatura)
            .options(
                joinedload(Asignatura.programa_asignaturas)
                # 👇 CORREGIDO: Usamos la clase ProgramaAsignatura en lugar del string "programa"
                .joinedload(ProgramaAsignatura.programa) 
            )
            .filter(Asignatura.activo == True)
            .all()
        )
        
        for asig in asignaturas:
            key = utils.default_process(asig.nombre)
            if not key: continue
            
            self._add_to_lookup(key, asig)
            self._keys_global.add(key)
            
            # Indexar por contexto (Programa y Curso)
            for pa in asig.programa_asignaturas:
                prog_id = pa.programa_id
                curso = pa.curso if pa.curso else 0
                
                self._add_to_context_index(prog_id, curso, key)
                self._add_to_context_index(prog_id, 0, key)

        # 2. Cargar Alias
        aliases = (
            self.db.query(AsignaturaAlias)
            .options(
                joinedload(AsignaturaAlias.asignatura)
                .joinedload(Asignatura.programa_asignaturas)
            )
            .all()
        )
        for al in aliases:
            key = utils.default_process(al.alias)
            if not key: continue
            
            self._add_to_lookup(key, al.asignatura)
            self._keys_global.add(key)

            for pa in al.asignatura.programa_asignaturas:
                prog_id = pa.programa_id
                curso = pa.curso if pa.curso else 0
                
                self._add_to_context_index(prog_id, curso, key)
                self._add_to_context_index(prog_id, 0, key)

    def _add_to_lookup(self, key: str, asig: Asignatura):
        if key not in self._map_lookup:
            self._map_lookup[key] = []
        if asig not in self._map_lookup[key]:
            self._map_lookup[key].append(asig)

    def _add_to_context_index(self, prog_id: int, curso: int, key: str):
        if prog_id not in self._keys_by_context:
            self._keys_by_context[prog_id] = {}
        if curso not in self._keys_by_context[prog_id]:
            self._keys_by_context[prog_id][curso] = set()
        
        self._keys_by_context[prog_id][curso].add(key)

    def _resolve_program_strict(self, context_text: str) -> Optional[int]:
        if not context_text: return None
        ctx_norm = utils.default_process(context_text)
        if not ctx_norm: return None

        mejor_candidato = None
        max_longitud = 0

        for p in self._programs_cache:
            p_norm = utils.default_process(p.nombre)
            if not p_norm: continue
            if p_norm in ctx_norm:
                if len(p_norm) > max_longitud:
                    max_longitud = len(p_norm)
                    mejor_candidato = p.id
        return mejor_candidato

    def _resolve_periodo_id(self, context_text: str) -> int:
        if not context_text: return 0
        norm = utils.default_process(context_text)
        tiene_1 = "primer" in norm or "1c" in norm or "semestre 1" in norm or "cuatrimestre 1" in norm
        tiene_2 = "segundo" in norm or "2c" in norm or "semestre 2" in norm or "cuatrimestre 2" in norm
        if tiene_1 and not tiene_2: return 1
        if tiene_2 and not tiene_1: return 2
        return 0

    def _resolve_curso(self, curso_text: str) -> int:
        if not curso_text: return 0
        norm = utils.default_process(curso_text)
        if "primer" in norm or "1" in norm: return 1
        if "segundo" in norm or "2" in norm: return 2
        if "tercer" in norm or "3" in norm: return 3
        if "cuarto" in norm or "4" in norm: return 4
        if "quinto" in norm or "5" in norm: return 5
        return 0

    def _is_period_compatible(self, asig_periodo_enum, target_period_id: int) -> bool:
        if target_period_id == 0: return True
        p_str = str(asig_periodo_enum).upper()
        if "ANUAL" in p_str: return True
        if target_period_id == 1: return "PRIMER" in p_str or "1" in p_str
        if target_period_id == 2: return "SEGUNDO" in p_str or "2" in p_str
        return True

    def _filter_candidates_by_period(self, candidates_keys: Set[str], period_id: int) -> List[str]:
        if period_id == 0: return list(candidates_keys)
        filtered = []
        for key in candidates_keys:
            asigs = self._map_lookup.get(key, [])
            for a in asigs:
                if self._is_period_compatible(a.periodo, period_id):
                    filtered.append(key)
                    break 
        return filtered

    def match(self, texto_sucio: str, plan_context: str = None, periodo_context: str = None, curso_context: str = None) -> Tuple[Optional[Asignatura], str, float]:
        if not texto_sucio: return None, "EMPTY", 0.0
        texto_proc = utils.default_process(texto_sucio)
        if not texto_proc: return None, "EMPTY_AFTER_CLEAN", 0.0

        prog_id = self._resolve_program_strict(plan_context)
        period_id = self._resolve_periodo_id(periodo_context)
        curso_id = self._resolve_curso(curso_context)
        
        if prog_id and prog_id in self._keys_by_context:
            return self._match_with_full_context(texto_proc, prog_id, period_id, curso_id)
        else:
            return self._match_global(texto_proc)

    def _match_with_full_context(self, texto_proc: str, prog_id: int, period_id: int, curso_id: int) -> Tuple[Optional[Asignatura], str, float]:
        candidates_set = set()
        if curso_id > 0 and curso_id in self._keys_by_context[prog_id]:
             candidates_set = self._keys_by_context[prog_id][curso_id]
        
        if not candidates_set:
            candidates_set = self._keys_by_context[prog_id].get(0, set())

        candidates = self._filter_candidates_by_period(candidates_set, period_id)

        if not candidates and candidates_set:
             candidates = list(candidates_set)

        if texto_proc in candidates:
            asig = self._get_best_candidate(texto_proc, prog_id, period_id, curso_id)
            if asig:
                es_oficial = utils.default_process(asig.nombre) == texto_proc
                return asig, "EXACT" if es_oficial else "ALIAS_DB", 100.0

        search_space = candidates
        res = process.extractOne(
            query=texto_proc,
            choices=search_space,
            scorer=fuzz.token_set_ratio,
            score_cutoff=60 
        )

        if res:
            match_key, score, _ = res
            if score >= FUZZY_THRESHOLD - 5: 
                asig = self._get_best_candidate(match_key, prog_id, period_id, curso_id)
                return asig, "FUZZY_AUTO", score
            
            asig = self._get_best_candidate(match_key, prog_id, period_id, curso_id)
            return asig, "FUZZY_LOW_CONFIDENCE", score

        return self._match_global(texto_proc, strict_mode=True)

    def _match_global(self, texto_proc: str, strict_mode: bool = False) -> Tuple[Optional[Asignatura], str, float]:
        candidates = list(self._keys_global)

        if texto_proc in self._keys_global:
            asig = self._get_best_candidate(texto_proc, None, 0, 0)
            es_oficial = utils.default_process(asig.nombre) == texto_proc
            return asig, "EXACT" if es_oficial else "ALIAS_DB", 100.0

        res = process.extractOne(
            query=texto_proc,
            choices=candidates,
            scorer=fuzz.token_set_ratio,
            score_cutoff=50
        )

        if res:
            match_key, score, _ = res
            asig = self._get_best_candidate(match_key, None, 0, 0)
            threshold = FUZZY_THRESHOLD if not strict_mode else FUZZY_THRESHOLD + 5
            status = "FUZZY_AUTO" if score >= threshold else "FUZZY_LOW_CONFIDENCE"
            return asig, status, score

        return None, "NO_MATCH", 0.0

    def _get_best_candidate(self, key: str, prog_id: Optional[int], period_id: int, curso_id: int) -> Optional[Asignatura]:
        candidates = self._map_lookup.get(key, [])
        if not candidates: return None
        
        filtered = []
        if prog_id:
            for asig in candidates:
                for pa in asig.programa_asignaturas:
                    if pa.programa_id == prog_id:
                        filtered.append(asig)
                        break
        else:
            filtered = candidates
        
        if not filtered: return candidates[0]
        
        filtered_by_curso = []
        if curso_id > 0:
            for asig in filtered:
                 for pa in asig.programa_asignaturas:
                     if pa.programa_id == prog_id and pa.curso == curso_id:
                         filtered_by_curso.append(asig)
                         break
        
        candidates_level_2 = filtered_by_curso if filtered_by_curso else filtered

        if period_id > 0:
            for asig in candidates_level_2:
                if self._is_period_compatible(asig.periodo, period_id):
                    return asig
        
        return candidates_level_2[0]