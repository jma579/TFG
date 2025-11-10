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


###########################
## CONSTANTES DEL PARSER ##
###########################

# Configuración por defecto del parser
DEFAULT_PARSER_CONFIG = {
    # Versión del parser
    'version': '1.0',
    
    # Configuración de Gemini
    'gemini_model': 'gemini-2.5-flash',
    'gemini_temperature': 0.0,
    'gemini_mime_type': 'application/json',
    'gemini_api_key_env': 'GEMINI_API_KEY',
    
    # Configuración de sesiones
    'tipos_validos': ['teoria', 'practicas de aula', 'practicas de laboratorio'],
    'tipo_default': 'teoria',
    'hora_min': '08:00',
    'hora_max': '21:30',
    'duracion_min_minutos': 30,
    'duracion_max_minutos': 240,
    
    # Logging y errores
    'log_level': 'INFO',
    'strict_validation': True,
    
    # Comportamiento del parser
    'reuse_gemini_context': False,
    'cache_responses': True,
    
    # Timeouts y reintentos
    'gemini_timeout': 30,  # segundos
    'max_retries': 3,
    'retry_delay': 1  # segundos
}

# Patrones para procesar títulos
PATRON_TITULO = {
    "GRADO": r"GRADO EN (?P<titulacion>[^()]+?)(?:\s+(?P<periodo>PRIMER|SEGUNDO) CUATRIMESTRE)?$",
    "DOBLE GRADO": r"DOBLE GRADO EN (?P<titulacion>[^()]+?)(?:\s+(?P<periodo>PRIMER|SEGUNDO) CUATRIMESTRE)?$"
}

# Mapeo de periodos
PERIODO_MAP = {
    "PRIMER": "PRIMER_CUATRIMESTRE",
    "SEGUNDO": "SEGUNDO_CUATRIMESTRE",
}

# =============================================================================
# CONSTANTES DEL PROMPT DE PARSING DE HORARIOS
# (Etiquetas para construir el texto de entrada de Gemini)
# =============================================================================
PROMPT_HEADER_CONTEXT = "== 1. CONTEXTO DE LA TABLA =="
PROMPT_LABEL_CURSO = "CURSO:"
PROMPT_LABEL_MENCION = "MENCIÓN:"
PROMPT_LABEL_PAGINA = "PÁGINA:"

PROMPT_HEADER_KEYS = "== 2. CLAVE DE COORDENADAS (MAPA DE LA TABLA) =="
PROMPT_LABEL_DAYS = "DÍAS_DE_LA_TABLA (Columnas):"
PROMPT_LABEL_TIMES = "HORAS_DE_INICIO (Filas):"

PROMPT_HEADER_CANDIDATES = "== 3. SESIONES CANDIDATAS (Celdas con contenido) =="
PROMPT_DIVIDER_CANDIDATE = "--- SESIÓN CANDIDATA ---"
PROMPT_LABEL_DAY = "DÍA:"
PROMPT_LABEL_START_TIME = "HORA_INICIO_FILA:"
PROMPT_LABEL_RAW_CONTENT = "CONTENIDO_RAW:"

# =============================================================================
# CONSTANTES DEL PROMPT DE PARSING (El "Contrato" de Gemini)
# =============================================================================

# --- Constantes de Mapeo de Tipo (LAS QUE FALTABAN) ---

# 1. Representación en string de las modalidades válidas para el prompt
MODALIDADES_VALIDAS_LITERAL = "['teoria', 'practicas de laboratorio', 'practicas de aula']"

# 2. Reglas de mapeo (anteriormente llamada REGLAS_MAPEO_MODALIDADES)
REGLAS_MAPEO_TIPO = """
- Si el 'CONTENIDO_RAW' contiene 'LAB', 'PL' o 'Experimental', usa 'practicas de laboratorio'.
- Si el 'CONTENIDO_RAW' contiene 'PA', usa 'practicas de aula'.
- Para todo lo demás (clases teóricas estándar), usa 'teoria'.
"""

# --- Constantes del Prompt (ACTUALIZADAS) ---

# Encabezado de la Tarea
PROMPT_TASK_HEADER = "== 4. TAREA DE PARSEO (Tu Misión) =="
PROMPT_TASK_BODY = """
Tu misión es analizar el bloque "== 3. SESIONES CANDIDATAS ==" anterior.
Cada "SESIÓN CANDIDATA" debe ser convertida en un objeto JSON.
Tu salida debe ser una ÚNICA lista JSON (`List[SesionSchema]`) que contenga TODAS las sesiones inferidas.
NO incluyas texto explicativo, solo la lista JSON.
"""

