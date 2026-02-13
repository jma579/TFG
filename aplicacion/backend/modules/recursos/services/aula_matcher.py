"""
Servicio de emparejamiento de Aulas (Entity Resolution).

Responsabilidades:
- Identificar el aula de la base de datos que corresponde a un texto extraído del PDF.
- Manejar variaciones comunes de escritura (espacios, guiones, ceros a la izquierda).
- Optimizar el rendimiento mediante caché en memoria y estrategias de búsqueda jerárquica.

Estrategia Técnica:
1. Cache Singleton: Carga masiva al inicio para evitar N+1 consultas a BD.
2. Match Exacto (O(1)): Búsqueda instantánea en hashmap (incluyendo variantes sin espacios).
3. Fuzzy Match (O(N)): Algoritmo probabilístico como último recurso.
"""

import logging
import re
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from rapidfuzz import process, fuzz

from database.models import Aula

logger = logging.getLogger(__name__)


class AulaMatcher:
    """
    Motor de resolución de entidades para Aulas.
    """

    MIN_SCORE_THRESHOLD = 80

    def __init__(self, db: Session):
        """Inicializa el matcher y carga la caché de aulas."""
        self.db = db
        
        self._map_lookup: Dict[str, Aula] = {}
        self._keys_fuzzy: List[str] = []
        
        self._cached_aulas: List[Aula] = []
        
        self.refresh_cache()

    def refresh_cache(self):
        """Carga masiva de aulas en memoria."""
        logger.info("Iniciando carga de caché de Aulas...")
        
        self._map_lookup = {}
        self._keys_fuzzy = []
        self._cached_aulas = []
        
        aulas = self.db.query(Aula).filter(Aula.activo == True).all()
        self._cached_aulas = aulas # Guardamos la lista pura
        
        count_indexed = 0
        for aula in aulas:
            if aula.nombre:
                self._indexar_termino(aula.nombre, aula)
                self._indexar_termino(aula.nombre.replace(" ", ""), aula)
            
            if aula.codigo:
                self._indexar_termino(aula.codigo, aula)
                self._indexar_termino(aula.codigo.replace(" ", ""), aula)
            
            count_indexed += 1

        self._keys_fuzzy = list(self._map_lookup.keys())
        
        logger.info(
            f"AulaMatcher Cache: {count_indexed} aulas cargadas, "
            f"{len(self._keys_fuzzy)} variantes indexadas."
        )

    def _indexar_termino(self, texto: str, aula: Aula):
        key = self._normalize(texto)
        if not key or len(key) < 2: return
        self._map_lookup[key] = aula

    def match(self, texto_aula: str) -> Optional[Aula]:
        """
        Busca la mejor coincidencia de aula.
        Jerarquía: Exacto -> Variante -> Sufijo Código -> Fuzzy.
        """
        if not texto_aula or len(texto_aula.strip()) < 2:
            return None

        query_norm = self._normalize(texto_aula)
        
        if query_norm in self._map_lookup:
            return self._map_lookup[query_norm]

        query_compressed = query_norm.replace(" ", "")
        if query_compressed in self._map_lookup:
            return self._map_lookup[query_compressed]

        query_alnum = "".join(filter(str.isalnum, query_norm)).upper()
        
        if len(query_alnum) >= 2:
            for aula in self._cached_aulas:
                if not aula.codigo: continue
                
                code_alnum = "".join(filter(str.isalnum, aula.codigo)).upper()
                
                if code_alnum.endswith(query_alnum):
                    logger.info(
                        f"Smart Suffix Match: '{texto_aula}' coincide con final de código '{aula.codigo}'"
                    )
                    return aula

        resultado = process.extractOne(
            query=query_norm,
            choices=self._keys_fuzzy,
            scorer=fuzz.token_sort_ratio, 
            score_cutoff=self.MIN_SCORE_THRESHOLD
        )

        if resultado:
            match_key, score, _ = resultado
            logger.info(
                f"Fuzzy Aula Match: '{texto_aula}' -> '{match_key}' (Score: {score:.1f})"
            )
            return self._map_lookup[match_key]

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        if not text: return ""
        text = text.upper().strip()
        replacements = (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'))
        for a, b in replacements:
            text = text.replace(a, b)
        text = re.sub(r'([A-Z])(\d)', r'\1 \2', text)
        text = " ".join(text.split())
        return text