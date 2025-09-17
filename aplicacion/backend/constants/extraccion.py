from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


# =============================================================================
# ENUMS PARA EXTRACCIÓN OCR
# =============================================================================

class ExtractionMethod(str, Enum):
    """Métodos disponibles para extracción de texto de PDFs."""
    NATIVE = "native"          # PyPDF2 - Extracción nativa de texto embebido
    OCR = "ocr"               # Tesseract - OCR para PDFs escaneados
    HYBRID = "hybrid"         # Combinación de ambos métodos
    FALLBACK = "fallback"     # Método de respaldo usado cuando falla el primario


class ExtractionQuality(str, Enum):
    """Niveles de calidad del texto extraído."""
    EXCELLENT = "excellent"   # >95% confianza, texto limpio y completo
    GOOD = "good"            # 80-95% confianza, texto mayormente correcto
    ACCEPTABLE = "acceptable" # 60-80% confianza, errores menores
    POOR = "poor"            # 30-60% confianza, errores evidentes
    UNUSABLE = "unusable"    # <30% confianza, texto ilegible o vacío


class ProcessingStatus(str, Enum):
    """Estados del procesamiento de extracción."""
    PENDING = "pending"       # En cola para procesamiento
    PROCESSING = "processing" # Siendo procesado actualmente
    COMPLETED = "completed"   # Completado exitosamente
    FAILED = "failed"        # Falló el procesamiento
    TIMEOUT = "timeout"      # Excedió tiempo límite
    CANCELLED = "cancelled"  # Cancelado por usuario/sistema


class ErrorType(str, Enum):
    """Tipos de errores durante la extracción."""
    FILE_NOT_FOUND = "file_not_found"           # Archivo no existe
    INVALID_PDF = "invalid_pdf"                 # PDF corrupto o inválido
    OCR_ENGINE_ERROR = "ocr_engine_error"      # Error en motor OCR
    DEPENDENCY_MISSING = "dependency_missing"   # Falta dependencia (Tesseract)
    INSUFFICIENT_MEMORY = "insufficient_memory" # Memoria insuficiente
    PROCESSING_TIMEOUT = "processing_timeout"   # Timeout durante procesamiento
    UNKNOWN_ERROR = "unknown_error"            # Error no identificado

MIN_CHARACTERS_FOR_USEFUL_TEXT = 5  # Mínimo de caracteres para considerar texto útil


# =============================================================================
# DATACLASSES PARA RESULTADOS ESTRUCTURADOS DEL OCR
# =============================================================================

@dataclass
class ExtractionMetadata:
    """Metadatos optimizados del proceso de extracción."""
    # Campos obligatorios (sin defaults)
    method: ExtractionMethod                    # Método finalmente utilizado
    methods_attempted: List[ExtractionMethod]  # Métodos que se intentaron
    processing_time_seconds: float             # Tiempo total de procesamiento
    page_count: int                            # Número total de páginas
    file_size_mb: float                        # Tamaño del archivo en MB
    tesseract_available: bool                  # Si Tesseract está disponible
    errors: List[str]                          # Lista de errores encontrados
    
    # Campos opcionales (con defaults)
    has_embedded_text: Optional[bool] = None   # Si contiene texto embebido (detectado)
    char_count: Optional[int] = None           # Total de caracteres extraídos
    word_count: Optional[int] = None           # Total de palabras extraídas
    warnings: List[str] = None                 # Lista de advertencias (opcional)
    
    def __post_init__(self):
        """Inicializar campos opcionales si son None."""
        if self.warnings is None:
            self.warnings = []


