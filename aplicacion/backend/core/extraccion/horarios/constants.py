import re

# --- Config por defecto (tuning, editable en runtime) ---
DEFAULT_EXTRACTOR_CONFIG = {
    "prefer_lattice": True,
    "lattice_opts": {"flavor": "lattice"},
    "stream_opts": {"flavor": "stream"},
    "table_areas_by_page": {},   # {1: ["x1,y1,x2,y2"], ...}
    "columns_by_page": {},       # {1: ["x_hora, x_lunes, x_martes, x_miércoles, x_jueves, x_viernes"], ...}
    "max_header_scan_rows": 5,
    "window_strict": True,
}

DEFAULT_PARSER_CONFIG = {
    "version": "0.1.0",
}


# --- Constantes del extractor (invariantes) ---
TIME_WINDOW = ("08:00", "20:30")
TIME_WINDOW_START, TIME_WINDOW_END = TIME_WINDOW
DAYS_CANONICAL = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES"]
DAY_ALIASES = {"LUNES":"LUNES",
               "MARTES":"MARTES",
               "MIERCOLES":"MIÉRCOLES",
               "MIÉRCOLES":"MIÉRCOLES",
               "JUEVES":"JUEVES",
               "VIERNES":"VIERNES"}
HEADER_DAYS_ORDER = {"LUNES":0,"MARTES":1,"MIÉRCOLES":2,"JUEVES":3,"VIERNES":4}

EXPECTED_DAYS_COUNT = 5
TIME_FORMAT = "%H:%M"
TIME_SLOT_MINUTES = 60
HEADER_MIN_DAY_HITS = 3
CELL_EMPTY_TOKENS = {"", "-", "—"}
NORMALIZE_LINE_SEPS = ("\r\n","\r","\n")

# Patrones regex para detectar la titulacion en el PDF
TITULACION_PATTERNS = [
    re.compile(r"Titulaci[oó]n\s*:\s*(.+)", re.IGNORECASE),
    re.compile(r"Doble\s+Grado\s+en\s+([A-Za-zÁÉÍÓÚÜáéíóúüñÑ\s]+)", re.IGNORECASE),
    re.compile(r"Máster(?:\s+Universitario)?\s+en\s+([A-Za-zÁÉÍÓÚÜáéíóúüñÑ\s]+)", re.IGNORECASE),
    re.compile(r"GRADO\s+EN\s+([A-ZÁÉÍÓÚÜÑ ]+)", re.IGNORECASE),
    re.compile(r"GRADO:?\s*([A-ZÁÉÍÓÚÜÑ ]+)", re.IGNORECASE),
]

BLACKLIST_TOKENS = ("HORARIO", "CURSO", "AULA")
TIME_LIKE_REGEX = r"(?:\b[01]?\d|2[0-3])[:h\.]?[0-5]\d\b|\b\d{3,4}\b"

# Penalizaciones para confianza
CONFIDENCE_ERR_MAX = 0.6
CONFIDENCE_ERR_STEP = 0.3
CONFIDENCE_SEVERE_MAX = 0.40
CONFIDENCE_SEVERE_STEP = 0.08
CONFIDENCE_MODERATE_MAX = 0.25
CONFIDENCE_MODERATE_STEP = 0.04
CONFIDENCE_MINOR_MAX = 0.15
CONFIDENCE_MINOR_STEP = 0.02
CONFIDENCE_CELL_COVERAGE = 0.4
CONFIDENCE_PAGE_COVERAGE = 0.3
CONFIDENCE_NO_TEXT_PENALTY = 0.05

# Umbrales de calidad
QUALITY_UNUSABLE_CELL_COVERAGE = 0.1
QUALITY_UNUSABLE_PAGE_RATIO = 0.2
QUALITY_POOR_PAGE_RATIO = 0.4
QUALITY_POOR_CELL_COVERAGE = 0.4
QUALITY_POOR_SEVERE_PER_PAGE = 2
QUALITY_ACCEPTABLE_PAGE_RATIO = 0.5
QUALITY_ACCEPTABLE_CELL_COVERAGE = 0.6
QUALITY_ACCEPTABLE_SEVERE_PER_PAGE = 1  # <= page_count
QUALITY_GOOD_PAGE_RATIO = 0.75
QUALITY_GOOD_CELL_COVERAGE = 0.75
QUALITY_GOOD_CONFIDENCE = 0.75
QUALITY_EXCELLENT_PAGE_RATIO = 0.9
QUALITY_EXCELLENT_CELL_COVERAGE = 0.9
QUALITY_EXCELLENT_CONFIDENCE = 0.9


#--- Constantes del parser (invariantes) ---

# Normalizacion / splitting
TOKEN_SPLIT_REGEX = r"[\\n,;]+|\\s+—\\s+|\\s+-\\s+"
RE_WHITESPACE_NORM = r"[ \\t]+"
RE_DASHES = r"[–—-]+"
UNKNOWN_TOKENS = {"", "-", "—"}

# Grupos
RE_GRUPO_PL = r"\\bPL\\s?\\d+\\b"
RE_GRUPO_PA = r"\\bPA\\s?\\d+\\b"
RE_GRUPO_GENERIC = r"\\bGrupo\\s?\\d+\\b"

# Aulas
RE_AULA = r"\\b(?:AULA\\s?\\d+)\\b"
RE_AULA_LAB = r"\\bLAB\\b"
RE_AULA_LSC = r"\\bLSC\\s?\\d+\\b"
RE_AULA_SEMINARIO = r"\\bSEMINARIO(?:\\s+[A-ZÁÉÍÓÚÜÑa-záéíóúüñ]+)?\\b"
RE_AULA_ABBREV = r"\\bAULA\\b|\\bLAB\\b|\\bLSC\\b"

# Modalidad (keywords y mapeo canon)
MODALIDAD_KEYWORDS = {
    "practicas_laboratorio": {"PL", "LAB", "LSC", "LABORATORIO"},
    "practicas_aula": {"PA", "PRÁCT.", "PRÁCTICAS", "PRACT."},
    "teoria": {"TEOR", "TEORÍA", "CLASE", "LECCIÓN"}
}
MODALIDAD_CANON_MAP = {
    "lab": "practicas_laboratorio",
    "pl": "practicas_laboratorio", 
    "pa":"practicas_aula", 
}

# Orden de prioridad de modalidades (de más específica a más general)
# Se usa para resolver casos donde una misma celda activa varias categorías.
MODALIDAD_PRIORITY = [
    "practicas_laboratorio",  # máxima prioridad: laboratorio, LSC, PL
    "practicas_aula",         # segunda: prácticas en aula o PA
    "teoria",                 # por defecto, si no hay ninguna otra señal
]

# Ambigüedades / avisos
AMBIGUOUS_TOKENS = {"GRUPO", "G.", "P.", "PL", "PA"} 
AULA_PREFIXES = {"AULA", "LAB", "LSC", "SEMINARIO"} 

# Asignatura
RE_PUNCT_TRIM = r"^[\\s,;:-]+|[\\s,;:-]+$"
RE_MULTI_SPACE = r"\\s{2,}"