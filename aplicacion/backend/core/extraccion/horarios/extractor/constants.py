import re

# Configuracion fisica
 
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


# Cosido (STITCHING) 

STITCHING_CONFIG = {
    'stitch_threshold': 1.0,  
    'space_threshold': 3.5,   
    'newline_threshold': 5.0  
}


# Patrones de reparación y detección de entidades clave

REPAIRS_BROKEN_WORDS = [
    (r'I\s+n\s+g\s+e\s+n\s+i\s+e\s+r\s*[íi]\s*a', 'Ingeniería'),
    (r'Ing\s+en\s+ier[íi]a', 'Ingeniería'), 
    
    (r'Estructurade', 'Estructura de'),
    (r'Intr\s*\.\s*a', 'Intr. a'),    
    (r'Fundam\s+en\s+tos', 'Fundamentos'),
    (r'Fund\.\s+F[íi]sicos', 'Fund. Físicos'),
    
    (r'Comp\s+u\s+tadores', 'Computadores'),
    (r'Compu\s+tadores', 'Computadores'),
    (r'P\s+r\s+o\s+g\s+r\s+a\s+m\s+a\s+c\s+i\s*[óo]\s*n', 'Programación'),
    (r'Progra\s+mación', 'Programación'),
    
    (r'informacio\s+n\b', 'información'),
    (r'Sist\.\s+informaci[oó]n', 'Sist. Información'),
    
    (r'animationand', 'animation and'),
    (r'operativosavanzados', 'operativos avanzados'),
]

PATRONES_RADAR = {
    'titulo': r'(?:DOBLE )?GRADO\s+EN\s+[\w\s\.]+(?:PRIMER|SEGUNDO)\s+CUATRIMESTRE',
    'curso': r'\b(?:(?:PRIMER|SEGUNDO|TERCER|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|[1-6](?:º|er|°)?)(?:\s*CURSO)?|(?:I{1,3}|IV|V|VI)\s+CURSO)\b(?!\s*CUATRIMESTRE)',
    'mencion': r'(?:MENCI[ÓO]N(?:ES)?|MECI[ÓO]N|ESPECIALIDAD|ITINERARIO)(?:\s+EN|\s+DE)?\s+([A-ZÁÉÍÓÚÑ\.\s]+)',
}

RX_CURSO = re.compile(PATRONES_RADAR['curso'], re.IGNORECASE)
RX_MENCION = re.compile(PATRONES_RADAR['mencion'], re.IGNORECASE)

MAPA_CURSOS = {
    "PRIMER": "1º", "PRIMERO": "1º", "1ER": "1º",
    "SEGUNDO": "2º",
    "TERCER": "3º", "TERCERO": "3º",
    "CUARTO": "4º",
    "QUINTO": "5º",
    "SEXTO": "6º",
    
    "1º": "1º", "1°": "1º", 
    "2º": "2º", "2°": "2º",
    "3º": "3º", "3°": "3º",
    "4º": "4º", "4°": "4º",
    "5º": "5º", "5°": "5º",
    "6º": "6º", "6°": "6º",

    "I": "1º", "II": "2º", "III": "3º", "IV": "4º", "V": "5º", "VI": "6º"
}

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


# Configuración de detección de títulos y periodos

LABEL_PERIODO_1 = "Primer Cuatrimestre"
LABEL_PERIODO_2 = "Segundo Cuatrimestre"

LABEL_GRADO_FISICA = "Grado en Física"
LABEL_GRADO_MATEMATICAS = "Grado en Matemáticas"
LABEL_GRADO_INFORMATICA = "Grado en Ingeniería Informática"
LABEL_GRADO_DOBLE = "Doble Grado en Física y Matemáticas"
LABEL_GRADO_UNKNOWN = "-"

KEYWORDS_PERIODO_1 = ["PRIMER CUATRIMESTRE", "1º CUATRIMESTRE"]
KEYWORDS_PERIODO_2 = ["SEGUNDO CUATRIMESTRE", "2º CUATRIMESTRE"]

KEYWORDS_FISICA = ["FÍSICA", "FISICA"]
KEYWORDS_MATEMATICAS = ["MATEMÁTICAS", "MATEMATICAS"]
KEYWORDS_DOBLE = ["DOBLE GRADO"]
KEYWORDS_INFORMATICA = ["GRADO EN INGENIERÍA INFORMÁTICA", "GRADO EN INGENIERIA INFORMATICA"]

# Configuración de corte de pie de página (noise removal)

FOOTER_CUTOFF_PATTERNS = [
    r'Horas\s+reservadas\s+para',
    r'La\s+programación\s+de\s+prácticas',
    r'El\s+número\s+de\s+grupos\s+podría',
    r'Las\s+prácticas\s+de\s+laboratorio',
    r'Los\s+grupos\s+de\s+laboratorios',
    r'^\s*\(\*\)\s*', # Líneas que empiezan por (*)
    r'coordinadas\s+con\s+el\s+responsable',
    r'Cada\s+alumno\s+sólo\s+tendrá',
    r'se\s+unirán\s+los\s+grupos',
    r'programación\s+estará\s+disponible'
]

RX_FOOTER_CUTOFF = [re.compile(p, re.IGNORECASE) for p in FOOTER_CUTOFF_PATTERNS]