# Encabezado de las Reglas
PROMPT_RULES_HEADER = "== 5. REGLAS DE INFERENCIA ESTRICTAS =="

# Regla 1: Inferencia de Duración
PROMPT_RULE_DURATION = """
REGLA 1 (Duración y Celdas Combinadas):
- Debes inferir la `hora_fin` de cada sesión. Usa la `HORA_INICIO_FILA` y la lista `HORAS_DE_INICIO (Filas)` del "== 2. CLAVE DE COORDENADAS ==".
- Una sesión se extiende hasta la `HORA_INICIO_FILA` de la siguiente sesión candidata en esa misma columna, O MÁS.
- **Inferencia de Celdas Combinadas**: El `CONTENIDO_RAW` (ej. "Fisica Basica") puede aplicarse a múltiples filas de horas (ej. '12:00', '12:30', '13:00'). Tu trabajo es detectar esto y calcular la `hora_fin` correcta.
- Ejemplo: Una sesión en '12:00' (en un horario que va '12:00', '12:30', '13:00', '13:30') y cuya celda ocupa visualmente hasta las 13:30, debe tener `hora_inicio: "12:00"` y `hora_fin: "13:30"`.
"""

# Regla 2: Mapeo de Tipo (CORREGIDA)
PROMPT_RULE_TYPE_MAPPING_HEADER = f"""
REGLA 2 (Tipo/Modalidad):
- Debes mapear el `tipo` (modalidad) obligatoriamente a uno de estos tres valores: {MODALIDADES_VALIDAS_LITERAL}.
- Usa estas reglas de mapeo:
{REGLAS_MAPEO_TIPO}
"""

# Regla 3: Extracción de Entidades
PROMPT_RULE_EXTRACTION = """
REGLA 3 (Extracción de Entidades):
- Extrae `asignatura`, `aula` y `grupo` del `CONTENIDO_RAW`.
- El `dia` debe ser el valor de la etiqueta `DÍA:`.
- Si `aula` o `grupo` no se encuentran en el `CONTENIDO_RAW`, usa `null`.
- La `asignatura` NUNCA debe ser `null`. Si no puedes identificar una asignatura, omite la sesión.
"""

# Encabezado del Esquema de Salida
PROMPT_OUTPUT_HEADER = "== 6. ESQUEMA DE SALIDA (JSON: List[SesionSchema]) =="

# Ejemplo de JSON para el prompt
EXAMPLE_JSON_OUTPUT = [
    {
        "asignatura": "Asignatura Ejemplo",
        "tipo": "teoria",
        "dia": "LUNES",
        "hora_inicio": "09:30",
        "hora_fin": "11:30",
        "aula": "AULA 4",
        "grupo": "Grupo 1"
    },
    {
        "asignatura": "Otra Asignatura",
        "tipo": "practicas de laboratorio",
        "dia": "MARTES",
        "hora_inicio": "12:30",
        "hora_fin": "14:00",
        "aula": "LAB",
        "grupo": "Grupo 2"
    }
]

TIPOS_SESION = {
    # Teoría
    "TEORIA": "teoria",
    "TEORÍA": "teoria",
    "T": "teoria",
    "TEÓRICA": "teoria",
    # Prácticas
    "PRACTICA": "practicas de aula",
    "PRÁCTICA": "practicas de aula",
    "PA": "practicas de aula",
    "PRACTICAS": "practicas de aula",
    "PRÁCTICAS": "practicas de aula",
    # Laboratorio
    "LAB": "practicas de laboratorio",
    "LABORATORIO": "practicas de laboratorio",
    "PL": "practicas de laboratorio",
    "PRACTICAS LAB": "practicas de laboratorio",
    "PRÁCTICAS LAB": "practicas de laboratorio"
}

DIAS_MAP = {
    # Forma completa
    "LUNES": "LUNES",
    "MARTES": "MARTES",
    "MIERCOLES": "MIERCOLES",
    "MIÉRCOLES": "MIERCOLES",
    "JUEVES": "JUEVES",
    "VIERNES": "VIERNES",
    # Abreviaturas
    "L": "LUNES",
    "M": "MARTES",
    "X": "MIERCOLES",
    "J": "JUEVES",
    "V": "VIERNES",
    # Otras variantes comunes
    "LUN": "LUNES",
    "MAR": "MARTES",
    "MIE": "MIERCOLES",
    "MIÉ": "MIERCOLES",
    "JUE": "JUEVES",
    "VIE": "VIERNES"
}