@dataclass 
class ExtractionResult:
    """Resultado completo de una extracción de texto."""
    # Resultado principal
    text: str                         # Texto extraído del PDF
    quality: ExtractionQuality       # Nivel de calidad evaluado
    confidence: float                 # Confianza en el resultado (0.0-1.0)
    status: ProcessingStatus         # Estado final del procesamiento
    
    # Metadatos optimizados
    metadata: ExtractionMetadata     # Información detallada del proceso
    
    # Información de error (si aplica)
    error_type: Optional[ErrorType] = None  # Tipo de error si falló
    error_message: Optional[str] = None     # Mensaje descriptivo del error
    
    @property
    def success(self) -> bool:
        """Indica si la extracción fue exitosa."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def is_usable(self) -> bool:
        """Indica si el texto extraído es utilizable."""
        return self.quality in [
            ExtractionQuality.EXCELLENT,
            ExtractionQuality.GOOD,
            ExtractionQuality.ACCEPTABLE
        ]
    
    @property
    def processing_time_seconds(self) -> float:
        """Tiempo de procesamiento en segundos."""
        return self.metadata.processing_time_seconds


# =============================================================================
# CONFIGURACIÓN Y CONSTANTES POR DEFECTO
# =============================================================================

DEFAULT_OCR_CONFIG = {
    'timeout_seconds': 300,          # 5 minutos máximo
    'min_text_length': 10,           # Mínimo 10 caracteres
    'quality_threshold': 0.6,        # Umbral de calidad aceptable
    'ocr_lang': 'spa',              # Idioma para OCR (español)
    'ocr_psm': 6,                   # Page segmentation mode (entero)
    'ocr_oem': 3,                   # OCR Engine mode
    'ocr_dpi': 300,                 # DPI para conversión de imágenes
    'max_file_size_mb': 50,         # Máximo 50MB
}


# =============================================================================
# CONSTANTES PARA EVALUACIÓN DE CALIDAD DE TEXTO
# =============================================================================

# Pesos principales para categorías de calidad
WEIGHT_BASIC_METRICS = 0.3          # 30% - Métricas básicas de texto
WEIGHT_ACADEMIC_PATTERNS = 0.4      # 40% - Patrones académicos específicos
WEIGHT_QUALITY_INDICATORS = 0.3     # 30% - Indicadores de calidad y coherencia

# Pesos internos para métricas básicas
BASIC_WEIGHT_STRUCTURE = 0.4        # 40% - Estructura del documento
BASIC_WEIGHT_CHAR_QUALITY = 0.35    # 35% - Calidad de caracteres
BASIC_WEIGHT_WORD_QUALITY = 0.25    # 25% - Calidad de palabras

# Pesos internos para patrones académicos
ACADEMIC_WEIGHT_CODES = 0.4         # 40% - Códigos de asignatura
ACADEMIC_WEIGHT_TERMINOLOGY = 0.35  # 35% - Terminología académica
ACADEMIC_WEIGHT_SCHEDULE = 0.25     # 25% - Formatos de horario

# Pesos internos para indicadores de calidad
QUALITY_WEIGHT_COHERENCE = 0.5      # 50% - Coherencia semántica
QUALITY_WEIGHT_ERROR_ABSENCE = 0.5  # 50% - Ausencia de errores

# Umbrales para mapeo de ExtractionQuality
THRESHOLD_EXCELLENT = 0.85          # >= 85% = EXCELLENT
THRESHOLD_GOOD = 0.70               # 70-84% = GOOD
THRESHOLD_ACCEPTABLE = 0.50         # 50-69% = ACCEPTABLE
THRESHOLD_POOR = 0.30               # 30-49% = POOR
                                    # < 30% = UNUSABLE

# Bonificaciones de score
BONUS_ACADEMIC_EXCELLENCE = 0.1     # +10% por excelencia académica
BONUS_SOLID_STRUCTURE = 0.05        # +5% por estructura sólida

# Penalizaciones de score
PENALTY_HIGH_NOISE = 0.2            # -20% por alto nivel de ruido
PENALTY_CORRUPTION = 0.15           # -15% por corrupción significativa

# Umbrales para aplicar bonificaciones y penalizaciones
THRESHOLD_STRUCTURE_EXCELLENCE = 0.7     # Umbral para bonificación de estructura
THRESHOLD_HIGH_NOISE_LEVEL = 0.5         # Umbral para penalización por ruido
THRESHOLD_SIGNIFICANT_CORRUPTION = 0.1   # Umbral para penalización por corrupción
THRESHOLD_MULTIPLE_SUBJECT_CODES = 2     # Mínimo códigos para excelencia académica

# Garantías de score mínimo
MINIMUM_VIABLE_SCORE = 0.2          # Score mínimo para texto procesable


# =============================================================================
# PATRONES REGEX PARA PARSING ACADÉMICO
# =============================================================================

# Umbral mínimo de confianza global
MIN_CONFIDENCE = 0.3

# Patrones para códigos de asignaturas
SUBJECT_CODE_PATTERNS = [
    r'\b[A-Z]{1,3}\d{3,4}\b',           # G1234, MAT101, etc. (formato básico)
    r'\b[A-Z]{1,3}[-\s]\d{3,4}\b',      # G-1234, G 1234 (con separadores)
    r'\([A-Z]{1,3}\d{3,4}\)',           # (G1234) en paréntesis
    r'\b[A-Z]{1,3}\.\d{3,4}\b',         # G.1234 con punto
    r'\b[A-Z]{1,3}\d{3,4}[A-Z]?\b'      # G1234A con sufijo opcional
]

# Patrones para rangos de tiempo
TIME_PATTERNS = [
    r'(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})',     # 09:00-11:00
    r'(\d{1,2}):(\d{2})\s+a\s+(\d{1,2}):(\d{2})',        # 09:00 a 11:00
    r'(\d{1,2})\s*[-–—]\s*(\d{1,2})\s*h',                 # 9-11h
    r'(\d{1,2})h\s*[-–—]\s*(\d{1,2})h',                   # 9h-11h
    r'de\s+(\d{1,2}):(\d{2})\s+a\s+(\d{1,2}):(\d{2})'    # de 09:00 a 11:00
]

# Patrones para días de la semana
DAY_PATTERNS = [
    r'\b(Lunes|lunes|Martes|martes|Miércoles|miércoles|Jueves|jueves|Viernes|viernes|Sábado|sábado|Domingo|domingo)\b',  # Días completos
    r'\b([LMXJVSD])\b',                                    # Abreviaciones de una letra
    r'\b(Lu|Ma|Mi|Ju|Vi|Sa|Do)\b',                         # Abreviaciones de dos letras
    r'\b([LMXJVSD])\s*[-–—]\s*([LMXJVSD])\b',             # Rangos L-V
    r'\b(lunes|Lu)\s+a\s+(viernes|Vi)\b'                   # "lunes a viernes"
]

# Patrones para profesores
PROFESSOR_PATTERNS = [
    r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b',  # Nombre simple: "Juan García"
    r'\b(Dr\.?|Dra\.?|Prof\.?|Profesor|Profesora)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
    r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*[@.]',  # Con contexto de email
    r'Profesor:\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',  # "Profesor: Nombre"
    r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de|del|la|los|las)\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',  # Con artículos
]

# Patrones para aulas y ubicaciones
CLASSROOM_PATTERNS = [
    # PATRONES MEJORADOS PARA CASOS COMPLEJOS
    r'\b(Laboratorio|Lab\.?)\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+?)(?:\s+(\d+[A-Z]?))?\b',  # "Laboratorio de Simulación 1"
    r'\b(Seminario|Aula|Sala)\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)\b',                    # "Seminario de Informática"
    r'\b(Aula|Sala)\s+(Magna|Principal|Central|Grande|Pequeña)\b',                        # "Aula Magna", "Sala Principal"
    r'\b([A-Z]{2,5}\d+[A-Z]?)\b',                                                         # "LSC1", "INFO2A", "TELEC3"
    # PATRONES ORIGINALES (MÁS ESPECÍFICOS)
    r'\b(Aula|Sala|Lab\.?|Laboratorio)\s+([A-Z]?\d+[A-Z]?)\b',                          # Aula 101, Lab A2
    r'\b(Edificio|Ed\.?)\s+([A-Z]+),?\s*(Aula|Sala)?\s*(\d+[A-Z]?)\b',                  # Edificio A, Aula 101
    r'\b(Seminario|Biblioteca|Despacho)\s+([A-Z]?\d*[A-Z]?)\b',                         # Seminario A
    r'\bAula\s+([A-Z]+\d+[A-Z]*)\b',                                                    # Aula A101B
    r'\b([A-Z]\d{2,3}[A-Z]?)\b(?=\s|$)'                                                 # A101, B205A (standalone)
]


# =============================================================================
# DATACLASSES PARA ENTIDADES DEL PARSING
# =============================================================================

@dataclass
class SubjectCode:
    """Representa un código de asignatura detectado."""
    code: str                           # Código de la asignatura (ej: "G1234")
    full_match: str                     # Texto completo que hizo match
    confidence: float                   # Confianza de la detección (0.0-1.0)
    position: Tuple[int, int]          # Posición en el texto (inicio, fin)
    
    def __post_init__(self):
        """Validación básica de los datos."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence debe estar entre 0.0 y 1.0")


