from typing import Optional, Tuple, Dict, List
from sqlalchemy.orm import Session
from rapidfuzz import process, fuzz, utils

from database.models import Asignatura, AsignaturaAlias

FUZZY_THRESHOLD = 88 # Por encima de este valor se acepta el match automáticamente (0-100)

class AsignaturaMatcher:
    """
    Servicio de resolución de entidades para Asignaturas.
    Estrategia híbrida: Cache Memoria + DB Alias + Fuzzy Matching.
    """

    def __init__(self, db: Session):
        self.db = db
        self._cargar_cache()

    def _cargar_cache(self):
        # 1. Mapa: "texto_normalizado" -> Objeto Asignatura
        self._map_lookup: Dict[str, Asignatura] = {}
        
        # 2. Lista de nombres oficiales para el algoritmo
        self._nombres_oficiales_keys: List[str] = []

        # A) Cargar Oficiales
        asignaturas = self.db.query(Asignatura).filter(Asignatura.activo == True).all()
        for asig in asignaturas:
            # utils.default_process normaliza (minusculas, trim, etc)
            key = utils.default_process(asig.nombre)
            if key:
                self._map_lookup[key] = asig
                self._nombres_oficiales_keys.append(key)

        # B) Cargar Alias
        aliases = self.db.query(AsignaturaAlias).all()
        for al in aliases:
            key = utils.default_process(al.alias)
            if key and key not in self._map_lookup:
                self._map_lookup[key] = al.asignatura

    def match(self, texto_sucio: str) -> Tuple[Optional[Asignatura], str, float]:
        """
        Retorna: (Asignatura, Metodo, Score)
        """
        if not texto_sucio:
            return None, "EMPTY", 0.0

        texto_proc = utils.default_process(texto_sucio)
        if not texto_proc:
            return None, "EMPTY_AFTER_CLEAN", 0.0

        # --- MATCH EXACTO / ALIAS DB ---
        if texto_proc in self._map_lookup:
            match_asig = self._map_lookup[texto_proc]
            es_nombre_oficial = utils.default_process(match_asig.nombre) == texto_proc
            metodo = "EXACT" if es_nombre_oficial else "ALIAS_DB"
            return match_asig, metodo, 100.0

        # --- FUZZY MATCHING ---
        # Usamos token_set_ratio que maneja bien el desorden de palabras
        resultado = process.extractOne(
            query=texto_proc,
            choices=self._nombres_oficiales_keys,
            scorer=fuzz.token_set_ratio,
            score_cutoff=50
        )

        if resultado:
            mejor_match_str, score, _ = resultado # RapidFuzz devuelve (match, score, index)
            
            if score >= FUZZY_THRESHOLD:
                return self._map_lookup[mejor_match_str], "FUZZY_AUTO", score
            
            return None, "FUZZY_LOW_CONFIDENCE", score

        return None, "NO_MATCH", 0.0

    def registrar_nuevo_alias(self, asignatura_id: int, alias_sucio: str) -> AsignaturaAlias:
        """Registra un alias validado por humano para aprendizaje futuro."""
        nuevo_alias = AsignaturaAlias(
            asignatura_id=asignatura_id,
            alias=alias_sucio,
            origen="AUTO_LEARNING"
        )
        self.db.add(nuevo_alias)
        self.db.commit()
        
        # Actualizar caché local
        key = utils.default_process(alias_sucio)
        if key:
             self._map_lookup[key] = self.db.query(Asignatura).get(asignatura_id)
             
        return nuevo_alias