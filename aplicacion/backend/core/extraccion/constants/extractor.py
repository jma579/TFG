"""
Constantes específicas para el extractor PDF nativo.

Este módulo contiene toda la configuración específica del PDFExtractor,
patrones regex para detección académica, configuración de cleantext y
constantes para cálculos de métricas de calidad.
"""

import re
from typing import Dict, Any, List

# =============================================================================
# CONFIGURACIÓN POR DEFECTO DEL EXTRACTOR PDF
# =============================================================================

DEFAULT_EXTRACT_CONFIG = {
    'max_file_size_mb': 10,          # Máximo 10MB (fichas y horarios son pequeños)
    'max_pages': 20,                 # Máximo 20 páginas (fichas suelen ser 1-3 páginas)
    'stop_after_n_empty_pages': 3,   # Parar después de 3 páginas vacías
    'min_alpha_ratio': 0.35,         # 35% mínimo (más permisivo para tablas/horarios)
    'max_short_words_ratio': 0.80,   # 80% máximo (códigos G111 tienen palabras cortas)
    'log_level': 'INFO',             # Nivel de logging por defecto
}

# =============================================================================
# PATRONES REGEX PARA DETECCIÓN ACADÉMICA BÁSICA
# =============================================================================

# Patrones para códigos de asignaturas (específicos para tu universidad)
SUBJECT_CODE_PATTERNS = [
    r'\bG\d{2,4}\b',                    # G100, G111, G1662, etc. (patrón principal)
    r'\bG\d{2,4}[A-Z]?\b',             # G100A, G111B (con sufijo opcional)
    r'\([G]\d{2,4}\)',                  # (G111) en paréntesis
    r'\bG[\s\-\.]\d{2,4}\b',           # G-111, G.111, G 111
]

# Patrones para detección básica de horarios (formato universitario español)
TIME_PATTERNS = [
    r'(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})',     # 09:00-11:00 (formato más común)
    r'(\d{1,2}):(\d{2})\s+a\s+(\d{1,2}):(\d{2})',        # 09:00 a 11:00 (español)
    r'de\s+(\d{1,2}):(\d{2})\s+a\s+(\d{1,2}):(\d{2})',   # de 09:00 a 11:00
    r'(\d{1,2})\.(\d{2})\s*[-–—]\s*(\d{1,2})\.(\d{2})',   # 09.00-11.00 (formato alternativo)
]
# Patrón base para hora suelta
TIME_BASE = r'\b\d{1,2}:\d{2}\b'

# Patrones para días de la semana (específicos para documentos académicos españoles)
DAY_PATTERNS = [
    r'\b(Lunes|Martes|Miércoles|Jueves|Viernes)\b',        # Solo días laborables (más común en horarios académicos)
    r'\b(lunes|martes|miércoles|jueves|viernes)\b',        # Minúsculas
    # r'\b(L|M|X|J|V)\b',  # Usar solo si está cerca de una hora (proximidad)
    r'\b(Lu|Ma|Mi|Ju|Vi)\b',                               # Abreviaciones de dos letras (sin fines de semana)
]

# Patrones para aulas (específicos para sistema universitario español)
CLASSROOM_PATTERNS = [
    r'\b(Aula|Sala)\s+(\d{1,3}[A-Z]?)\b',                 # Aula 101, Sala 25A
    r'\b(Lab\.?|Laboratorio)\s+([A-Z]?\d+[A-Z]?)\b',      # Lab 1, Laboratorio A2
    r'\b(Seminario)\s+(\d+[A-Z]?)\b',                     # Seminario 3A
    r'\b([A-Z]{1,3}\d{1,3}[A-Z]?)\b',                     # A101, LSC2, etc.
    r'\bAULA\s+LSC\d+\b',                                 # AULA LSC12
    r'\bLSC\s+DICOM\s*-\s*AULA\s+\d{1,2}\b',           # LSC DICOM - AULA 12
    r'\bUNICAN-LABS\b',                                    # UNICAN-LABS
    r'\bLATC\b',                                           # LATC
    r'\bLRT\b',                                            # LRT
]

# Si se usan patrones compilados, compílalos donde se usen en el extractor. Elimina esta variable si no se usa.

# =============================================================================
# CONFIGURACIÓN DE CLEANTEXT PARA PDFS ACADÉMICOS
# =============================================================================

