"""
Constantes de evaluación de calidad para extracción de PDFs académicos.
"""

# Pesos principales para categorías de calidad
WEIGHT_BASIC_METRICS = 0.3
WEIGHT_ACADEMIC_PATTERNS = 0.4
WEIGHT_QUALITY_INDICATORS = 0.3

# Pesos internos para métricas básicas
BASIC_WEIGHT_STRUCTURE = 0.4
BASIC_WEIGHT_CHAR_QUALITY = 0.35
BASIC_WEIGHT_WORD_QUALITY = 0.25

# Pesos internos para patrones académicos
ACADEMIC_WEIGHT_CODES = 0.4
ACADEMIC_WEIGHT_TERMINOLOGY = 0.35
ACADEMIC_WEIGHT_SCHEDULE = 0.25

# Pesos internos para indicadores de calidad
QUALITY_WEIGHT_COHERENCE = 0.5
QUALITY_WEIGHT_ERROR_ABSENCE = 0.5

# Umbrales para mapeo de ExtractionQuality
THRESHOLD_EXCELLENT = 0.85          # >= 85% = EXCELLENT
THRESHOLD_GOOD = 0.70               # 70-84% = GOOD
THRESHOLD_ACCEPTABLE = 0.50         # 50-69% = ACCEPTABLE
THRESHOLD_POOR = 0.30               # 30-49% = POOR
                                    # < 30% = UNUSABLE

# Bonificaciones de score
BONUS_ACADEMIC_EXCELLENCE = 0.1
BONUS_SOLID_STRUCTURE = 0.05

# Penalizaciones de score
PENALTY_HIGH_NOISE = 0.2
PENALTY_CORRUPTION = 0.15

# Umbrales para aplicar bonificaciones y penalizaciones
THRESHOLD_STRUCTURE_EXCELLENCE = 0.7
THRESHOLD_HIGH_NOISE_LEVEL = 0.5
THRESHOLD_SIGNIFICANT_CORRUPTION = 0.1
THRESHOLD_MULTIPLE_SUBJECT_CODES = 2

# Garantías de score mínimo
MINIMUM_VIABLE_SCORE = 0.2

# Constantes básicas compartidas
MIN_CHARACTERS_FOR_USEFUL_TEXT = 50
MIN_CONFIDENCE = 0.3