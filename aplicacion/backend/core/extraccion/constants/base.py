
"""
Constantes base compartidas en todo el sistema académico.

Este módulo contiene las constantes fundamentales para el sistema de
evaluación de calidad, scoring y umbrales utilizados en la extracción
de PDFs académicos.
"""

# Importar enums desde core.extraccion.entities.extractor
from core.extraccion.entities.extractor import ExtractionQuality, ProcessingStatus, ErrorType


# =============================================================================
# CONSTANTES DE EVALUACIÓN DE CALIDAD COMPARTIDAS
# =============================================================================

# Pesos principales para categorías de calidad
WEIGHT_BASIC_METRICS = 0.3          # 30% - Métricas básicas de texto
WEIGHT_ACADEMIC_PATTERNS = 0.4      # 40% - Patrones académicos específicos
WEIGHT_QUALITY_INDICATORS = 0.3     # 30% - Indicadores de calidad y coherencia

# Pesos internos para métricas básicas
BASIC_WEIGHT_STRUCTURE = 0.4        # 40% - Estructura del documento
BASIC_WEIGHT_CHAR_QUALITY = 0.35    # 35% - Calidad de caracteres
BASIC_WEIGHT_WORD_QUALITY = 0.25    # 25% - Calidad de palabras

# Pesos internos para patrones académicos
ACADEMIC_WEIGHT_CODES = 0.4         # 40% - Códigos de asignatura
ACADEMIC_WEIGHT_TERMINOLOGY = 0.35  # 35% - Terminología académica
ACADEMIC_WEIGHT_SCHEDULE = 0.25     # 25% - Formatos de horario

# Pesos internos para indicadores de calidad
QUALITY_WEIGHT_COHERENCE = 0.5      # 50% - Coherencia semántica
QUALITY_WEIGHT_ERROR_ABSENCE = 0.5  # 50% - Ausencia de errores

# Umbrales para mapeo de ExtractionQuality
THRESHOLD_EXCELLENT = 0.85          # >= 85% = EXCELLENT
THRESHOLD_GOOD = 0.70               # 70-84% = GOOD
THRESHOLD_ACCEPTABLE = 0.50         # 50-69% = ACCEPTABLE
THRESHOLD_POOR = 0.30               # 30-49% = POOR
                                    # < 30% = UNUSABLE

# Bonificaciones de score
BONUS_ACADEMIC_EXCELLENCE = 0.1     # +10% por excelencia académica
BONUS_SOLID_STRUCTURE = 0.05        # +5% por estructura sólida

# Penalizaciones de score
PENALTY_HIGH_NOISE = 0.2            # -20% por alto nivel de ruido
PENALTY_CORRUPTION = 0.15           # -15% por corrupción significativa

# Umbrales para aplicar bonificaciones y penalizaciones
THRESHOLD_STRUCTURE_EXCELLENCE = 0.7     # Umbral para bonificación de estructura
THRESHOLD_HIGH_NOISE_LEVEL = 0.5         # Umbral para penalización por ruido
THRESHOLD_SIGNIFICANT_CORRUPTION = 0.1   # Umbral para penalización por corrupción
THRESHOLD_MULTIPLE_SUBJECT_CODES = 2     # Mínimo códigos para excelencia académica

# Garantías de score mínimo
MINIMUM_VIABLE_SCORE = 0.2          # Score mínimo para texto procesable

# Constantes básicas compartidas
MIN_CHARACTERS_FOR_USEFUL_TEXT = 50   # Mínimo de caracteres para considerar texto útil
MIN_CONFIDENCE = 0.3                 # Umbral mínimo de confianza global


# =============================================================================
# CONFIGURACIÓN BASE PARA PARSERS
# =============================================================================

BASE_PARSER_CONFIG = { # TODO: Ajustar según necesidades
    "min_confidence": 0.5,
    "context_radius": 80,
    "log_level": "info",
    "min_text_length": 30,  # Mínimo de caracteres para intentar parsear
    "radius": 80
    # Puedes añadir más parámetros genéricos aquí
}