import logging
import re
from typing import Optional
from sqlalchemy.orm import Session

# Intentamos importar rapidfuzz
try:
    from rapidfuzz import process, fuzz
except ImportError:
    print("❌ ERROR: 'rapidfuzz' no instalado.")
    raise

from database.models import Aula

logger = logging.getLogger(__name__)

class AulaMatcher:
    """
    Servicio para emparejar aulas usando lógica Fuzzy insensible a mayúsculas
    y tolerante a diferencias de espaciado (LSC1 vs LSC 1).
    """

    # Mantenemos el umbral en 80, que es seguro.
    MIN_SCORE_THRESHOLD = 80

    def match(self, db: Session, texto_aula: str) -> Optional[Aula]:
        if not texto_aula or len(texto_aula.strip()) < 2:
            return None

        # 1. Traer aulas
        aulas = db.query(Aula).all()
        if not aulas:
            logger.warning("⚠️ AulaMatcher: BD vacía de aulas.")
            return None

        # 2. Preparar candidatos (Normalización en origen)
        choices = {}
        for aula in aulas:
            # A) Nombre en Mayúsculas
            if aula.nombre:
                nombre_upper = aula.nombre.upper().strip()
                choices[nombre_upper] = aula
            
            # B) Código en Mayúsculas y variantes
            if aula.codigo:
                codigo_upper = aula.codigo.upper().strip()
                choices[codigo_upper] = aula
                
                # Opción Expandida: "LSC1" -> "LSC 1"
                codigo_expandido = re.sub(r'([A-Z])(\d)', r'\1 \2', codigo_upper)
                codigo_expandido = codigo_expandido.replace("-", " ").replace("_", " ")
                choices[codigo_expandido] = aula

        # 3. Normalizar Input (PDF)
        query_norm = self._normalize(texto_aula)

        # 4. Fuzzy Match
        resultado = process.extractOne(
            query=query_norm,
            choices=choices.keys(),
            scorer=fuzz.token_set_ratio
        )

        if not resultado:
            return None

        match_text, score, _ = resultado

        # --- LOGS ACTIVADOS ---
        # Solo mostramos si hay una mínima similitud (>40) para no ensuciar con ruido total
        if score > 40:
            if score >= self.MIN_SCORE_THRESHOLD:
                # ÉXITO
                logger.info(f"✅ MATCH AULA: '{query_norm}' -> '{match_text}' (Oficial: {choices[match_text].nombre}) | Score: {score}")
            else:
                # FALLO (Casi, pero no)
                logger.warning(f"❌ AULA RECHAZADA: '{query_norm}' se parece a '{match_text}' pero Score {score} < {self.MIN_SCORE_THRESHOLD}")

        if score >= self.MIN_SCORE_THRESHOLD:
            return choices[match_text]
        
        return None

    def _normalize(self, text: str) -> str:
        """Mayúsculas, sin tildes y separando números (AULA14 -> AULA 14)."""
        if not text: return ""
        text = text.upper().strip()
        
        # Quitar tildes
        replacements = (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'))
        for a, b in replacements:
            text = text.replace(a, b)
            
        # Separar números pegados
        text = re.sub(r'([A-Z])(\d)', r'\1 \2', text)
        
        return text

# Instancia Singleton
aula_matcher = AulaMatcher()