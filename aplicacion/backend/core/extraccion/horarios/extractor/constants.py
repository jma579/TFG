import re
from core.extraccion.common.entities import ExtractionQuality, ProcessingStatus

# =============================================================================
# 1. CONFIGURACIÓN FÍSICA
# =============================================================================

ATOM_EXTRACT_SETTINGS = {
    "x_tolerance": 1.0, 
    "y_tolerance": 3,
    "keep_blank_chars": False
}

PDFPLUMBER_GRID_SETTINGS = {
    "vertical_strategy": "lines", 
    "horizontal_strategy": "lines",
    "snap_tolerance": 5,
    "join_tolerance": 5,
    "edge_min_length": 3,
}

GRID_CONFIG = {
    'min_col_width': 25,      
    'min_row_height': 10,     
    'header_scan_height': 250, 
}

# =============================================================================
# 2. COSIDO (STITCHING) - AJUSTE FINO V1.8
# =============================================================================

STITCHING_CONFIG = {
    'stitch_threshold': 1.0,  
    # SUBIDO A 3.5: Tolerancia mayor para NO partir palabras justificadas ("Fundam en tos")
    'space_threshold': 3.5,   
    'newline_threshold': 5.0  
}

# =============================================================================
# 3. PATRONES DE REPARACIÓN Y DETECCIÓN
# =============================================================================

REPAIRS_BROKEN_WORDS = [
    # Ingeniería
    (r'I\s+n\s+g\s+e\s+n\s+i\s+e\s+r\s*[íi]\s*a', 'Ingeniería'),
    (r'Ing\s+en\s+ier[íi]a', 'Ingeniería'), 
    
    # Casos detectados en capturas (Pág 1 y 2)
    (r'Estructurade', 'Estructura de'),
    (r'Intr\s*\.\s*a', 'Intr. a'),      # Arregla "Intr . a"
    (r'Fundam\s+en\s+tos', 'Fundamentos'),
    (r'Fund\.\s+F[íi]sicos', 'Fund. Físicos'),
    
    # Asignaturas comunes
    (r'Comp\s+u\s+tadores', 'Computadores'),
    (r'Compu\s+tadores', 'Computadores'),
    (r'P\s+r\s+o\s+g\s+r\s+a\s+m\s+a\s+c\s+i\s*[óo]\s*n', 'Programación'),
    (r'Progra\s+mación', 'Programación'),
    
    # Información / Informática
    (r'informacio\s+n\b', 'información'),
    (r'Sist\.\s+informaci[oó]n', 'Sist. Información'),
    
    # Fusiones accidentales
    (r'animationand', 'animation and'),
    (r'operativosavanzados', 'operativos avanzados'),
]

PATRONES_RADAR = {
    'titulo': r'(?:DOBLE )?GRADO\s+EN\s+[\w\s\.]+(?:PRIMER|SEGUNDO)\s+CUATRIMESTRE',
    
    # --- REGEX DE CURSO (ESTRATEGIA DUAL) ---
    # GRUPO 1: Palabras u ordinales (PRIMER, 1º) -> "CURSO" es opcional.
    # GRUPO 2: Romanos (I, II, III) -> "CURSO" es OBLIGATORIO para no confundir con "Física II".
    'curso': r'\b(?:(?:PRIMER|SEGUNDO|TERCER|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|[1-6](?:º|er|°)?)(?:\s*CURSO)?|(?:I{1,3}|IV|V|VI)\s+CURSO)\b(?!\s*CUATRIMESTRE)',
    
    'mencion': r'(?:MENCI[ÓO]N(?:ES)?|MECI[ÓO]N|ESPECIALIDAD|ITINERARIO)(?:\s+EN|\s+DE)?\s+([A-ZÁÉÍÓÚÑ\.\s]+)',
}

RX_CURSO = re.compile(PATRONES_RADAR['curso'], re.IGNORECASE)
RX_MENCION = re.compile(PATRONES_RADAR['mencion'], re.IGNORECASE)

