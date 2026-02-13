"""
Configuración y constantes para extracción y parsing de fichas académicas.
"""

# Configuración del extractor
DEFAULT_EXTRACTOR_CONFIG = {
    'max_file_size_mb': 10,
    'max_pages': 20,
    'stop_after_n_empty_pages': 3,
    'min_alpha_ratio': 0.35,
    'max_short_words_ratio': 0.80,
    'log_level': 'INFO',
}

# Configuración del parser
BASE_PARSER_CONFIG = {
    "min_confidence": 0.5,
    "context_radius": 80,
    "log_level": "info",
    "min_text_length": 30,
    "radius": 80
}

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
THRESHOLD_EXCELLENT = 0.85
THRESHOLD_GOOD = 0.70
THRESHOLD_ACCEPTABLE = 0.50
THRESHOLD_POOR = 0.30

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

# Patrones para códigos de asignaturas
SUBJECT_CODE_PATTERNS = [
    r'\bG\d{2,4}\b',
    r'\bG\d{2,4}[A-Z]?\b',
    r'\([G]\d{2,4}\)',
    r'\bG[\s\-\.]\d{2,4}\b',
]

# Patrones para secciones de fichas
FICHA_SECTION_PATTERNS = [
    r'(?i)(denominación|nombre)\s*:',
    r'(?i)(créditos|ects)\s*:',
    r'(?i)(carácter|tipo)\s*:',
    r'(?i)(competencias?)\s*:',
    r'(?i)(objetivos?)\s*:',
    r'(?i)(programa|temario)\s*:',
    r'(?i)(metodología)\s*:',
    r'(?i)(evaluación)\s*:',
    r'(?i)(bibliografía)\s*:',
]

# Métricas de calidad de texto
MIN_ALPHA_RATIO = 0.6
MAX_DIGIT_RATIO = 0.4
MAX_PUNCT_RATIO = 0.3
MAX_WHITESPACE_RATIO = 0.4

MIN_WORD_LENGTH_AVG = 2.5
MAX_SHORT_WORDS_RATIO = 0.4
MIN_LONG_WORDS_RATIO = 0.1

# Patrones de corrupción común en PDFs
CORRUPTION_PATTERNS = [
    r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\"\']+',
    r'\s{5,}',
    r'[\r\n]{3,}',
    r'[A-Za-z]{20,}',
]

# Terminología académica española
ACADEMIC_TERMS = [
    'asignatura', 'materia', 'denominación', 'curso', 'grado', 
    'créditos', 'ects', 'carácter', 'tipo',
    'semestre', 'cuatrimestre', 'horario', 'calendario',
    'aula', 'sala', 'laboratorio', 'seminario', 
    'profesor', 'profesora', 'departamento', 'facultad',
    'evaluación', 'examen', 'práctica', 'teoría', 'tutoría',
    'competencias', 'objetivos', 'programa', 'temario',
    'prerrequisitos', 'bibliografía', 'metodología', 'resultados'
]

# Patrones de ruido común en PDFs académicos
NOISE_PATTERNS = [
    r'página\s+\d+',
    r'©\s*\d{4}',
    r'http[s]?://[^\s]+',
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+',
    r'Curso\s+\d{4}-\d{4}',
    r'Página\s+\d+\s+de\s+\d+',
]

# Configuración de cleantext
CLEANTEXT_CONFIG = {
    'clean_all': False,
    'extra_spaces': True,
    'stemming': False,
    'stopwords': False,
    'lowercase': False,
    'numbers': False,
    'punct': False,
    'stp_lang': 'spanish'
}

CLEANTEXT_NOISE_REGEX = (
    r'('
    r'http[s]?://\S+|'
    r'www\.\S+|'
    r'\b\d{9,}\b|'
    r'\+\d{1,3}\s\d{3,}'
    r')'
)

CLEANTEXT_NOISE_REPLACE = ''

# Patrones para post-procesamiento
CURRENCY_SYMBOLS_PATTERN = r'[€$£¥₹¢]'

EMOJI_PATTERN = (
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+"
)

EXCESSIVE_LINEBREAKS_PATTERN = r'\n{3,}'
EXCESSIVE_LINEBREAKS_REPLACE = '\n\n'

NON_ACADEMIC_EMAIL_PATTERN = (
    r'\b[a-zA-Z0-9._%+-]+@'
    r'(?!.*(?:univ|\.es|\.edu))'
    r'[a-zA-Z0-9.-]+\.[a-z]{2,}\b'
)

# Patrones para parsing de fichas
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

PATTERN_PROFESORADO = r"DATOS\s+DEL\s+PROFESORADO(.*?)(?:DESGLOSE|TOTALES?|EVALUACI[ÓO]N|$)"

# Configuración de profesorado
PROFESOR_PREFIXES = [
    'CU', 'TU', 'CD', 'CE', 'AS', 'AY', 'I3', 'A3', 'EXT', 'PSN', 'PP'
]

PROFESOR_INSTITUTIONS = [
    'Universidad', 
    'Hospital', 
    'CSIC', 
    'Dpto', 
    'Facultad', 
    'Instituto', 
    'Centro'
]

PROFESOR_SUFIXES = [
    r'\bCSIC\b',
    r'\bCSIC N\b',
    r'\bUC\b',
    r'\bUniversidad\b',
    r'\bDpto\b',
    r'\bFacultad\b',
    r'\bInstituto\b',
    r'\bCentro\b',
    r'\bHospital\b', 
    r'\bS\b',
    r'\bN\b'
]

# Mapas de normalización
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