CLEANTEXT_CONFIG = {
    'fix_unicode': True,           # Corregir caracteres Unicode malformados
    'to_ascii': False,               # NO convertir a ASCII (preservar acentos españoles)
    'lower': False,           # NO convertir a minúsculas (preservar códigos)
    'no_line_breaks': False,      # Preservar saltos de línea
    'no_phone_numbers': True,     # Remover números de teléfono
    'no_numbers': False,          # PRESERVAR números (importantes para códigos/horarios)
    'no_digits': False,           # PRESERVAR dígitos
    'no_currency_symbols': True,  # Remover símbolos de moneda
    'no_punct': False,           # PRESERVAR puntuación básica
    'lang': 'es',                # Idioma español
}

# =============================================================================
# CONSTANTES PARA MÉTRICAS DE CALIDAD DE TEXTO NATIVO
# =============================================================================

# Ratios mínimos para considerar texto de calidad
MIN_ALPHA_RATIO = 0.6               # 60% caracteres alfabéticos mínimo
MAX_DIGIT_RATIO = 0.4               # 40% dígitos máximo
MAX_PUNCT_RATIO = 0.3               # 30% puntuación máximo
MAX_WHITESPACE_RATIO = 0.4          # 40% espacios en blanco máximo

# Longitudes mínimas para evaluación
MIN_WORD_LENGTH_AVG = 2.5           # Longitud promedio mínima de palabras
MAX_SHORT_WORDS_RATIO = 0.4         # 40% palabras cortas (<3 chars) máximo
MIN_LONG_WORDS_RATIO = 0.1          # 10% palabras largas (>6 chars) mínimo

# Patrones de corrupción común en PDFs
CORRUPTION_PATTERNS = [
    r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\"\']+',  # Caracteres extraños
    r'\s{5,}',                               # Espacios excesivos
    r'[\r\n]{3,}',                          # Saltos de línea excesivos
    r'[A-Za-z]{20,}',                       # Palabras excesivamente largas
]

# Terminología académica española específica para fichas y horarios universitarios
ACADEMIC_TERMS = [
    # Términos de asignaturas y estructura académica
    'asignatura', 'materia', 'denominación', 'curso', 'grado', 
    'créditos', 'ects', 'carácter', 'tipo',
    
    # Términos temporales
    'semestre', 'cuatrimestre', 'horario', 'calendario',
    
    # Espacios y personal
    'aula', 'sala', 'laboratorio', 'seminario', 
    'profesor', 'profesora', 'departamento', 'facultad',
    
    # Términos de evaluación y metodología
    'evaluación', 'examen', 'práctica', 'teoría', 'tutoría',
    'competencias', 'objetivos', 'programa', 'temario',
    
    # Términos específicos de fichas
    'prerrequisitos', 'bibliografía', 'metodología', 'resultados'
]

# Patrones de ruido común en PDFs académicos universitarios
NOISE_PATTERNS = [
    r'página\s+\d+',                        # Números de página
    r'©\s*\d{4}',                          # Copyright
    r'http[s]?://[^\s]+',                  # URLs
    r'\b\d{4}-\d{2}-\d{2}\b',             # Fechas ISO
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+',  # Emails
    r'Curso\s+\d{4}-\d{4}',               # Años académicos
    r'Página\s+\d+\s+de\s+\d+',           # Paginación típica
]

# =============================================================================
# PATRONES ESPECÍFICOS PARA FICHAS ACADÉMICAS
# =============================================================================

# Patrones para detectar secciones típicas de fichas
FICHA_SECTION_PATTERNS = [
    r'(?i)(denominación|nombre)\s*:',       # Nombre de asignatura
    r'(?i)(créditos|ects)\s*:',            # Créditos
    r'(?i)(carácter|tipo)\s*:',            # Tipo de asignatura
    r'(?i)(competencias?)\s*:',            # Competencias
    r'(?i)(objetivos?)\s*:',               # Objetivos
    r'(?i)(programa|temario)\s*:',         # Programa
    r'(?i)(metodología)\s*:',              # Metodología
    r'(?i)(evaluación)\s*:',               # Evaluación
    r'(?i)(bibliografía)\s*:',             # Bibliografía
]

# Patrones para detectar información de horarios
HORARIO_SECTION_PATTERNS = [
    r'(?i)(horario)\s*:',                  # Sección de horario
    r'(?i)(aula|sala)\s*:',                # Aula asignada
    r'(?i)(profesor|docente)\s*:',         # Profesor
    r'(?i)(grupo)\s*:',                    # Grupo de clase
]

