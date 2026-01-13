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
    Diseñado para alto rendimiento y tolerancia a fallos tipográficos.
    """

    # Umbral de similitud para aceptar un match difuso.
    MIN_SCORE_THRESHOLD = 80

    def __init__(self, db: Session):
        """
        Inicializa el matcher y carga la caché de aulas inmediatamente.
        
        Args:
            db: Sesión de base de datos para la carga inicial.
        """
        self.db = db
        
        # Estructuras de datos en memoria (Caché)
        # Mapa inverso: Texto Normalizado -> Objeto Aula
        self._map_lookup: Dict[str, Aula] = {}
        
        # Lista de claves únicas para el motor fuzzy
        self._keys_fuzzy: List[str] = []
        
        # Carga inicial
        self.refresh_cache()

    def refresh_cache(self):
        """
        (Re)Carga todas las aulas activas en memoria.
        
        Genera índices para:
        1. Nombres oficiales normalizados ("AULA 1").
        2. Códigos oficiales normalizados ("A1").
        3. Variantes comprimidas sin espacios ("AULA1", "LSC1") para maximizar matches exactos.
        """
        logger.info("Iniciando carga de caché de Aulas...")
        
        # Reset de estructuras
        self._map_lookup = {}
        self._keys_fuzzy = []
        
        # Consulta eficiente: solo aulas activas
        aulas = self.db.query(Aula).filter(Aula.activo == True).all()
        
        count_indexed = 0
        for aula in aulas:
            # Estrategia de Variantes:
            # Indexamos el nombre tal cual y versiones "limpias" para maximizar
            # la probabilidad de un Match Exacto (O(1)).
            
            # 1. Indexar Nombre oficial
            if aula.nombre:
                self._indexar_termino(aula.nombre, aula)
                # Variante extra: Sin espacios (ej: "LSC 1" -> "LSC1")
                self._indexar_termino(aula.nombre.replace(" ", ""), aula)
            
            # 2. Indexar Código oficial
            if aula.codigo:
                self._indexar_termino(aula.codigo, aula)
                # Variante extra: Sin espacios
                self._indexar_termino(aula.codigo.replace(" ", ""), aula)
            
            count_indexed += 1

        # Preparamos la lista plana para RapidFuzz
        self._keys_fuzzy = list(self._map_lookup.keys())
        
        logger.info(
            f"AulaMatcher Cache: {count_indexed} aulas cargadas, "
            f"{len(self._keys_fuzzy)} variantes indexadas en memoria."
        )

    def _indexar_termino(self, texto: str, aula: Aula):
        """
        Normaliza e inserta un término en el mapa de búsqueda.
        """
        key = self._normalize(texto)
        
        # Filtro de calidad: ignorar claves vacías o de 1 solo caracter
        if not key or len(key) < 2: 
            return
        
        # Guardamos la referencia.
        # Nota: Si hay colisión (mismo nombre normalizado para aulas distintas),
        # sobrescribimos con la última. Asumimos unicidad en nombres de aulas.
        self._map_lookup[key] = aula

    def match(self, texto_aula: str) -> Optional[Aula]:
        """
        Busca la mejor coincidencia de aula para un texto dado.
        
        Flujo de ejecución jerárquico:
        1. Match Exacto Estándar (Rápido).
        2. Match Exacto Variante (Sin espacios, Rápido).
        3. Fuzzy Match (Lento, último recurso).
        
        Args:
            texto_aula: Texto crudo extraído del PDF (ej: "LSC-1").
            
        Returns:
            Objeto Aula encontrado o None.
        """
        if not texto_aula or len(texto_aula.strip()) < 2:
            return None

        # Usamos TU lógica de normalización original
        query_norm = self._normalize(texto_aula)
        
        # --- PASO 1: MATCH EXACTO (Optimización O(1)) ---
        # Si el texto coincide perfectamente con lo indexado, retornamos ya.
        if query_norm in self._map_lookup:
            return self._map_lookup[query_norm]

        # --- PASO 2: MATCH EXACTO VARIANTE (Solución "LSC1") ---
        # Probamos quitando espacios al input (ej: PDF trae "LSC 1", BD tiene "LSC1")
        # Como indexamos ambas versiones en refresh_cache, esto atrapa el cruce.
        query_compressed = query_norm.replace(" ", "")
        if query_compressed in self._map_lookup:
            return self._map_lookup[query_compressed]

        # --- PASO 3: FUZZY MATCH (Probabilístico) ---
        # Si no hay coincidencia exacta, usamos el algoritmo de distancia de edición.
        # Usamos token_sort_ratio para ser indiferentes al orden ("AULA 1" == "1 AULA")
        resultado = process.extractOne(
            query=query_norm,
            choices=self._keys_fuzzy,
            scorer=fuzz.token_sort_ratio, 
            score_cutoff=self.MIN_SCORE_THRESHOLD
        )

        if resultado:
            match_key, score, _ = resultado
            
            # Auditoría: Logueamos si es fuzzy para diferenciarlo de un exacto
            # (Un exacto implícito tendría score 100, pero aquí ya lo hubiéramos retornado antes)
            logger.info(
                f"🔍 Fuzzy Aula Match: '{texto_aula}' -> '{match_key}' "
                f"(Score: {score:.1f}, Oficial: {self._map_lookup[match_key].nombre})"
            )
            
            return self._map_lookup[match_key]

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalización de texto específica para aulas.
        
        Reglas (Conservadas de la versión original):
        1. Mayúsculas y eliminación de espacios extremos.
        2. Eliminación de tildes.
        3. Separación inteligente de letras y números ("AULA14" -> "AULA 14").
        """
        if not text: return ""
        
        # 1. Mayúsculas y Trim
        text = text.upper().strip()
        
        # 2. Quitar tildes
        replacements = (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'))
        for a, b in replacements:
            text = text.replace(a, b)
            
        # 3. Separar números pegados (Lógica clave)
        # Ej: "LSC1" -> "LSC 1", "AULA14" -> "AULA 14"
        text = re.sub(r'([A-Z])(\d)', r'\1 \2', text)
        
        # Limpieza adicional de espacios dobles generados por la regex
        text = " ".join(text.split())
        
        return text