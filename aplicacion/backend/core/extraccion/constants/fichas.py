DEFAULT_FICHA_CONFIG = {
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

PATTERN_ECTS = r"(?:CR[ÉE]DITOS?\s*ECTS|ECTS)\s*:\s*([0-9]{1,2}(?:[.,][0-9]+)?)"

PATTERN_PERIODO = r"(?:SECUENCIA|PER[IÍ]ODO)\s*:\s*([A-Za-zÁÉÍÓÚÜÑ]+)"

PATTERN_MODALIDAD = r"\b(OBLIGATORIA|OPTATIVA|B[ÁA]SICA|TRONCAL)\b"

PATTERN_IDIOMA = r"\b(?:Idioma|Language)\s*:\s*([A-Za-zÁÉÍÓÚÜÑ]+)"

PATTERN_ENGLISH_FRIENDLY = r"\b(?:English\s*friendly|Docencia\s+en\s+ingl[eé]s)\s*:\s*(sí|si|no|yes|true|false|1|0)\b"

# Delimita bloque profesorado entre encabezado y secciones siguientes habituales
PATTERN_PROFESORADO = r"DATOS\s+DEL\s+PROFESORADO(.*?)(?:DESGLOSE|TOTALES?|EVALUACI[ÓO]N|$)"

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