MAPA_CURSOS = {
    # Palabras clave
    "PRIMER": "1º", "PRIMERO": "1º", "1ER": "1º",
    "SEGUNDO": "2º",
    "TERCER": "3º", "TERCERO": "3º",
    "CUARTO": "4º",
    "QUINTO": "5º",
    "SEXTO": "6º",
    
    # Ordinales explícitos (la regex captura el símbolo º)
    "1º": "1º", "1°": "1º", 
    "2º": "2º", "2°": "2º",
    "3º": "3º", "3°": "3º",
    "4º": "4º", "4°": "4º",
    "5º": "5º", "5°": "5º",
    "6º": "6º", "6°": "6º",

    # Romanos (Requieren contexto "CURSO" en la regex, así que son seguros)
    "I": "1º", "II": "2º", "III": "3º", "IV": "4º", "V": "5º", "VI": "6º"
}

# Si una línea tiene esto, LA DESCARTAMOS para la búsqueda de curso.
KEYWORDS_TABLE_CONTENT = [
    "LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES",
    "08:", "09:", "10:", "11:", "12:", "13:", "14:", "15:", "16:", "17:", "18:", "19:", "20:",
    "AULA", "LAB", "SEMANAS", "PÁGINA", "PAGE", "HOJA"
]

RX_HORA = re.compile(r'\b(?:[01]?\d|2[0-3])[:.]?[0-5]\d\b')

DIAS_REGEX = {
    'LUN': re.compile(r'L\s*U\s*N\s*E\s*S', re.IGNORECASE),
    'MAR': re.compile(r'M\s*A\s*R\s*T\s*E\s*S', re.IGNORECASE),
    'MIE': re.compile(r'M\s*I\s*[ÉE]\s*R\s*C\s*O\s*L\s*E\s*S', re.IGNORECASE),
    'JUE': re.compile(r'J\s*U\s*E\s*V\s*E\s*S', re.IGNORECASE),
    'VIE': re.compile(r'V\s*I\s*E\s*R\s*N\s*E\s*S', re.IGNORECASE),
}

DIAS_SEMANA = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES']
DAYS_MAP = {
    'LUN': 'LUNES', 'MAR': 'MARTES', 'MIE': 'MIÉRCOLES', 'MIÉ': 'MIÉRCOLES', 
    'JUE': 'JUEVES', 'VIE': 'VIERNES'
}
VALID_TIME_CHARS = set('0123456789.:')

DEFAULT_EXTRACTOR_CONFIG = {
    'min_tablas_por_pagina': 1,
    'log_level': 'INFO'
}

# =============================================================================
# 4. CONFIGURACIÓN DE DETECCIÓN DE TÍTULOS Y PERIODOS
# =============================================================================

# Etiquetas de salida (Lo que se guarda en el JSON)
LABEL_PERIODO_1 = "Primer Cuatrimestre"
LABEL_PERIODO_2 = "Segundo Cuatrimestre"

LABEL_GRADO_FISICA = "Grado en Física"
LABEL_GRADO_MATEMATICAS = "Grado en Matemáticas"
LABEL_GRADO_INFORMATICA = "Grado en Ingeniería Informática"
LABEL_GRADO_DOBLE = "Doble Grado en Física y Matemáticas"
LABEL_GRADO_UNKNOWN = "-"

# Palabras clave para la detección (Debe estar en MAYÚSCULAS para coincidir con upper())
KEYWORDS_PERIODO_1 = ["PRIMER CUATRIMESTRE", "1º CUATRIMESTRE"]
KEYWORDS_PERIODO_2 = ["SEGUNDO CUATRIMESTRE", "2º CUATRIMESTRE"]

KEYWORDS_FISICA = ["FÍSICA", "FISICA"]
KEYWORDS_MATEMATICAS = ["MATEMÁTICAS", "MATEMATICAS"]
KEYWORDS_DOBLE = ["DOBLE GRADO"]
# Para informática buscamos la frase específica para no confundir con menciones
KEYWORDS_INFORMATICA = ["GRADO EN INGENIERÍA INFORMÁTICA", "GRADO EN INGENIERIA INFORMATICA"]