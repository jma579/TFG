"""
PDF Text Extraction Module — FICHAS

FINALIDAD:
- Convertir documentos PDF nativos (fichas académicas) en texto plano procesable
- Extraer texto embebido de PDFs académicos españoles
- Proporcionar métricas de calidad y confianza
- Base sólida del pipeline de extracción de FICHAS (no horarios)

ESTRATEGIA:
- Extracción exclusivamente nativa con PyPDF2
- Evaluación de calidad académica (códigos, terminología, estructura)
- Manejo robusto de errores y PDFs encriptados
- Metadatos detallados de procesamiento

RESPONSABILIDADES:
1. Extraer texto nativo de fichas académicas
2. Evaluar calidad específica para contexto académico español
3. Proporcionar metadatos completos de extracción
4. Validar y filtrar contenido por calidad mínima
5. Detectar y manejar PDFs encriptados
"""

from typing import Dict, Any, Optional, Tuple, List
import logging
from pathlib import Path
import time
import re
import PyPDF2
from cleantext import clean


# === Imports actualizados ===
from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ErrorType,
    ExtractionMetadata
)
from core.extraccion.fichas.entities import (
    ExtractionResult
)
from core.extraccion.fichas.constants import (
    DEFAULT_EXTRACTOR_CONFIG, CLEANTEXT_CONFIG,
    ACADEMIC_TERMS, SUBJECT_CODE_PATTERNS,
    CORRUPTION_PATTERNS, NOISE_PATTERNS,
    MIN_CHARACTERS_FOR_USEFUL_TEXT,
    WEIGHT_BASIC_METRICS, WEIGHT_ACADEMIC_PATTERNS, WEIGHT_QUALITY_INDICATORS,
    BASIC_WEIGHT_STRUCTURE, BASIC_WEIGHT_CHAR_QUALITY, BASIC_WEIGHT_WORD_QUALITY,
    ACADEMIC_WEIGHT_CODES, ACADEMIC_WEIGHT_TERMINOLOGY, 
    QUALITY_WEIGHT_COHERENCE, QUALITY_WEIGHT_ERROR_ABSENCE,
    THRESHOLD_EXCELLENT, THRESHOLD_GOOD, THRESHOLD_ACCEPTABLE, THRESHOLD_POOR,
    PENALTY_HIGH_NOISE, PENALTY_CORRUPTION,
    BONUS_ACADEMIC_EXCELLENCE, BONUS_SOLID_STRUCTURE,
    THRESHOLD_STRUCTURE_EXCELLENCE, THRESHOLD_HIGH_NOISE_LEVEL,
    THRESHOLD_SIGNIFICANT_CORRUPTION, THRESHOLD_MULTIPLE_SUBJECT_CODES,
    MINIMUM_VIABLE_SCORE,
)




# =============================================================================
# CLASE PRINCIPAL FICHA EXTRACTOR
# =============================================================================

