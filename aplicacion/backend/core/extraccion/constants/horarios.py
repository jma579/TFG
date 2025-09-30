"""
Constantes y expresiones regulares para el parser de horarios académicos.
Estas constantes están alineadas con los patrones habituales del OCR y
con los imports que realiza `HorarioParser`.
"""

from __future__ import annotations

# Días de la semana admitidos en el documento OCR.
# Incluimos ambas variantes de MIÉRCOLES para tolerar pérdida de tilde.
DAYS = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES"]

# Tokens/regex para segmentar por curso (bloques tipo "PRIMER CURSO", etc.).
# Cada tupla es (numero_curso, patron_regex).
CURSO_TOKENS = [
    (1, r"\bPRIMER\s+CURSO\b"),
    (2, r"\bSEGUNDO\s+CURSO\b"),
    (3, r"\bTERCER\s+CURSO\b"),
    (4, r"\bCUARTO\s+CURSO\b"),
    (5, r"\bQUINTO\s+CURSO\b"),
]

# Regex para detectar el nombre del programa/título (líneas en mayúsculas "anchas").
PROGRAM_RX = r"^(?P<programa>[A-ZÁÉÍÓÚÜÑ ]{10,})$"

# Regex para detectar el periodo (p. ej., "PRIMER CUATRIMESTRE").
PERIODO_RX = r"\b(PRIMER|SEGUNDO)\s+CUATRIMESTRE\b"

# Regex de aulas típicas en los horarios (AULA N, LSC N, PL N).
AULA_RX = r"\b(AULA\s+[A-Za-z0-9]+|LSC\s*\d+|PL\s*\d+)\b"

# Regex para grupos (acepta mayúsculas/minúsculas gracias al inline flag (?i)).
GRUPO_RX = r"(?i)\b(Grupo\s+\d+)\b"

# Tags que identifican prácticas/laboratorio.
LAB_TAGS = r"\b(LAB|Pr[aá]ct\.?|Pr[aá]cticas|PL\s*\d+)\b"

# Token de hora: admite "8:30", "0830", "18:30", "1830".
HOUR_TOKEN = r"(?:[01]?\d|2[0-3]):?[0-5]\d"

# Split por días (si quisieras usar re.split para segmentación por día).
DAY_SPLIT_RX = r"(?=^(LUNES|MARTES|MIÉRCOLES|MIERCOLES|JUEVES|VIERNES)\s*$)"

# Configuración por defecto del parser de horarios.
DEFAULT_HORARIO_CONFIG = {
    "min_confidence": 0.50,
    # Modalidad por defecto cuando no se detecta tag de LAB/Prácticas.
    "default_modalidad": "TEORIA",
}

__all__ = [
    "DAYS",
    "CURSO_TOKENS",
    "PROGRAM_RX",
    "PERIODO_RX",
    "AULA_RX",
    "GRUPO_RX",
    "LAB_TAGS",
    "HOUR_TOKEN",
    "DAY_SPLIT_RX",
    "DEFAULT_HORARIO_CONFIG",
]
