import re

# =============================================================================
# REGLAS DE PARSEO SEMÁNTICO (V1.5 - FINAL POLISH)
# =============================================================================

# 1. CONSTANTES DE TIPO DE SESIÓN
TIPO_PRACTICA = 'PRÁCTICA'
TIPO_TEORIA = 'TEORÍA'
TIPO_GENERICO = 'CLASE'

# 2. CORRECCIONES PREVIAS (OCR TYPOS)
OCR_CORRECTIONS = {
    r'\bAULA\s+S\b': 'AULA 5',
    r'\bAULA\s+LA\b': 'AULA 14',
    r'\bAULA\s+L4\b': 'AULA 14',
    r'\bLSC\s+I\b': 'LSC 1',
    r'informacio\s+n': 'información',
}

# 3. PATRONES DE AULAS (Añadido LATC)
RE_AULA = re.compile(
    r'\b(?:'
    r'AULA\s*(?:DE\s+)?(?:INF\s*)?[\w\.\-]+|'
    r'LAB(?:\.|oratorio)?\s*[\w\s\.]+|'
    r'LSC\s*\d+|'
    r'LATC|'                                  # NUEVO: Laboratorio ATC específico
    r'ATC|'
    r'L\s*\d+|'
    r'SEM\.?\s*(?:INF|FIS|MAT|EST)[\w\s]*|'
    r'UNICAN-LABS|'
    r'ODS'
    r')\b',
    re.IGNORECASE
)

# 4. PATRONES DE GRUPOS
RE_GRUPO = re.compile(
    r'\b(?:'
    r'Grupos?\s*[A-Z0-9\-\s]+|'
    r'PL\s*\d+(?:\s*y\s*PL\s*\d+)?|'
    r'PA\s*\d+(?:\s*y\s*PA\s*\d+)?|'
    r'GADE'
    r')\b',
    re.IGNORECASE
)

# 5. LIMPIEZA DE ASIGNATURA
# Añadidos: ?, *, (, ) para eliminar basura de notas al pie o dudas
_RE_CLEANUP_TOKENS = re.compile(
    r'\b(TE|PL|PA|y)\b|[/\.,:–\-\?\*\(\)]+', 
    re.IGNORECASE
)

def apply_ocr_corrections(text: str) -> str:
    if not text: return ""
    for pattern, replacement in OCR_CORRECTIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def clean_subject_name(text: str) -> str:
    if not text: return ""
    clean = _RE_CLEANUP_TOKENS.sub(' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean