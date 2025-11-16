import re

##########################################
## CONSTANTES DEL EXTRACTOR DE HORARIOS ##
##########################################

# Constantes para detección de estructura
TABLA_CONFIG = {
    'min_columnas': 5,  # L-V
    'min_filas': 6,    # Mínimo de franjas horarias
    'tolerancia_alineacion': 5.0  # Pixels/puntos de tolerancia para alineación
}

# Patrones de identificación
PATRONES = {
    'titulo': r'(?:DOBLE )?GRADO\s+EN\s+.+?(?:PRIMER|SEGUNDO)\s+CUATRIMESTRE',  # DOTALL/IGNORECASE en búsqueda
    'curso': r'\b[1-5]º\s*(?:CURSO)?\b',
    'mencion': r'MENCI[ÓO]N\s+EN\s+[A-ZÁÉÍÓÚÑ\s]+',
    'hora': r'\b(?:[01]?\d|2[0-3])[:.]?[0-5]\d\b'
}
# Hora: admite 08:30, 8:30, 0830, 08.30
PATRON_HORA = r'\b(?:[01]?\d|2[0-3])[:.]?[0-5]\d\b'
RX_HORA = re.compile(PATRON_HORA, re.IGNORECASE)

# Curso: 1º, 2º, ..., 5º (opcional "CURSO"); tolera espacio antes del "º"
PATRON_CURSO = r'\b[1-5]\s*º\s*(?:CURSO)?\b'
RX_CURSO = re.compile(PATRON_CURSO, re.IGNORECASE)

# Mención: "MENCIÓN EN <TEXTO>"
PATRON_MENCION = r'MENCI[ÓO]N\s+EN\s+[A-ZÁÉÍÓÚÑ\s]+'
RX_MENCION = re.compile(PATRON_MENCION, re.IGNORECASE)

# Etiquetas esperadas
DIAS_SEMANA = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES']
HORAS_VALIDAS = [f"{h:02d}:{m:02d}" for h in range(8,20) for m in (0,30)]

# Configuración por defecto del extractor
DEFAULT_EXTRACTOR_CONFIG = {
    'max_file_size_mb': 15,
    'min_tablas_por_pagina': 1,
    'max_tablas_por_pagina': 2,
    'log_level': 'INFO',
    'tabla_config': TABLA_CONFIG
}

# Configuración de detección de tablas para pdfplumber
PDFPLUMBER_TABLE_SETTINGS_TEXT = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "intersection_y_tolerance": 3,
    "intersection_x_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 3,
    "min_words_horizontal": 2,
    "snap_tolerance": 3,
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": []
}
PDFPLUMBER_TABLE_SETTINGS_LINES = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_x_tolerance": 5,
    "intersection_y_tolerance": 5,
    "snap_tolerance": 3,
    "min_words_vertical": 0,
    "min_words_horizontal": 0,
}

# Mapeo de días y sus abreviaturas
DAYS_MAP = {
    'LUN': 'LUNES',
    'MAR': 'MARTES', 
    'MIE': 'MIÉRCOLES',
    'MIÉ': 'MIÉRCOLES',
    'JUE': 'JUEVES',
    'VIE': 'VIERNES'
}

# Validación temporal
TIME_CONFIG = {
    'min_hour': 0,
    'max_hour': 23,
    'min_minute': 0,
    'max_minute': 59,
    'min_franjas': 6,  # era 8
}

# Caracteres válidos para parsing de tiempo
VALID_TIME_CHARS = set('0123456789.:')

# Pesos para evaluación de calidad de tablas
TABLE_QUALITY_WEIGHTS = {
    'days_structure': 0.3,     # 30% - Estructura de días completa
    'time_structure': 0.3,     # 30% - Estructura de horas correcta
    'content_density': 0.4     # 40% - Densidad de contenido en celdas
}


#===================================#
# CONSTANTES DEL PARSER DE HORARIOS #
#===================================#

# Patrones para identificación de aulas
PATRONES_AULAS = {
    'aulas': [
        r'AULA\s+\d+',
        r'Aula\s+\d+'
    ],
    'laboratorios': [
        r'LAB\s+\d+',
        r'LAB'
    ],
    'seminarios': [
        r'Seminario\s+de\s+informática',
        r'Seminario\s+de\s+física',
        r'Seminario\s+de\s+matemáticas'
    ],
    'otros': [
        r'LSC\s*\d+',
        r'ATC'
    ]
}

# Compilar todos los patrones de aulas en un solo regex (para eficiencia)
_all_aula_patterns = []
for categoria in PATRONES_AULAS.values():
    _all_aula_patterns.extend(categoria)
PATRON_AULA_COMBINADO = re.compile('|'.join(f'({p})' for p in _all_aula_patterns), re.IGNORECASE)

# Patrones para grupos de prácticas
PATRON_GRUPO_PL = re.compile(r'PL\s*(\d+)', re.IGNORECASE)
PATRON_GRUPO_PA = re.compile(r'PA\s*(\d+)', re.IGNORECASE)
PATRON_GRUPO_GENERICO = re.compile(r'Grupo\s+(\d+)', re.IGNORECASE)

# Patrones para parsing de título
PATRON_PERIODO = re.compile(r'(PRIMER|SEGUNDO)\s+CUATRIMESTRE', re.IGNORECASE)
PATRON_NORMALIZAR_ESPACIOS = re.compile(r'\s{2,}')
CARACTERES_STRIP_TITULO = ' -——'

# Patrón para limpieza de texto (añadir espacio antes de mayúscula precedida de minúscula)
PATRON_MAYUSCULA_SIN_ESPACIO = re.compile(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])')

# Patrón para preposiciones pegadas
PATRON_PREPOSICION_PEGADA_Y = re.compile(r'([a-záéíóúñ])([yY])([A-ZÁÉÍÓÚÑ])')
PATRON_PREPOSICION_PEGADA_GENERAL = re.compile(r'([a-záéíóúñ])(de|en|con|para)([A-ZÁÉÍÓÚÑ])', re.IGNORECASE)

# Tipos de sesión
TIPO_TEORIA = 'TEORÍA'
TIPO_PRACTICA = 'PRÁCTICA'
TIPO_PRACTICA_AULA = 'PRÁCTICA_AULA'

# Duraciones (en minutos)
DURACION_MINIMA_SESION = 60      # 1 hora
DURACION_MAXIMA_SESION = 180     # 3 horas
DURACION_DEFAULT_ULTIMA_SESION = 120  # 2 horas (cuando no hay sesión siguiente)
GRID_STEP_MINUTES = 60           # Salto típico entre franjas horarias

# Configuración base del parser de horarios
DEFAULT_PARSER_CONFIG = {
    'version': '0.1.0',

    # Logging y validación
    'log_level': 'INFO',
    'strict_validation': True,

    # Normalización general
    'normalize_whitespace': True,
    'unknown_subject_label': 'DESCONOCIDO',

    # Inferencias y suposiciones
    'infer_teoria_when_no_group': True,  # Si no hay marca de grupo (PL/PA) se asume TEORÍA

    # Rejilla temporal y duraciones (usar constantes globales)
    'grid_step_minutes': GRID_STEP_MINUTES,
    'fallback_session_duration_minutes': DURACION_DEFAULT_ULTIMA_SESION,
    'min_session_duration_minutes': DURACION_MINIMA_SESION,
    'max_session_duration_minutes': DURACION_MAXIMA_SESION,

    # Heurísticas de postprocesado
    'postprocess_merge_short_fragments': True,          # unir fragmentos muy cortos
    'postprocess_max_fragment_len': 5,
    'postprocess_inherit_aula_same_slot': True,         # heredar aula en misma franja
    'postprocess_merge_consecutive_same_subject': True, # fusionar sesiones contiguas

    # Formato de salida
    'time_format': '%H:%M',
}

# =============================================================================
# CONSTANTES PARA FUSIÓN DE CELDAS (EXTRACTOR)
# =============================================================================

# Longitud mínima para considerar texto válido (no fragmentos como "de", "y")
MIN_FRAGMENT_LENGTH = 3

# Longitud máxima para considerar como "solo aula" o "solo grupo"
MAX_ROOM_LENGTH = 25  # Aumentado para "AULA 4 bis", etc.
MAX_GROUP_LENGTH = 15

# Porcentaje mínimo de coincidencia con patrón de aula (bajado para mayor tolerancia)
MIN_ROOM_PATTERN_COVERAGE = 0.6  # 60% del texto debe ser el aula