@dataclass
class Schedule:
    """Representa un horario detectado."""
    time_start: Optional[str] = None    # Hora de inicio (ej: "09:00")
    time_end: Optional[str] = None      # Hora de fin (ej: "11:00")
    days: List[str] = None              # Lista de días (ej: ["lunes", "miércoles"])
    raw_text: str = ""                  # Texto original detectado
    confidence: float = 0.0             # Confianza de la detección
    position: Tuple[int, int] = (0, 0)  # Posición en el texto
    
    def __post_init__(self):
        """Inicializar campos opcionales."""
        if self.days is None:
            self.days = []
    
    @property
    def is_valid(self) -> bool:
        """Verifica si el horario tiene información válida."""
        return bool(self.time_start and self.time_end)
    
    @property
    def day_of_week(self) -> Optional[str]:
        """Retorna el primer día de la lista (compatibilidad con parsing.py)."""
        return self.days[0] if self.days else None
    
    @property  
    def day_of_week_number(self) -> int:
        """Retorna número del día para ordenamiento (0=Lunes, 6=Domingo)."""
        day_map = {
            'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Jueves': 3, 
            'Viernes': 4, 'Sábado': 5, 'Domingo': 6
        }
        return day_map.get(self.day_of_week, 999) if self.day_of_week else 999
    
    @property
    def start_time(self) -> Optional[str]:
        """Alias para time_start (compatibilidad con parsing.py)."""
        return self.time_start
        
    @property  
    def end_time(self) -> Optional[str]:
        """Alias para time_end (compatibilidad con parsing.py)."""
        return self.time_end


