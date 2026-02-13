"""
Servicio de emparejamiento de Asignaturas (Entity Resolution).
"""

from typing import Optional, Tuple, Dict, List, Set
from sqlalchemy.orm import Session, joinedload
from rapidfuzz import process, fuzz
import logging

from database.models import Asignatura, Programa

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 88 
MIN_CUTOFF = 65
PROGRAMA_THRESHOLD = 85 

class AsignaturaMatcher:
    """Servicio de resolución de entidades para Asignaturas."""

    def __init__(self, db: Session):
        self.db = db
        self._map_lookup: Dict[str, List[Asignatura]] = {}
        self._keys_by_context: Dict[int, Dict[int, Set[str]]] = {}
        self._keys_global: Set[str] = set()
        
        self._programas_map: Dict[str, int] = {}
        self._programas_keys: List[str] = []
        
        self._cargar_cache()

    def _cargar_cache(self):
        """Carga masiva de Asignaturas y Programas. """
        logger.info("Cargando caché de Asignaturas y Programas...")
        
        programas = self.db.query(Programa).filter(Programa.activo == True).all()
        for prog in programas:
            key = self._normalize(prog.nombre)
            if key:
                self._programas_map[key] = prog.id
        self._programas_keys = list(self._programas_map.keys())

        asignaturas = (
            self.db.query(Asignatura)
            .filter(Asignatura.activo == True)
            .options(
                joinedload(Asignatura.aliases),
                joinedload(Asignatura.programa_asignaturas)
            )
            .all()
        )

        for asig in asignaturas:
            self._indexar_termino(asig.nombre, asig)
            for alias_obj in asig.aliases:
                self._indexar_termino(alias_obj.alias, asig)

        logger.info(f"Caché cargada: {len(asignaturas)} asignaturas y {len(programas)} programas.")

    def _indexar_termino(self, texto: str, asig: Asignatura):
        """Helper para insertar claves en los índices."""
        key = self._normalize(texto)
        if not key: return
        if key not in self._map_lookup:
            self._map_lookup[key] = []
        if asig not in self._map_lookup[key]:
            self._map_lookup[key].append(asig)
        
        self._keys_global.add(key)

        for pa in asig.programa_asignaturas:
            prog_id = pa.programa_id
            curso = pa.curso or 0
            
            if prog_id not in self._keys_by_context:
                self._keys_by_context[prog_id] = {}
            if curso not in self._keys_by_context[prog_id]:
                self._keys_by_context[prog_id][curso] = set()
                
            self._keys_by_context[prog_id][curso].add(key)
            if 0 not in self._keys_by_context[prog_id]:
                self._keys_by_context[prog_id][0] = set()
            self._keys_by_context[prog_id][0].add(key)

    def infer_program_id(self, text_plan: str) -> Optional[int]:
        """
        Intenta deducir el ID del programa a partir de un texto (título del PDF).
        Utiliza Fuzzy Matching para ser robusto ante pequeñas diferencias.
        """
        if not text_plan:
            return None
            
        query_norm = self._normalize(text_plan)
        if not query_norm:
            return None

        if query_norm in self._programas_map:
            return self._programas_map[query_norm]

        if not self._programas_keys:
            return None
            
        result = process.extractOne(
            query=query_norm,
            choices=self._programas_keys,
            scorer=fuzz.token_set_ratio, 
            score_cutoff=PROGRAMA_THRESHOLD
        )

        if result:
            match_key, score, _ = result
            prog_id = self._programas_map[match_key]
            logger.info(f"Contexto detectado: '{text_plan}' -> ID {prog_id} (Score: {score:.1f})")
            return prog_id
            
        logger.warning(f"No se pudo inferir el programa para: '{text_plan}'")
        return None

    def match(
        self, 
        texto_raw: str, 
        prog_id: Optional[int] = None, 
        curso: int = 0,
        strict_mode: bool = False
    ) -> Tuple[Optional[Asignatura], str, float]:
        """Busca la asignatura aplicando lógica de fallbacks en cascada."""
        query_norm = self._normalize(texto_raw)
        if len(query_norm) < 2:
            return None, "NO_MATCH", 0.0

        if query_norm in self._map_lookup:
            candidates = self._map_lookup[query_norm]
            best = self._resolver_ambiguedad(candidates, prog_id, curso)
            return best, "EXACT", 100.0

        search_universe: Set[str] = set()
        
        if prog_id and curso > 0:
            prog_context = self._keys_by_context.get(prog_id, {})
            search_universe = prog_context.get(curso, set())
        
        if not search_universe and prog_id:
             search_universe = self._keys_by_context.get(prog_id, {}).get(0, set())

        if not search_universe:
            search_universe = self._keys_global

        if not search_universe:
            return None, "NO_MATCH", 0.0

        result = process.extractOne(
            query=query_norm,
            choices=search_universe,
            scorer=fuzz.token_set_ratio,
            score_cutoff=MIN_CUTOFF
        )

        if result:
            match_key, score, _ = result
            candidates = self._map_lookup[match_key]
            best_asig = self._resolver_ambiguedad(candidates, prog_id, curso)

            final_threshold = FUZZY_THRESHOLD + (5 if strict_mode else 0)
            status = "FUZZY_AUTO" if score >= final_threshold else "FUZZY_LOW_CONFIDENCE"
            
            return best_asig, status, round(score, 2)

        return None, "NO_MATCH", 0.0

    def _resolver_ambiguedad(self, candidates: List[Asignatura], prog_id: Optional[int], curso: int) -> Asignatura:
        """Resuelve casos con múltiples asignaturas candidatas aplicando reglas de contexto."""
        if len(candidates) == 1: return candidates[0]
        if prog_id:
            filtrados = [a for a in candidates if any(pa.programa_id == prog_id for pa in a.programa_asignaturas)]
            if filtrados: candidates = filtrados
        if len(candidates) == 1: return candidates[0]
        if curso > 0 and prog_id:
            filtrados = [a for a in candidates if any(pa.programa_id == prog_id and pa.curso == curso for pa in a.programa_asignaturas)]
            if filtrados: return filtrados[0]
        return candidates[0]

    @staticmethod
    def _normalize(text: str) -> str:
        if not text: return ""
        text = " ".join(text.strip().upper().split())
        replacements = (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ü", "U"), ("Ñ", "N"), (".", ""), (",", ""), ("-", " "))
        for a, b in replacements: text = text.replace(a, b)
        return text