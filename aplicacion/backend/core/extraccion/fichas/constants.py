# =============================================================================
# CONFIGURACIÓN BASE PARA EXTRATOR Y PARSER
# =============================================================================

DEFAULT_EXTRACTOR_CONFIG = {
    'max_file_size_mb': 10,          # Máximo 10MB (fichas y horarios son pequeños)
    'max_pages': 20,                 # Máximo 20 páginas (fichas suelen ser 1-3 páginas)
    'stop_after_n_empty_pages': 3,   # Parar después de 3 páginas vacías
    'min_alpha_ratio': 0.35,         # 35% mínimo (más permisivo para tablas/horarios)
    'max_short_words_ratio': 0.80,   # 80% máximo (códigos G111 tienen palabras cortas)
    'log_level': 'INFO',             # Nivel de logging por defecto
}

BASE_PARSER_CONFIG = { # TODO: Ajustar según necesidades
    "min_confidence": 0.5,
    "context_radius": 80,
    "log_level": "info",
    "min_text_length": 30,  # Mínimo de caracteres para intentar parsear
    "radius": 80
    # Puedes añadir más parámetros genéricos aquí
}


# =============================================================================
# CONSTANTES DE EVALUACIÓN DE CALIDAD DE LA EXTRACCION
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
# PATRONES REGEX PARA DETECCIÓN ACADÉMICA BÁSICA
# =============================================================================

# Patrones para códigos de asignaturas (específicos para tu universidad)
SUBJECT_CODE_PATTERNS = [
    r'\bG\d{2,4}\b',                    # G100, G111, G1662, etc. (patrón principal)
    r'\bG\d{2,4}[A-Z]?\b',             # G100A, G111B (con sufijo opcional)
    r'\([G]\d{2,4}\)',                  # (G111) en paréntesis
    r'\bG[\s\-\.]\d{2,4}\b',           # G-111, G.111, G 111
]

# Patrones para detectar secciones típicas de fichas
FICHA_SECTION_PATTERNS = [
    r'(?i)(denominación|nombre)\s*:',       # Nombre de asignatura
    r'(?i)(créditos|ects)\s*:',            # Créditos
    r'(?i)(carácter|tipo)\s*:',            # Tipo de asignatura
    r'(?i)(competencias?)\s*:',            # Competencias
    r'(?i)(objetivos?)\s*:',               # Objetivos
    r'(?i)(programa|temario)\s*:',         # Programa
    r'(?i)(metodología)\s*:',              # Metodología
    r'(?i)(evaluación)\s*:',               # Evaluación
    r'(?i)(bibliografía)\s*:',             # Bibliografía
]


# =============================================================================
# CONSTANTES PARA MÉTRICAS DE CALIDAD DE TEXTO NATIVO
# =============================================================================

# Ratios mínimos para considerar texto de calidad
MIN_ALPHA_RATIO = 0.6               # 60% caracteres alfabéticos mínimo
MAX_DIGIT_RATIO = 0.4               # 40% dígitos máximo
MAX_PUNCT_RATIO = 0.3               # 30% puntuación máximo
MAX_WHITESPACE_RATIO = 0.4          # 40% espacios en blanco máximo

# Longitudes mínimas para evaluación
MIN_WORD_LENGTH_AVG = 2.5           # Longitud promedio mínima de palabras
MAX_SHORT_WORDS_RATIO = 0.4         # 40% palabras cortas (<3 chars) máximo
MIN_LONG_WORDS_RATIO = 0.1          # 10% palabras largas (>6 chars) mínimo

# Patrones de corrupción común en PDFs
CORRUPTION_PATTERNS = [
    r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\"\']+',  # Caracteres extraños
    r'\s{5,}',                               # Espacios excesivos
    r'[\r\n]{3,}',                          # Saltos de línea excesivos
    r'[A-Za-z]{20,}',                       # Palabras excesivamente largas
]

# Terminología académica española específica para fichas y horarios universitarios
ACADEMIC_TERMS = [
    # Términos de asignaturas y estructura académica
    'asignatura', 'materia', 'denominación', 'curso', 'grado', 
    'créditos', 'ects', 'carácter', 'tipo',
    
    # Términos temporales
    'semestre', 'cuatrimestre', 'horario', 'calendario',
    
    # Espacios y personal
    'aula', 'sala', 'laboratorio', 'seminario', 
    'profesor', 'profesora', 'departamento', 'facultad',
    
    # Términos de evaluación y metodología
    'evaluación', 'examen', 'práctica', 'teoría', 'tutoría',
    'competencias', 'objetivos', 'programa', 'temario',
    
    # Términos específicos de fichas
    'prerrequisitos', 'bibliografía', 'metodología', 'resultados'
]