@dataclass
class Professor:
    """Representa información de un profesor detectada."""
    name: str                           # Nombre del profesor
    title: Optional[str] = None         # Título académico (Dr., Prof., etc.)
    full_match: str = ""                # Texto completo que hizo match
    confidence: float = 0.0             # Confianza de la detección
    position: Tuple[int, int] = (0, 0)  # Posición en el texto
    
    @property
    def display_name(self) -> str:
        """Retorna el nombre completo con título si existe."""
        if self.title:
            return f"{self.title} {self.name}"
        return self.name


@dataclass
class Classroom:
    """Representa información de un aula detectada."""
    identifier: str                     # Identificador del aula (ej: "A101")
    type: Optional[str] = None          # Tipo (Aula, Lab, Seminario, etc.)
    building: Optional[str] = None      # Edificio si está especificado
    full_match: str = ""                # Texto completo que hizo match
    confidence: float = 0.0             # Confianza de la detección
    position: Tuple[int, int] = (0, 0)  # Posición en el texto
    
    @property
    def display_name(self) -> str:
        """Retorna el nombre completo del aula."""
        parts = []
        if self.type:
            parts.append(self.type)
        parts.append(self.identifier)
        if self.building:
            parts.append(f"(Ed. {self.building})")
        return " ".join(parts)


@dataclass
class ParsedAcademicContent:
    """Resultado completo del parsing de contenido académico."""
    # Entidades detectadas
    subject_codes: List[SubjectCode] = None
    schedules: List[Schedule] = None
    professors: List[Professor] = None
    classrooms: List[Classroom] = None
    
    # Metadatos del parsing
    confidence_score: float = 0.0           # Confianza general (0.0-1.0)
    parsing_errors: List[str] = None        # Lista de errores encontrados
    detected_patterns: Dict[str, int] = None # Conteo de patrones detectados
    processing_time_ms: Optional[float] = None # Tiempo de procesamiento
    
    def __post_init__(self):
        """Inicializar campos opcionales si son None."""
        if self.subject_codes is None:
            self.subject_codes = []
        if self.schedules is None:
            self.schedules = []
        if self.professors is None:
            self.professors = []
        if self.classrooms is None:
            self.classrooms = []
        if self.parsing_errors is None:
            self.parsing_errors = []
        if self.detected_patterns is None:
            self.detected_patterns = {}
    
    @property
    def total_entities(self) -> int:
        """Retorna el número total de entidades detectadas."""
        return (len(self.subject_codes) + len(self.schedules) + 
                len(self.professors) + len(self.classrooms))
    
    @property
    def is_successful(self) -> bool:
        """Indica si el parsing fue exitoso (tiene al menos una entidad)."""
        return self.total_entities > 0 and self.confidence_score > 0.0
    
    @property
    def overall_confidence(self) -> float:
        """Alias para confidence_score (compatibilidad con parsing.py)."""
        return self.confidence_score