class FichaExtractor:  #TODO: Modificar los warnings de acuerdo con la estructura de Warning
    """
    Extractor de texto nativo de PDFs académicos españoles.
    
    ARQUITECTURA:
    - Inicialización: Configuración básica, logging y validaciones
    - Extracción: Método principal con validación robusta y manejo de encriptación
    - Evaluación: Assessment avanzado de calidad académica específica
    - Utilidades: Funciones helper especializadas para patrones académicos
    
    FLUJO PRINCIPAL:
    1. Validar archivo PDF de entrada (tamaño, formato, accesibilidad)
    2. Extraer texto nativo con PyPDF2 (manejo de encriptación)
    3. Evaluar calidad específica para contexto académico español
    4. Retornar resultado estructurado con metadatos completos
    5. Detectar patrones académicos (códigos, horarios, aulas)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar extractor de PDF con configuración.
        
        PROPÓSITO:
        - Establecer parámetros de calidad, timeouts y límites
        - Inicializar logging con nivel configurable
        - Configurar validaciones de entrada y thresholds académicos
        
        Args:
            config: Diccionario de configuración personalizada
                    Soporta: log_level, max_pages, stop_after_n_empty_pages,
                    min_alpha_ratio, max_short_words_ratio
        """
        # 1. Configurar logging con nivel personalizable
        self.logger = logging.getLogger(__name__)
        
        # 2. Aplicar configuración personalizada
        self.config = DEFAULT_EXTRACTOR_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # 3. Configurar nivel de logging si se especifica
        if 'log_level' in self.config:
            self.logger.setLevel(getattr(logging, self.config['log_level'].upper(), logging.INFO))
        
        # 4. Inicializar estadísticas
        self.stats = {
            'extractions_total': 0,
            'native_success': 0,
            'failures': 0,
            'avg_processing_time': 0.0,
            'avg_quality_score': 0.0,  # Nueva métrica más útil
        }
        
        self.logger.info("PDFExtractor inicializado correctamente")
        

    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        MÉTODO PRINCIPAL: Extraer texto nativo de PDF académico.
        
        FLUJO DIRECTO PARA PDFs NATIVOS:
        1. Validaciones de entrada (archivo, formato, accesibilidad, encriptación)
        2. Extraer texto nativo exclusivamente con PyPDF2
        3. Evaluar calidad específica para contexto académico español
        4. Si calidad insuficiente → Error claro con contexto específico
        5. Retornar resultado estructurado con metadatos académicos completos
        
        Args:
            pdf_path: Ruta al archivo PDF a procesar
            
        Returns:
            ExtractionResult con texto, calidad, metadatos académicos y estadísticas
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si no es un PDF válido, está encriptado o no contiene texto embebido
            TimeoutError: Si el procesamiento excede el límite de tiempo configurado
        """
        start_time = time.time()
        self.stats['extractions_total'] += 1
        
        try:
            # 1. Validaciones de entrada
            self._validate_pdf_input(pdf_path)
            self.logger.info(f"Iniciando extracción de: {pdf_path}")
            
            # 2. Extraer texto 
            text = self._extract_text(pdf_path)
            
            # 3. Evaluar calidad del texto extraído (evaluación única y completa)
            quality, confidence = self._assess_text_quality(text['text'])
            
            # 4. Verificar si la calidad es suficiente para procesamiento académico
            if quality == ExtractionQuality.UNUSABLE:
                # Si la calidad es inutilizable, fallar claramente
                self.stats['failures'] += 1
                raise ValueError(
                    "PDF no contiene texto nativo de calidad suficiente. "
                    "Debe usar documentos con texto embebido legible, no imágenes escaneadas."
                )
            
            # 5. El texto tiene calidad suficiente, proceder
            self.stats['native_success'] += 1
            final_text = text
            
            # 6. Construir resultado completo
            processing_time = time.time() - start_time
            self._update_processing_time(processing_time)
            
            text_content = final_text['text']
            metadata = self._build_success_metadata(
                quality, confidence, text_content, processing_time, pdf_path, final_text
            )
            
            result = ExtractionResult(
                text=text_content,
                metadata=metadata
            )
            
            # Actualizar estadística de calidad promedio
            self._update_quality_stats(confidence)
            
            self.logger.info(f"Extracción completada: {quality.value}, {confidence:.2f} confianza")
            return result
            
        except Exception as e:
            return self._handle_extraction_error(e, pdf_path, start_time)
        
    def _validate_pdf_input(self, pdf_path: str) -> None:
        """
        Validar archivo PDF de entrada.
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si no es un PDF válido o excede tamaño máximo
        """
        pdf_file = Path(pdf_path)
        
        # Check file exists
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        # Check file size (configurable, default 50MB)
        max_size_mb = self.config.get('max_file_size_mb', 50)
        file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ValueError(f"PDF demasiado grande: {file_size_mb:.1f}MB > {max_size_mb}MB")
        
        # Basic PDF validation
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValueError("Archivo no parece ser un PDF válido")
        except Exception as e:
            raise ValueError(f"Error validando PDF: {e}")
        
    def _extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extractor nativo optimizado para fichas académicas y horarios.

        OBJETIVO: Extraer texto nativo exclusivamente y devolver métricas académicas.

        Returns:
            Dict con texto limpio, páginas con contenido, errores y warnings
            Campos: text, page_count, pages_with_text, errors, warnings
        """
        self.logger.debug(f"Iniciando extracción nativa de: {pdf_path}")
        
        # ESTRUCTURA DE RESULTADO - Solo campos esenciales para PDFs nativos
        result = {
            'text': '',                                    
            'page_count': 0,
            'pages_with_text': 0,                              
            'errors': [],                                 
            'warnings': []
        }
        
        try:
            # Abrir PDF con modo no-estricto para mejor compatibilidad
            with open(pdf_path, 'rb') as file:
                try: 
                    reader = PyPDF2.PdfReader(file, strict=False)
                    total_pages = len(reader.pages)
                    result['page_count'] = total_pages
                    
                    # Manejar PDFs encriptados
                    if reader.is_encrypted:
                        self.logger.debug("PDF encriptado detectado, intentando desencriptación")
                        if not reader.decrypt(""):
                            result['errors'].append("PDF encriptado y no se pudo desencriptar")
                            return result
                    
                    self.logger.debug(f"PDF abierto exitosamente: {total_pages} páginas")

                except Exception as e:
                    self.logger.error(f"Error al abrir PDF: {str(e)}")
                    result['errors'].append(f"Error al abrir PDF: {str(e)}")
                    return result

                # Configuración de límites de procesamiento
                max_pages = self.config.get('max_pages', None)
                stop_after_n_empty_pages = self.config.get('stop_after_n_empty_pages', 5)
                
                # Extraer texto página por página con límites configurables
                page_texts = []
                pages_with_text = 0
                consecutive_empty_pages = 0
                
                pages_to_process = reader.pages[:max_pages] if max_pages else reader.pages
                
                for page_num, page in enumerate(pages_to_process):
                    try:
                        # Extraer texto sin limpieza inicial para evitar doble procesamiento
                        raw_text = page.extract_text()
                        if len((raw_text or "").strip()) > MIN_CHARACTERS_FOR_USEFUL_TEXT:
                            page_texts.append(raw_text)
                            pages_with_text += 1
                            consecutive_empty_pages = 0
                        else:
                            page_texts.append("")
                            consecutive_empty_pages += 1
                            result['warnings'].append(f"Página {page_num + 1}: Poco o ningún texto extraído")
                            # Detener si hay demasiadas páginas vacías consecutivas
                            if consecutive_empty_pages >= stop_after_n_empty_pages:
                                self.logger.debug(f"Deteniendo extracción tras {consecutive_empty_pages} páginas vacías")
                                break
                    except Exception as e:
                        page_texts.append("")
                        consecutive_empty_pages += 1
                        error_msg = f"Página {page_num + 1}: Error de extracción - {str(e)}"
                        result['warnings'].append(error_msg)
                        self.logger.warning(error_msg)
                
                # Combinar y limpiar texto una sola vez
                non_empty_pages = [page for page in page_texts if page.strip()]
                
                if non_empty_pages:
                    combined_text = '\n\n'.join(non_empty_pages)
                    # Aplicar limpieza una sola vez al texto combinado
                    final_text = self._text_cleaner(combined_text)
                else:
                    final_text = ""
                    result['warnings'].append("Ninguna página contiene texto extraíble")
                
                # Construir resultado final
                result['text'] = final_text
                result['page_count'] = total_pages
                result['pages_with_text'] = pages_with_text
                
                # Logging informativo del proceso de extracción
                self.logger.debug(f"Extracción nativa completada: {len(final_text)} chars, {pages_with_text}/{total_pages} páginas con contenido")
                
                return result
            
        except Exception as e:
            # MANEJO DE ERRORES GENERALES
            error_msg = f"Error general en extracción nativa: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
            return result
    
    def _assess_text_quality(self, text: str) -> tuple[ExtractionQuality, float]:
        """
        Evaluador de calidad del texto extraído para documentos académicos.

        OBJETIVO: Evaluar la calidad del texto extraído y asignar nivel de confianza.
        ENFOQUE: Análisis multidimensional específico para fichas académicas y horarios.

        PROCESO DETALLADO:
        1. Validaciones básicas y filtros de entrada
        2. Calcular métricas básicas de longitud y estructura
        3. Evaluar coherencia y patrones académicos específicos
        4. Detectar indicadores de calidad académica
        5. Calcular score ponderado final
        6. Mapear a categorías ExtractionQuality con confianza

        Args:
            text: Texto extraído a evaluar

        Returns:
            Tupla (ExtractionQuality, confidence_score_0_to_1)
        """
        # ESTRUCTURA DE RESULTADO - Valores por defecto para casos extremos
        quality = ExtractionQuality.UNUSABLE
        confidence = 0.0
        
        try:
            # Validacion básica de texto usable
            if not text or len(text.strip()) < MIN_CHARACTERS_FOR_USEFUL_TEXT:
                return quality, confidence
            
            # Calcular métricas básicas de longitud y estructura
            basic_metrics = self._get_basic_metrics(text)
            
            # Evaluar coherencia y patrones académicos específicos
            academic_metrics = self._get_academic_patterns(text)
            
            # Detectar indicadores de calidad académica
            quality_indicators = self._get_quality_indicators(text, basic_metrics, academic_metrics)
            
            # Calcular score simplificado para contexto PDF-nativo
            basic_score = self._calculate_basic_score(basic_metrics)
            academic_score = self._calculate_academic_score(academic_metrics)  
            quality_score = self._calculate_quality_score(quality_indicators)
            
            # Score base combinado con pesos por categoría
            base_score = (
                basic_score * WEIGHT_BASIC_METRICS +
                academic_score * WEIGHT_ACADEMIC_PATTERNS +
                quality_score * WEIGHT_QUALITY_INDICATORS
            )
            
            # Aplicar bonificaciones y penalizaciones usando constantes
            final_score = base_score
            
            # Bonificación por excelencia académica
            if (academic_metrics.get('has_academic_structure', False) and 
                academic_metrics.get('subject_code_count', 0) > THRESHOLD_MULTIPLE_SUBJECT_CODES):
                final_score += BONUS_ACADEMIC_EXCELLENCE
            # Bonificación por estructura sólida
            if quality_indicators.get('structure_score', 0) > THRESHOLD_STRUCTURE_EXCELLENCE:
                final_score += BONUS_SOLID_STRUCTURE
            # Penalización por alto ruido
            if quality_indicators.get('noise_level', 0) > THRESHOLD_HIGH_NOISE_LEVEL:
                final_score -= PENALTY_HIGH_NOISE
            # Penalización por corrupción significativa
            if quality_indicators.get('char_corruption_ratio', 0) > THRESHOLD_SIGNIFICANT_CORRUPTION:
                final_score -= PENALTY_CORRUPTION
            # 4. Normalización final y garantías mínimas
            final_score = max(0.0, min(1.0, final_score))  # Clamp [0.0, 1.0]
            
            # Garantizar score mínimo para texto procesable
            if basic_metrics.get('char_count', 0) >= MIN_CHARACTERS_FOR_USEFUL_TEXT:
                final_score = max(final_score, MINIMUM_VIABLE_SCORE)
            
            # PASO 6: Mapear a categorías ExtractionQuality con confianza
            # Mapeo a categorías ExtractionQuality (thresholds ya validados en constructor)
            if final_score >= THRESHOLD_EXCELLENT:
                quality = ExtractionQuality.EXCELLENT
                # Confianza alta con bonos por excelencia académica
                range_size = 1.0 - THRESHOLD_EXCELLENT
                range_position = (final_score - THRESHOLD_EXCELLENT) / range_size if range_size > 0 else 0.0
                base_confidence = 0.85 + range_position * 0.15  # 0.85-1.0
                academic_bonus = 0.05 if academic_metrics.get('has_academic_structure', False) else 0.0
                confidence = min(1.0, base_confidence + academic_bonus)
                
            elif final_score >= THRESHOLD_GOOD:
                quality = ExtractionQuality.GOOD
                # Confianza media-alta con ajustes por coherencia
                range_size = THRESHOLD_EXCELLENT - THRESHOLD_GOOD
                range_position = (final_score - THRESHOLD_GOOD) / range_size
                base_confidence = 0.70 + range_position * 0.15  # 0.70-0.85
                coherence_bonus = quality_indicators.get('coherence_score', 0) * 0.05
                confidence = min(0.89, base_confidence + coherence_bonus)
                
            elif final_score >= THRESHOLD_ACCEPTABLE:
                quality = ExtractionQuality.ACCEPTABLE
                # Confianza media con penalizaciones por ruido
                range_size = THRESHOLD_GOOD - THRESHOLD_ACCEPTABLE
                range_position = (final_score - THRESHOLD_ACCEPTABLE) / range_size
                base_confidence = 0.50 + range_position * 0.20  # 0.50-0.70
                noise_penalty = quality_indicators.get('noise_level', 0) * 0.10
                confidence = max(0.50, base_confidence - noise_penalty)
                
            elif final_score >= THRESHOLD_POOR:
                quality = ExtractionQuality.POOR
                # Confianza baja con descuentos por corrupción de texto
                range_size = THRESHOLD_ACCEPTABLE - THRESHOLD_POOR
                range_position = (final_score - THRESHOLD_POOR) / range_size
                base_confidence = 0.30 + range_position * 0.20  # 0.30-0.50
                corruption_penalty = quality_indicators.get('char_corruption_ratio', 0) * 0.15
                confidence = max(0.30, base_confidence - corruption_penalty)
                
            else:
                quality = ExtractionQuality.UNUSABLE
                # Confianza muy baja proporcional al score residual
                confidence = max(0.05, final_score / THRESHOLD_POOR * 0.25) if THRESHOLD_POOR > 0 else 0.05
            
            return quality, confidence
            
        except Exception as e:
            # MANEJO DE ERRORES - Retorno seguro con calidad mínima
            self.logger.error(f"Error evaluando calidad de texto: {e}")
            return ExtractionQuality.UNUSABLE, 0.0

    def _update_processing_time(self, processing_time: float) -> None:
        """Actualizar estadística de tiempo promedio de procesamiento."""
        total = self.stats['extractions_total']
        current_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = ((current_avg * (total - 1)) + processing_time) / total

    def _build_success_metadata(self, quality: ExtractionQuality, confidence: float, text_content: str, processing_time: float,
                               pdf_path: str, extraction_result: Dict) -> ExtractionMetadata:
        """Construir metadatos para extracción exitosa de PDF nativo."""
        # Determinar si realmente hay texto embebido útil
        has_embedded_text = len(text_content.strip()) >= MIN_CHARACTERS_FOR_USEFUL_TEXT
        
        metadata_dict = {
            'quality': quality.value,
            'confidence': confidence,
            'status': ProcessingStatus.COMPLETED.value,
            'processing_time_seconds': processing_time,
            'page_count': extraction_result.get('page_count', 0),
            'file_size_mb': Path(pdf_path).stat().st_size / (1024 * 1024),
            'has_embedded_text': has_embedded_text,
            'char_count': len(text_content),
            'word_count': len(text_content.split()) if text_content else 0,
            'errors': extraction_result.get('errors', []),
            'warnings': extraction_result.get('warnings', [])
        }
        
        # Añadir pages_with_text si está disponible
        if 'pages_with_text' in extraction_result:
            metadata_dict['pages_with_text'] = extraction_result['pages_with_text']
            
        return ExtractionMetadata(**metadata_dict)

    def _update_quality_stats(self, quality_score: float) -> None:
        """Actualizar estadística de calidad promedio."""
        total = self.stats['extractions_total']
        current_avg = self.stats['avg_quality_score']
        self.stats['avg_quality_score'] = ((current_avg * (total - 1)) + quality_score) / total

    def _handle_extraction_error(self, error: Exception, pdf_path: str, 
                                start_time: float) -> ExtractionResult:
        """Manejar errores de extracción de forma centralizada."""
        self.stats['failures'] += 1
        self.logger.error(f"Error en extracción: {error}")
        
        # Determinar tipo de error específico
        error_type = ErrorType.UNKNOWN_ERROR
        if isinstance(error, FileNotFoundError):
            error_type = ErrorType.FILE_NOT_FOUND
        elif isinstance(error, ValueError):
            # Mapear errores específicos de PDF nativo
            error_type = ErrorType.INVALID_PDF
        elif isinstance(error, TimeoutError):
            error_type = ErrorType.PROCESSING_TIMEOUT
        
        # Calcular tamaño de archivo de forma segura
        try:
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        except:
            file_size_mb = 0.0
        
        # Construir metadatos de error ajustados para PDF nativo
        metadata = ExtractionMetadata(
            quality=ExtractionQuality.UNUSABLE,
            confidence=0.0,
            status=ProcessingStatus.FAILED,
            processing_time_seconds=time.time() - start_time,
            page_count=0,
            file_size_mb=file_size_mb,
            has_embedded_text=False,
            char_count=0,
            word_count=0,
            errors=[str(error)]
        )
        
        return ExtractionResult(
            text="",
            metadata=metadata,
            error_type=error_type,
            error_message=str(error)
        )

    
    # =============================================================================
    # FUNCIONES AUXILIARES PARA MODULARIDAD
    # =============================================================================
    
    def _get_basic_metrics(self, text: str) -> Dict[str, Any]:
        """
        Calcular métricas básicas de longitud y estructura del texto.
        
        Optimizado para documentos académicos españoles (fichas y horarios).
        
        MÉTRICAS CALCULADAS:
        - Conteos fundamentales: char_count, word_count, line_count, paragraph_count
        - Ratios de caracteres: alpha_ratio, digit_ratio, space_ratio, punct_ratio
        - Análisis de palabras: avg_word_length, short_words_ratio, long_words_ratio
        - Estructura: avg_line_length, has_structure (párrafos múltiples + saltos razonables)
        
        Args:
            text: Texto a analizar
            
        Returns:
            Dict con métricas básicas de calidad textual (15 métricas totales)
        """
        # Conteos básicos fundamentales
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        lines = text.split('\n')
        line_count = len(lines)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Análisis de tipos de caracteres para calidad
        alpha_chars = sum(1 for c in text if c.isalpha())
        digit_chars = sum(1 for c in text if c.isdigit())
        space_chars = sum(1 for c in text if c.isspace())
        punct_chars = sum(1 for c in text if c in '.,;:!?()-[]{}')
        
        # Calcular ratios importantes para evaluación de calidad
        alpha_ratio = alpha_chars / char_count if char_count > 0 else 0
        digit_ratio = digit_chars / char_count if char_count > 0 else 0
        space_ratio = space_chars / char_count if char_count > 0 else 0
        punct_ratio = punct_chars / char_count if char_count > 0 else 0
        
        # Análisis de distribución de palabras
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            short_words = sum(1 for w in words if len(w) <= 2)  # Posibles artefactos de extracción
            long_words = sum(1 for w in words if len(w) > 15)   # Palabras sospechosamente largas
            short_words_ratio = short_words / word_count
            long_words_ratio = long_words / word_count
        else:
            avg_word_length = 0
            short_words_ratio = 0
            long_words_ratio = 0
        
        # Evaluación de estructura del documento académico
        has_multiple_paragraphs = paragraph_count > 1
        has_reasonable_line_breaks = line_count > 1 and line_count < char_count / 10
        avg_line_length = char_count / line_count if line_count > 0 else 0
        has_structure = has_multiple_paragraphs and has_reasonable_line_breaks
        
        # Construir diccionario de métricas básicas
        basic_metrics = {
            # Conteos fundamentales
            'char_count': char_count,
            'word_count': word_count,
            'line_count': line_count,
            'paragraph_count': paragraph_count,
            
            # Ratios de tipos de caracteres
            'alpha_ratio': alpha_ratio,
            'digit_ratio': digit_ratio,
            'space_ratio': space_ratio,
            'punct_ratio': punct_ratio,
            
            # Análisis de palabras
            'avg_word_length': avg_word_length,
            'short_words_ratio': short_words_ratio,
            'long_words_ratio': long_words_ratio,
            
            # Estructura del documento
            'avg_line_length': avg_line_length,
            'has_structure': has_structure
        }
        
        return basic_metrics

    def _get_academic_patterns(self, text: str) -> Dict[str, Any]:
        """
        Detectar patrones académicos específicos en texto de documentos universitarios.
        
        Optimizado para fichas académicas y horarios españoles.
        
        PATRONES DETECTADOS:
        - Códigos de asignatura: subject_code_count, has_subject_codes
        - Terminología académica: academic_term_matches, academic_density  
        - Elementos de horario: time_pattern_count, weekday_count, classroom_count
        - Información docente: professor_mention_count, academic_email_count
        - Indicadores de calidad: has_schedule_format, has_academic_structure
        
        Args:
            text: Texto a analizar
            
        Returns:
            Dict con métricas de patrones académicos (11 métricas totales)
        """
        # Detección mejorada de códigos de asignatura españoles
        # Patrones: G111, M123, A456, B789, etc. (1-3 letras + 2-4 dígitos)
        # Patrones de códigos de asignatura
        subject_codes = []
        for pat in SUBJECT_CODE_PATTERNS:
            subject_codes += re.findall(pat, text)
        subject_code_count = len(subject_codes)
        has_subject_codes = subject_code_count > 0

        # Términos académicos
        text_lower = text.lower()
        academic_term_matches = sum(1 for t in ACADEMIC_TERMS if t in text_lower)
        word_count = max(len(text.split()), 1)
        academic_density = (academic_term_matches / word_count) * 100

        # Información docente y académica
        # Detectar títulos y menciones de profesores
        title_patterns = re.findall(
            r'\b(Dr\.?|Dra\.?|Prof\.?|Profesor|Profesora|Catedrático|Catedrática|'
            r'Coordinador|Coordinadora)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', 
            text
        )
        
        # Detectar emails académicos españoles mejorado
        academic_emails = re.findall(
            r'\b[a-zA-Z0-9._%+-]+@(?:'
            r'[a-zA-Z0-9.-]*(?:universidad|univ|uc3m|upm|ucm|uam|urjc|uah|usal|uva|ugr)' 
            r'|[a-zA-Z0-9.-]*\.(?:es|edu)'
            r')\b',
            text, re.IGNORECASE
        )
        
        # Indicadores de calidad académica compuestos
        has_academic_structure = academic_term_matches > 2 and has_subject_codes
        
        # Construir diccionario de métricas académicas
        academic_metrics = {
            # Códigos académicos
            'subject_code_count': subject_code_count,
            'has_subject_codes': has_subject_codes,
            
            # Terminología académica
            'academic_term_matches': academic_term_matches,
            'academic_density': academic_density,

            # Información docente
            'professor_mention_count': len(title_patterns),
            'academic_email_count': len(academic_emails),
            
            # Indicadores de calidad académica
            'has_academic_structure': has_academic_structure
        }
        
        return academic_metrics

    def _get_quality_indicators(self, text: str, basic_metrics: Dict[str, Any], academic_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detectar indicadores específicos de calidad académica en el texto extraído.
        
        Combina métricas básicas y académicas para evaluar la calidad del contenido.
        
        INDICADORES EVALUADOS:
        - Información estructurada: has_structured_content, structure_score
        - Coherencia semántica: coherence_score, semantic_quality  
        - Ausencia de artefactos: artifact_error_indicators, char_corruption_ratio
        - Proporción útil vs ruido: useful_content_ratio, noise_level
        
        Args:
            text: Texto a analizar
            basic_metrics: Métricas básicas del texto
            academic_metrics: Métricas de patrones académicos
            
        Returns:
            Dict con indicadores de calidad académica (10 métricas totales)
        """
        # 1. Evaluación de información estructurada
        # Determinar si el texto tiene estructura académica reconocible
        has_paragraphs = basic_metrics.get('paragraph_count', 0) > 1
        has_academic_codes = academic_metrics.get('has_subject_codes', False)
        has_academic_terms = academic_metrics.get('academic_term_matches', 0) > 0
        
        structure_indicators = sum([
            has_paragraphs,
            has_academic_codes,
            has_academic_terms,
            basic_metrics.get('has_structure', False)
        ])
        
        has_structured_content = structure_indicators >= 2
        structure_score = min(structure_indicators / 5.0, 1.0)  # Normalizado 0-1
        
        # 2. Evaluación de coherencia semántica
        # Detectar patrones que indican texto coherente vs artefactos
        char_count = basic_metrics.get('char_count', 0)
        word_count = basic_metrics.get('word_count', 0)
        
        # Ratio de caracteres alfabéticos (texto real vs símbolos extraños)
        alpha_ratio = basic_metrics.get('alpha_ratio', 0)
        
        # Longitud promedio de palabra razonable (2-12 caracteres típico español)
        avg_word_length = basic_metrics.get('avg_word_length', 0)
        reasonable_word_length = 2 <= avg_word_length <= 12
        
        # Ratio de palabras muy cortas (posibles artefactos de extracción)
        short_words_ratio = basic_metrics.get('short_words_ratio', 0)
        low_short_words = short_words_ratio < 0.3  # Menos del 30% palabras muy cortas
        
        # Score de coherencia basado en múltiples factores
        coherence_factors = [
            alpha_ratio >= 0.7,        # Al menos 70% caracteres alfabéticos
            reasonable_word_length,     # Longitud de palabra razonable
            low_short_words,           # Pocas palabras sospechosamente cortas
            word_count >= 10           # Mínimo contenido para evaluar
        ]
        
        coherence_score = sum(coherence_factors) / len(coherence_factors)
        semantic_quality = coherence_score >= 0.5
        
        # 3. Detección de artefactos y errores de procesamiento
        # Patrones típicos de artefactos en PDFs nativos procesados incorrectamente
        text_lower = text.lower()
        
        # Caracteres problemáticos y artefactos comunes en procesamiento PDF
        artifact_error_count = 0
        text_lower = text.lower()
        for pat in (CORRUPTION_PATTERNS + NOISE_PATTERNS):
            artifact_error_count += len(re.findall(pat, text_lower))
        artifact_error_indicators = artifact_error_count
        char_count = basic_metrics.get("char_count", 0) or 0
        char_corruption_ratio = min(artifact_error_count / max(char_count, 1), 1.0)
        
        # 4. Evaluación de proporción útil vs ruido
        # Determinar qué porcentaje del texto es contenido académico útil
        
        # Contenido útil: términos académicos + códigos + estructura (normalizado)
        useful_indicators = [
            min(academic_metrics.get('academic_term_matches', 0) / 3.0, 1.0),  # Max 3 términos = 1.0
            min(academic_metrics.get('subject_code_count', 0) / 2.0, 1.0),     # Max 2 códigos = 1.0  
            min(academic_metrics.get('professor_mention_count', 0) / 1.0, 1.0), # Max 1 profesor = 1.0
            1.0 if has_structured_content else 0.0  # Estructura binaria
        ]
        
        # Promedio ponderado de indicadores útiles
        weights = [0.35, 0.35, 0.15, 0.15]  # Suma = 1.0
        useful_content_ratio = sum(indicator * weight for indicator, weight in zip(useful_indicators, weights))
        
        # Nivel de ruido inverso con ajuste para documentos académicos
        # Cálculo adaptativo de ruido por espacios y patrones académicos
        normal_space_ratio = 0.15  # Ratio normal de espacios en texto español
        current_space_ratio = basic_metrics.get('space_ratio', 0)
        space_deviation = abs(current_space_ratio - normal_space_ratio)
        space_noise = min(space_deviation * 3.0, 1.0)  # Penalizar desviación significativa
        
        '''
        # Si hay patrones de horario detectados, reducir peso de penalizaciones
        has_schedule_format = academic_metrics.get('has_schedule_format', False)
        schedule_weight_reduction = 0.5 if has_schedule_format else 1.0
        '''
        
        noise_factors = [
            char_corruption_ratio,                              # 0-1 (más = peor)
            # short_words_ratio * schedule_weight_reduction,      # Reducir peso si hay horarios
            # (1.0 - alpha_ratio) * schedule_weight_reduction,    # Reducir peso si hay horarios
            space_noise                                         # 0-1 (desviación de espacios normales)
        ]
        
        noise_level = sum(noise_factors) / len(noise_factors)
        
        # Construir diccionario de indicadores de calidad
        quality_indicators = {
            # Información estructurada
            'has_structured_content': has_structured_content,
            'structure_score': structure_score,
            
            # Coherencia semántica  
            'coherence_score': coherence_score,
            'semantic_quality': semantic_quality,
            
            # Ausencia de artefactos de procesamiento
            'artifact_error_indicators': artifact_error_indicators,
            'char_corruption_ratio': char_corruption_ratio,
            
            # Proporción útil vs ruido
            'useful_content_ratio': useful_content_ratio,
            'noise_level': noise_level
        }
        
        return quality_indicators

    def _calculate_basic_score(self, basic_metrics: Dict[str, Any]) -> float:
        """Calcular score de métricas básicas de forma simplificada."""
        # Componente de estructura
        structure_component = (
            min(basic_metrics.get('paragraph_count', 0) / 3.0, 1.0) * 
            BASIC_WEIGHT_STRUCTURE
        )
        
        # Componente de calidad de caracteres
        char_quality_component = (
            basic_metrics.get('alpha_ratio', 0) * 0.5 +
            (1.0 - basic_metrics.get('short_words_ratio', 1.0)) * 0.3 +
            min(basic_metrics.get('punct_ratio', 0) * 10, 1.0) * 0.2
        ) * BASIC_WEIGHT_CHAR_QUALITY
        
        # Componente de calidad de palabras simplificado
        avg_len = basic_metrics.get('avg_word_length', 0)
        if 4 <= avg_len <= 8:
            word_score = 1.0  # Rango óptimo para español
        elif 2 <= avg_len < 4 or 8 < avg_len <= 12:
            word_score = 0.7  # Aceptable
        else:
            word_score = 0.3  # Problemático
            
        word_quality_component = word_score * BASIC_WEIGHT_WORD_QUALITY
        
        return structure_component + char_quality_component + word_quality_component

    def _calculate_academic_score(self, academic_metrics: Dict[str, Any]) -> float:
        """Calcular score de patrones académicos de forma simplificada."""
        # Componente de códigos académicos
        codes_component = (
            min(academic_metrics.get('subject_code_count', 0) / 3.0, 1.0) * 
            ACADEMIC_WEIGHT_CODES
        )
        
        # Componente de terminología académica
        terminology_component = (
            min(academic_metrics.get('academic_density', 0) / 100.0, 1.0) * 0.7 +
            (1.0 if academic_metrics.get('academic_term_matches', 0) > 0 else 0.0) * 0.3
        ) * ACADEMIC_WEIGHT_TERMINOLOGY

        return codes_component + terminology_component

    def _calculate_quality_score(self, quality_indicators: Dict[str, Any]) -> float:
        """Calcular score de indicadores de calidad de forma simplificada."""
        # Componente de coherencia
        coherence_component = (
            quality_indicators.get('coherence_score', 0) * 
            QUALITY_WEIGHT_COHERENCE
        )
        
        # Componente de ausencia de errores
        error_absence_component = (
            (1.0 - quality_indicators.get('char_corruption_ratio', 1.0)) *
            QUALITY_WEIGHT_ERROR_ABSENCE
        )
        
        return coherence_component + error_absence_component

    def get_stats(self) -> Dict[str, Any]:
        """
        Estadísticas de uso para monitoreo y debugging.
        
        MÉTRICAS ÚTILES:
        - Total de extracciones realizadas
        - Tasa de éxito de extracción nativa
        - Tiempos promedio de procesamiento
        - Distribución de calidades obtenidas
        - Errores más frecuentes
        """
        return self.stats.copy()

    def _text_cleaner(self, text: Optional[str]) -> str:
        """
        Limpiador de texto usando clean-text library.
        Optimizado para documentos académicos PDF españoles.
        """
        if not text:
            return ""
        return clean(text, **CLEANTEXT_CONFIG, normalize_whitespace=True, strip_lines=True, no_emoji=True)


# =============================================================================
# INSTANCIA GLOBAL PARA FACILIDAD DE USO
# =============================================================================

# Instancia global tipada del extractor para uso conveniente
ficha_extractor: Optional[FichaExtractor] = None

def get_ficha_extractor() -> FichaExtractor:
    """
    Factory function para obtener instancia global del extractor de fichas.
    
    Returns:
        FichaExtractor: Instancia configurada para extracción de fichas académicas
    """
    global ficha_extractor
    if ficha_extractor is None:
        ficha_extractor = FichaExtractor()
    return ficha_extractor