# Patrones de ruido común en PDFs académicos universitarios
NOISE_PATTERNS = [
    r'página\s+\d+',                        # Números de página
    r'©\s*\d{4}',                          # Copyright
    r'http[s]?://[^\s]+',                  # URLs
    r'\b\d{4}-\d{2}-\d{2}\b',             # Fechas ISO
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+',  # Emails
    r'Curso\s+\d{4}-\d{4}',               # Años académicos
    r'Página\s+\d+\s+de\s+\d+',           # Paginación típica
]


# =============================================================================
# CONFIGURACIÓN DE CLEANTEXT PARA PDFS ACADÉMICOS
# =============================================================================

CLEANTEXT_CONFIG = {
    'fix_unicode': True,           # Corregir caracteres Unicode malformados
    'to_ascii': False,               # NO convertir a ASCII (preservar acentos españoles)
    'lower': False,           # NO convertir a minúsculas (preservar códigos)
    'no_line_breaks': False,      # Preservar saltos de línea
    'no_phone_numbers': True,     # Remover números de teléfono
    'no_numbers': False,          # PRESERVAR números (importantes para códigos/horarios)
    'no_digits': False,           # PRESERVAR dígitos
    'no_currency_symbols': True,  # Remover símbolos de moneda
    'no_punct': False,           # PRESERVAR puntuación básica
    'lang': 'es',                # Idioma español
}


# =============================================================================
# PATRONES Y MAPAS ESPECÍFICOS PARA PARSING FICHAS ACADÉMICAS
# =============================================================================

# PATTERN_CODIGO_NOMBRE:
# Soporta: "CODIGO Y DENOMINACION : G104 ANÁLISIS FUNCIONAL" o "ASIGNATURA G104 Análisis funcional"
PATTERN_CODIGO_NOMBRE = (
    r"(?:CODI?GO\s+Y\s+DENOMINACI[ÓO]N\s*:\s*|ASIGNATURA\s+)"
    r"([A-Z]{1,2}\d{1,4})\s+([^\n\r]+)"
)

PATTERN_TITULACION = (
    r"(Grado en [^\n\r]+?)\s+"
    r"(OBLIGATORIA|OPTATIVA|B[ÁA]SICA|TRONCAL)\s+"
    r"(\d+)"
)

PATTERN_ECTS = r"(?:CR[ÉE]DITOS?\s*ECTS|ECTS)\s*:\s*([0-9]{1,2}(?:[.,][0-9]+)?)"

PATTERN_PERIODO = r"(?:SECUENCIA|PER[IÍ]ODO)\s*:\s*([A-Za-zÁÉÍÓÚÜÑ]+)"

PATTERN_NUM_CUATRIMESTRE = r"N[ºo]\s*:\s*(\d+)"

PATTERN_MODALIDAD = r"\b(OBLIGATORIA|OPTATIVA|B[ÁA]SICA|TRONCAL)\b"

PATTERN_IDIOMA = r"\b(?:Idioma|Language)\s*:\s*([A-Za-zÁÉÍÓÚÜÑ]+)"

PATTERN_ENGLISH_FRIENDLY = r"\b(?:English\s*friendly|Docencia\s+en\s+ingl[eé]s)\s*:\s*(sí|si|no|yes|true|false|1|0)\b"

# Delimita bloque profesorado entre encabezado y secciones siguientes habituales
PATTERN_PROFESORADO = r"DATOS\s+DEL\s+PROFESORADO(.*?)(?:DESGLOSE|TOTALES?|EVALUACI[ÓO]N|$)"

# Lista de sufijos o palabras clave que suelen aparecer tras el nombre del profesor y que deben eliminarse
PROFESOR_SUFIXES = [
    r'\bCSIC\b',
    r'\bCSIC N\b',
    r'\bUC\b',
    r'\bUniversidad\b',
    r'\bDpto\b',
    r'\bFacultad\b',
    r'\bInstituto\b',
    r'\bCentro\b',
    r'\bS\b',
    r'\bN\b',
    r'\bDe\b',
    r'\bDel\b',
    r'\bLa\b',
    r'\bCU\b'
]

MAP_PERIODO = {
    "Cuatrimestral": "CUATRIMESTRAL",
    "Semestral": "SEMESTRAL",
    "Anual": "ANUAL",
}

MAP_MODALIDAD = {
    "OBLIGATORIA": "OBLIGATORIA",
    "OPTATIVA": "OPTATIVA",
    "BÁSICA": "BASICA",
    "BASICA": "BASICA",
    "TRONCAL": "TRONCAL",
}

MAP_IDIOMA = {
    "Español": "ESPAÑOL",
    "Castellano": "ESPAÑOL",
    "Inglés": "INGLES",
    "English": "INGLES",
}