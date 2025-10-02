DEFAULT_FICHA_CONFIG = {
    "version": "1.0.0",
    "min_confidence": 0.5,
    "default_idioma": "ESPAÑOL",
}

# ==========================
# Patrones regex para parsing
# ==========================

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