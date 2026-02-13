"""
PDF Text Extraction Module para Fichas Académicas.

Extrae texto embebido de PDFs académicos españoles con evaluación de calidad.
Estrategia exclusivamente nativa con PyPDF2.
"""

from typing import Dict, Any, Optional
import logging
from pathlib import Path
import time
import re
import PyPDF2
from cleantext import clean

from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ErrorType,
    ExtractionMetadata, Warning
)
from core.extraccion.fichas.entities import ExtractionResult
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
    MINIMUM_VIABLE_SCORE, CLEANTEXT_NOISE_REGEX, CLEANTEXT_NOISE_REPLACE,
    CURRENCY_SYMBOLS_PATTERN, EMOJI_PATTERN, EXCESSIVE_LINEBREAKS_PATTERN,
    EXCESSIVE_LINEBREAKS_REPLACE, NON_ACADEMIC_EMAIL_PATTERN
)


class FichaExtractor:  
    """
    Extractor de texto nativo de PDFs académicos españoles.
    
    Flujo: Validación → Extracción → Evaluación de calidad → Metadatos
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar extractor con configuración opcional.
        
        Args:
            config: Parámetros personalizados (log_level, max_pages, thresholds)
        """
        self.logger = logging.getLogger(__name__)
        
        self.config = DEFAULT_EXTRACTOR_CONFIG.copy()
        if config:
            self.config.update(config)
        
        if 'log_level' in self.config:
            self.logger.setLevel(getattr(logging, self.config['log_level'].upper(), logging.INFO))
        
        self.stats = {
            'extractions_total': 0,
            'native_success': 0,
            'failures': 0,
            'avg_processing_time': 0.0,
            'avg_quality_score': 0.0,
        }
        
        self.logger.info("FichaExtractor inicializado")
        

    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        Extraer texto nativo de PDF académico con evaluación de calidad.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            ExtractionResult con texto, calidad y metadatos
            
        Raises:
            FileNotFoundError: Archivo no existe
            ValueError: PDF inválido o sin texto embebido
        """
        start_time = time.time()
        self.stats['extractions_total'] += 1
        
        try:
            self._validate_pdf_input(pdf_path)
            self.logger.info(f"Iniciando extracción de: {pdf_path}")
            
            text = self._extract_text(pdf_path)
            
            quality, confidence = self._assess_text_quality(text['text'])
            
            if quality == ExtractionQuality.UNUSABLE:
                self.stats['failures'] += 1
                raise ValueError(
                    "PDF no contiene texto nativo de calidad suficiente. "
                    "Debe usar documentos con texto embebido legible, no imágenes escaneadas."
                )
            
            self.stats['native_success'] += 1
            final_text = text
            
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
            
            self._update_quality_stats(confidence)
            
            self.logger.info(f"Extracción completada: {quality.value}, {confidence:.2f} confianza")
            return result
            
        except Exception as e:
            return self._handle_extraction_error(e, pdf_path, start_time)
        
    def _validate_pdf_input(self, pdf_path: str) -> None:
        """
        Validar archivo PDF de entrada.
        
        Raises:
            FileNotFoundError: Archivo no existe
            ValueError: PDF inválido o demasiado grande
        """
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
        
        max_size_mb = self.config.get('max_file_size_mb', 50)
        file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ValueError(f"PDF demasiado grande: {file_size_mb:.1f}MB > {max_size_mb}MB")
        
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValueError("Archivo no parece ser un PDF válido")
        except Exception as e:
            raise ValueError(f"Error validando PDF: {e}")
        
    def _extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extraer texto nativo usando PyPDF2.

        Returns:
            Dict con texto limpio, conteo de páginas, errores y warnings
        """
        self.logger.debug(f"Iniciando extracción nativa de: {pdf_path}")
        
        result = {
            'text': '',
            'page_count': 0,
            'pages_with_text': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                try: 
                    reader = PyPDF2.PdfReader(file, strict=False)
                    total_pages = len(reader.pages)
                    result['page_count'] = total_pages
                    
                    if reader.is_encrypted:
                        self.logger.debug("PDF encriptado detectado")
                        if not reader.decrypt(""):
                            result['errors'].append("PDF encriptado y no se pudo desencriptar")
                            return result
                    
                    self.logger.debug(f"PDF abierto: {total_pages} páginas")

                except Exception as e:
                    self.logger.error(f"Error al abrir PDF: {str(e)}")
                    result['errors'].append(f"Error al abrir PDF: {str(e)}")
                    return result

                max_pages = self.config.get('max_pages', None)
                stop_after_n_empty_pages = self.config.get('stop_after_n_empty_pages', 5)
                
                page_texts = []
                pages_with_text = 0
                consecutive_empty_pages = 0
                
                pages_to_process = reader.pages[:max_pages] if max_pages else reader.pages
                
                for page_num, page in enumerate(pages_to_process):
                    try:
                        raw_text = page.extract_text()
                        if len((raw_text or "").strip()) > MIN_CHARACTERS_FOR_USEFUL_TEXT:
                            page_texts.append(raw_text)
                            pages_with_text += 1
                            consecutive_empty_pages = 0
                        else:
                            page_texts.append("")
                            consecutive_empty_pages += 1
                            result['warnings'].append(Warning(
                                message=f"Página {page_num + 1}: Poco o ningún texto extraído",
                                severity="minor"
                            ))
                            if consecutive_empty_pages >= stop_after_n_empty_pages:
                                self.logger.debug(f"Deteniendo tras {consecutive_empty_pages} páginas vacías")
                                break
                    except Exception as e:
                        page_texts.append("")
                        consecutive_empty_pages += 1
                        error_msg = f"Página {page_num + 1}: Error de extracción - {str(e)}"
                        result['warnings'].append(Warning(
                            message=error_msg,
                            severity="severe"
                        ))
                        self.logger.warning(error_msg)
                
                non_empty_pages = [page for page in page_texts if page.strip()]
                
                if non_empty_pages:
                    combined_text = '\n\n'.join(non_empty_pages)
                    final_text = self._text_cleaner(combined_text)
                else:
                    final_text = ""
                    result['warnings'].append(Warning(
                        message="Ninguna página contiene texto extraíble",
                        severity="severe"
                    ))
                
                result['text'] = final_text
                result['page_count'] = total_pages
                result['pages_with_text'] = pages_with_text
                
                self.logger.debug(f"Extracción completada: {len(final_text)} chars, {pages_with_text}/{total_pages} páginas")
                
                return result
            
        except Exception as e:
            error_msg = f"Error en extracción: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
            return result
    
    def _assess_text_quality(self, text: str) -> tuple[ExtractionQuality, float]:
        """
        Evaluar calidad del texto extraído para documentos académicos.

        Análisis multidimensional: métricas básicas, patrones académicos y calidad.

        Args:
            text: Texto extraído

        Returns:
            Tupla (ExtractionQuality, confidence_score_0_to_1)
        """
        quality = ExtractionQuality.UNUSABLE
        confidence = 0.0
        
        try:
            if not text or len(text.strip()) < MIN_CHARACTERS_FOR_USEFUL_TEXT:
                return quality, confidence
            
            basic_metrics = self._get_basic_metrics(text)
            academic_metrics = self._get_academic_patterns(text)
            quality_indicators = self._get_quality_indicators(text, basic_metrics, academic_metrics)
            
            basic_score = self._calculate_basic_score(basic_metrics)
            academic_score = self._calculate_academic_score(academic_metrics)  
            quality_score = self._calculate_quality_score(quality_indicators)
            
            base_score = (
                basic_score * WEIGHT_BASIC_METRICS +
                academic_score * WEIGHT_ACADEMIC_PATTERNS +
                quality_score * WEIGHT_QUALITY_INDICATORS
            )
            
            final_score = base_score
            
            # Bonificaciones
            if (academic_metrics.get('has_academic_structure', False) and 
                academic_metrics.get('subject_code_count', 0) > THRESHOLD_MULTIPLE_SUBJECT_CODES):
                final_score += BONUS_ACADEMIC_EXCELLENCE
            if quality_indicators.get('structure_score', 0) > THRESHOLD_STRUCTURE_EXCELLENCE:
                final_score += BONUS_SOLID_STRUCTURE
            
            # Penalizaciones
            if quality_indicators.get('noise_level', 0) > THRESHOLD_HIGH_NOISE_LEVEL:
                final_score -= PENALTY_HIGH_NOISE
            if quality_indicators.get('char_corruption_ratio', 0) > THRESHOLD_SIGNIFICANT_CORRUPTION:
                final_score -= PENALTY_CORRUPTION
            
            final_score = max(0.0, min(1.0, final_score))
            
            if basic_metrics.get('char_count', 0) >= MIN_CHARACTERS_FOR_USEFUL_TEXT:
                final_score = max(final_score, MINIMUM_VIABLE_SCORE)
            
            # Mapear a categorías
            if final_score >= THRESHOLD_EXCELLENT:
                quality = ExtractionQuality.EXCELLENT
                range_size = 1.0 - THRESHOLD_EXCELLENT
                range_position = (final_score - THRESHOLD_EXCELLENT) / range_size if range_size > 0 else 0.0
                base_confidence = 0.85 + range_position * 0.15
                academic_bonus = 0.05 if academic_metrics.get('has_academic_structure', False) else 0.0
                confidence = min(1.0, base_confidence + academic_bonus)
                
            elif final_score >= THRESHOLD_GOOD:
                quality = ExtractionQuality.GOOD
                range_size = THRESHOLD_EXCELLENT - THRESHOLD_GOOD
                range_position = (final_score - THRESHOLD_GOOD) / range_size
                base_confidence = 0.70 + range_position * 0.15
                coherence_bonus = quality_indicators.get('coherence_score', 0) * 0.05
                confidence = min(0.89, base_confidence + coherence_bonus)
                
            elif final_score >= THRESHOLD_ACCEPTABLE:
                quality = ExtractionQuality.ACCEPTABLE
                range_size = THRESHOLD_GOOD - THRESHOLD_ACCEPTABLE
                range_position = (final_score - THRESHOLD_ACCEPTABLE) / range_size
                base_confidence = 0.50 + range_position * 0.20
                noise_penalty = quality_indicators.get('noise_level', 0) * 0.10
                confidence = max(0.50, base_confidence - noise_penalty)
                
            elif final_score >= THRESHOLD_POOR:
                quality = ExtractionQuality.POOR
                range_size = THRESHOLD_ACCEPTABLE - THRESHOLD_POOR
                range_position = (final_score - THRESHOLD_POOR) / range_size
                base_confidence = 0.30 + range_position * 0.20
                corruption_penalty = quality_indicators.get('char_corruption_ratio', 0) * 0.15
                confidence = max(0.30, base_confidence - corruption_penalty)
                
            else:
                quality = ExtractionQuality.UNUSABLE
                confidence = max(0.05, final_score / THRESHOLD_POOR * 0.25) if THRESHOLD_POOR > 0 else 0.05
            
            return quality, confidence
            
        except Exception as e:
            self.logger.error(f"Error evaluando calidad: {e}")
            return ExtractionQuality.UNUSABLE, 0.0

    def _update_processing_time(self, processing_time: float) -> None:
        """Actualizar estadística de tiempo promedio."""
        total = self.stats['extractions_total']
        current_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = ((current_avg * (total - 1)) + processing_time) / total

    def _build_success_metadata(self, quality: ExtractionQuality, confidence: float, text_content: str, 
                               processing_time: float, pdf_path: str, extraction_result: Dict) -> ExtractionMetadata:
        """Construir metadatos para extracción exitosa."""
        has_embedded_text = len(text_content.strip()) >= MIN_CHARACTERS_FOR_USEFUL_TEXT
        
        metadata_dict = {
            'quality': quality,
            'confidence': confidence,
            'status': ProcessingStatus.COMPLETED,
            'processing_time_seconds': processing_time,
            'page_count': extraction_result.get('page_count', 0),
            'file_size_mb': Path(pdf_path).stat().st_size / (1024 * 1024),
            'has_embedded_text': has_embedded_text,
            'char_count': len(text_content),
            'word_count': len(text_content.split()) if text_content else 0,
            'errors': extraction_result.get('errors', []),
            'warnings': extraction_result.get('warnings', [])
        }
        
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
        
        error_type = ErrorType.UNKNOWN_ERROR
        if isinstance(error, FileNotFoundError):
            error_type = ErrorType.FILE_NOT_FOUND
        elif isinstance(error, ValueError):
            error_type = ErrorType.INVALID_PDF
        elif isinstance(error, TimeoutError):
            error_type = ErrorType.PROCESSING_TIMEOUT
        
        try:
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        except:
            file_size_mb = 0.0
        
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
            errors=[str(error)],
            warnings=[
                Warning(
                    message=f"Error de extracción: {str(error)}",
                    severity="severe"
                )
            ]
        )
        
        return ExtractionResult(
            text="",
            metadata=metadata,
            error_type=error_type,
            error_message=str(error)
        )

    def _get_basic_metrics(self, text: str) -> Dict[str, Any]:
        """
        Calcular métricas básicas de longitud y estructura del texto.
        
        Métricas: conteos, ratios de caracteres, análisis de palabras, estructura.
        """
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        lines = text.split('\n')
        line_count = len(lines)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        alpha_chars = sum(1 for c in text if c.isalpha())
        digit_chars = sum(1 for c in text if c.isdigit())
        space_chars = sum(1 for c in text if c.isspace())
        punct_chars = sum(1 for c in text if c in '.,;:!?()-[]{}')
        
        alpha_ratio = alpha_chars / char_count if char_count > 0 else 0
        digit_ratio = digit_chars / char_count if char_count > 0 else 0
        space_ratio = space_chars / char_count if char_count > 0 else 0
        punct_ratio = punct_chars / char_count if char_count > 0 else 0
        
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            short_words = sum(1 for w in words if len(w) <= 2)
            long_words = sum(1 for w in words if len(w) > 15)
            short_words_ratio = short_words / word_count
            long_words_ratio = long_words / word_count
        else:
            avg_word_length = 0
            short_words_ratio = 0
            long_words_ratio = 0
        
        has_multiple_paragraphs = paragraph_count > 1
        has_reasonable_line_breaks = line_count > 1 and line_count < char_count / 10
        avg_line_length = char_count / line_count if line_count > 0 else 0
        has_structure = has_multiple_paragraphs and has_reasonable_line_breaks
        
        return {
            'char_count': char_count,
            'word_count': word_count,
            'line_count': line_count,
            'paragraph_count': paragraph_count,
            'alpha_ratio': alpha_ratio,
            'digit_ratio': digit_ratio,
            'space_ratio': space_ratio,
            'punct_ratio': punct_ratio,
            'avg_word_length': avg_word_length,
            'short_words_ratio': short_words_ratio,
            'long_words_ratio': long_words_ratio,
            'avg_line_length': avg_line_length,
            'has_structure': has_structure
        }

    def _get_academic_patterns(self, text: str) -> Dict[str, Any]:
        """
        Detectar patrones académicos específicos en texto universitario español.
        
        Patrones: códigos de asignatura, terminología, información docente.
        """
        subject_codes = []
        for pat in SUBJECT_CODE_PATTERNS:
            subject_codes += re.findall(pat, text)
        subject_code_count = len(subject_codes)
        has_subject_codes = subject_code_count > 0

        text_lower = text.lower()
        academic_term_matches = sum(1 for t in ACADEMIC_TERMS if t in text_lower)
        word_count = max(len(text.split()), 1)
        academic_density = (academic_term_matches / word_count) * 100

        title_patterns = re.findall(
            r'\b(Dr\.?|Dra\.?|Prof\.?|Profesor|Profesora|Catedrático|Catedrática|'
            r'Coordinador|Coordinadora)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', 
            text
        )
        
        academic_emails = re.findall(
            r'\b[a-zA-Z0-9._%+-]+@(?:'
            r'[a-zA-Z0-9.-]*(?:universidad|univ|uc3m|upm|ucm|uam|urjc|uah|usal|uva|ugr)' 
            r'|[a-zA-Z0-9.-]*\.(?:es|edu)'
            r')\b',
            text, re.IGNORECASE
        )
        
        has_academic_structure = academic_term_matches > 2 and has_subject_codes
        
        return {
            'subject_code_count': subject_code_count,
            'has_subject_codes': has_subject_codes,
            'academic_term_matches': academic_term_matches,
            'academic_density': academic_density,
            'professor_mention_count': len(title_patterns),
            'academic_email_count': len(academic_emails),
            'has_academic_structure': has_academic_structure
        }

    def _get_quality_indicators(self, text: str, basic_metrics: Dict[str, Any], 
                               academic_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detectar indicadores de calidad académica en el texto.
        
        Combina métricas básicas y académicas para evaluar calidad del contenido.
        """
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
        structure_score = min(structure_indicators / 5.0, 1.0)
        
        char_count = basic_metrics.get('char_count', 0)
        word_count = basic_metrics.get('word_count', 0)
        alpha_ratio = basic_metrics.get('alpha_ratio', 0)
        avg_word_length = basic_metrics.get('avg_word_length', 0)
        reasonable_word_length = 2 <= avg_word_length <= 12
        short_words_ratio = basic_metrics.get('short_words_ratio', 0)
        low_short_words = short_words_ratio < 0.3
        
        coherence_factors = [
            alpha_ratio >= 0.7,
            reasonable_word_length,
            low_short_words,
            word_count >= 10
        ]
        
        coherence_score = sum(coherence_factors) / len(coherence_factors)
        semantic_quality = coherence_score >= 0.5
        
        text_lower = text.lower()
        
        artifact_error_count = 0
        for pat in (CORRUPTION_PATTERNS + NOISE_PATTERNS):
            artifact_error_count += len(re.findall(pat, text_lower))
        artifact_error_indicators = artifact_error_count
        char_count = basic_metrics.get("char_count", 0) or 0
        char_corruption_ratio = min(artifact_error_count / max(char_count, 1), 1.0)
        
        useful_indicators = [
            min(academic_metrics.get('academic_term_matches', 0) / 3.0, 1.0),
            min(academic_metrics.get('subject_code_count', 0) / 2.0, 1.0),
            min(academic_metrics.get('professor_mention_count', 0) / 1.0, 1.0),
            1.0 if has_structured_content else 0.0
        ]
        
        weights = [0.35, 0.35, 0.15, 0.15]
        useful_content_ratio = sum(indicator * weight for indicator, weight in zip(useful_indicators, weights))
        
        normal_space_ratio = 0.15
        current_space_ratio = basic_metrics.get('space_ratio', 0)
        space_deviation = abs(current_space_ratio - normal_space_ratio)
        space_noise = min(space_deviation * 3.0, 1.0)
        
        noise_factors = [
            char_corruption_ratio,
            space_noise
        ]
        
        noise_level = sum(noise_factors) / len(noise_factors)
        
        return {
            'has_structured_content': has_structured_content,
            'structure_score': structure_score,
            'coherence_score': coherence_score,
            'semantic_quality': semantic_quality,
            'artifact_error_indicators': artifact_error_indicators,
            'char_corruption_ratio': char_corruption_ratio,
            'useful_content_ratio': useful_content_ratio,
            'noise_level': noise_level
        }

    def _calculate_basic_score(self, basic_metrics: Dict[str, Any]) -> float:
        """Calcular score de métricas básicas."""
        structure_component = (
            min(basic_metrics.get('paragraph_count', 0) / 3.0, 1.0) * 
            BASIC_WEIGHT_STRUCTURE
        )
        
        char_quality_component = (
            basic_metrics.get('alpha_ratio', 0) * 0.5 +
            (1.0 - basic_metrics.get('short_words_ratio', 1.0)) * 0.3 +
            min(basic_metrics.get('punct_ratio', 0) * 10, 1.0) * 0.2
        ) * BASIC_WEIGHT_CHAR_QUALITY
        
        avg_len = basic_metrics.get('avg_word_length', 0)
        if 4 <= avg_len <= 8:
            word_score = 1.0
        elif 2 <= avg_len < 4 or 8 < avg_len <= 12:
            word_score = 0.7
        else:
            word_score = 0.3
            
        word_quality_component = word_score * BASIC_WEIGHT_WORD_QUALITY
        
        return structure_component + char_quality_component + word_quality_component

    def _calculate_academic_score(self, academic_metrics: Dict[str, Any]) -> float:
        """Calcular score de patrones académicos."""
        codes_component = (
            min(academic_metrics.get('subject_code_count', 0) / 3.0, 1.0) * 
            ACADEMIC_WEIGHT_CODES
        )
        
        terminology_component = (
            min(academic_metrics.get('academic_density', 0) / 100.0, 1.0) * 0.7 +
            (1.0 if academic_metrics.get('academic_term_matches', 0) > 0 else 0.0) * 0.3
        ) * ACADEMIC_WEIGHT_TERMINOLOGY

        return codes_component + terminology_component

    def _calculate_quality_score(self, quality_indicators: Dict[str, Any]) -> float:
        """Calcular score de indicadores de calidad."""
        coherence_component = (
            quality_indicators.get('coherence_score', 0) * 
            QUALITY_WEIGHT_COHERENCE
        )
        
        error_absence_component = (
            (1.0 - quality_indicators.get('char_corruption_ratio', 1.0)) *
            QUALITY_WEIGHT_ERROR_ABSENCE
        )
        
        return coherence_component + error_absence_component

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas de uso para monitoreo."""
        return self.stats.copy()

    def _text_cleaner(self, text: Optional[str]) -> str:
        """
        Limpiar texto usando clean-text library.
        Optimizado para documentos académicos PDF españoles.
        """
        if not text:
            return ""
        
        try:
            text = clean(
                text,
                **CLEANTEXT_CONFIG,
                reg=CLEANTEXT_NOISE_REGEX,
                reg_replace=CLEANTEXT_NOISE_REPLACE
            )
        except Exception as e:
            self.logger.warning(f"cleantext falló, usando texto sin limpiar: {e}")
        
        text = re.sub(CURRENCY_SYMBOLS_PATTERN, '', text)
        text = re.sub(EMOJI_PATTERN, '', text, flags=re.UNICODE)
        text = re.sub(NON_ACADEMIC_EMAIL_PATTERN, '', text, flags=re.IGNORECASE)
        text = re.sub(
            EXCESSIVE_LINEBREAKS_PATTERN,
            EXCESSIVE_LINEBREAKS_REPLACE,
            text
        )
        
        text = text.strip()
        
        return text


ficha_extractor: Optional[FichaExtractor] = None

def get_ficha_extractor() -> FichaExtractor:
    """
    Factory function para obtener instancia global del extractor.
    
    Returns:
        FichaExtractor: Instancia configurada
    """
    global ficha_extractor
    if ficha_extractor is None:
        ficha_extractor = FichaExtractor()
    return ficha_extractor