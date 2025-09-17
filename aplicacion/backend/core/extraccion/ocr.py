"""
OCR Text Extraction Module

FINALIDAD:
- Convertir documentos PDF en texto plano procesable
- Manejar tanto PDFs nativos como escaneados
- Proporcionar métricas de calidad y confianza
- Ser la base sólida del pipeline de extracción

ESTRATEGIA:
- Enfoque híbrido: PyPDF2 + Tesseract OCR
- Fallback inteligente entre métodos
- Evaluación de calidad automática
- Manejo robusto de errores

RESPONSABILIDADES:
1. Extraer texto de PDFs con múltiples métodos
2. Evaluar calidad del texto extraído
3. Proporcionar metadatos de extracción completos
4. Manejar casos de fallo gracefully
"""

from typing import Dict, Any, Optional, Tuple, List, Union
import logging
from pathlib import Path
from datetime import datetime
import time
import re
import os
import PyPDF2
from cleantext import clean

# OCR dependencies (with graceful fallback if not installed)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError as e:
    TESSERACT_AVAILABLE = False
    _missing_deps = str(e)

from constants.extraccion import (
    ExtractionMethod, ExtractionQuality, ExtractionResult,
    ProcessingStatus, ErrorType, ExtractionMetadata,
    DEFAULT_OCR_CONFIG, MIN_CHARACTERS_FOR_USEFUL_TEXT,
    WEIGHT_BASIC_METRICS, WEIGHT_ACADEMIC_PATTERNS, WEIGHT_QUALITY_INDICATORS,
    BASIC_WEIGHT_STRUCTURE, BASIC_WEIGHT_CHAR_QUALITY, BASIC_WEIGHT_WORD_QUALITY,
    ACADEMIC_WEIGHT_CODES, ACADEMIC_WEIGHT_TERMINOLOGY, ACADEMIC_WEIGHT_SCHEDULE,
    QUALITY_WEIGHT_COHERENCE, QUALITY_WEIGHT_ERROR_ABSENCE,
    THRESHOLD_EXCELLENT, THRESHOLD_GOOD, THRESHOLD_ACCEPTABLE, THRESHOLD_POOR,
    BONUS_ACADEMIC_EXCELLENCE, BONUS_SOLID_STRUCTURE,
    PENALTY_HIGH_NOISE, PENALTY_CORRUPTION,
    THRESHOLD_STRUCTURE_EXCELLENCE, THRESHOLD_HIGH_NOISE_LEVEL,
    THRESHOLD_SIGNIFICANT_CORRUPTION, THRESHOLD_MULTIPLE_SUBJECT_CODES,
    MINIMUM_VIABLE_SCORE
)




# =============================================================================
# CLASE PRINCIPAL OCR EXTRACTOR
# =============================================================================

class OCRExtractor:
    """
    Extractor de texto principal con estrategia híbrida.
    
    ARQUITECTURA:
    - Inicialización: Configuración de dependencias externas
    - Extracción: Método principal con fallback automático  
    - Evaluación: Assessment de calidad del texto
    - Utilidades: Funciones helper para validación
    
    FLUJO PRINCIPAL:
    1. Validar archivo de entrada
    2. Intentar extracción nativa (PyPDF2)
    3. Si falla o calidad baja → Fallback a OCR (Tesseract)
    4. Evaluar calidad final
    5. Retornar resultado con metadatos
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None, config: Optional[Dict] = None):
        """
        Inicializar extractor con configuración.
        
        PROPÓSITO:
        - Configurar dependencias externas (Tesseract path)
        - Establecer parámetros de calidad y timeouts
        - Inicializar logging y estadísticas
        
        Args:
            tesseract_cmd: Ruta al ejecutable de Tesseract (auto-detectar si None)
            config: Diccionario de configuración personalizada
        """
        # 1. Configurar logging
        self.logger = logging.getLogger(__name__)
    
        # 2. Configuración por defecto desde constants
        self._default_config = DEFAULT_OCR_CONFIG.copy()
        
        # 3. Aplicar configuración personalizada
        self.config = self._default_config.copy()
        if config:
            self.config.update(config)
        
        # 4. Configurar Tesseract
        self.tesseract_cmd = tesseract_cmd
        
        # 5. Inicializar estadísticas
        self.stats = {
            'extractions_total': 0,
            'native_success': 0,
            'ocr_success': 0,
            'failures': 0,
            'avg_processing_time': 0.0,
        }
        
        # 6. Configurar y verificar Tesseract
        self._setup_tesseract()
        
        self.logger.info("OCRExtractor inicializado correctamente")
    
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
        
        # Check file extension
        if pdf_file.suffix.lower() != '.pdf':
            raise ValueError(f"Archivo debe ser PDF, recibido: {pdf_file.suffix}")
        
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
    
    def _setup_tesseract(self) -> bool:
        """
        Configurar Tesseract OCR y verificar disponibilidad.
        
        Returns:
            bool: True si Tesseract está disponible y configurado
        """
        if not TESSERACT_AVAILABLE:
            self.logger.warning(f"Dependencias OCR no disponibles: {_missing_deps}")
            return False
        
        # Configurar comando Tesseract si se especificó
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        
        # Verificar que Tesseract funciona
        try:
            version = pytesseract.get_tesseract_version()
            self.logger.info(f"Tesseract OCR configurado correctamente: v{version}")
            return True
        except Exception as e:
            self.logger.error(f"Error configurando Tesseract: {e}")
            return False
    
    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        MÉTODO PRINCIPAL: Extraer texto de PDF con estrategia híbrida.
        
        FLUJO DE DECISIÓN:
        1. Validaciones de entrada (archivo existe, es PDF, tamaño razonable)
        2. Intentar extracción nativa con PyPDF2
        3. Evaluar calidad del resultado nativo
        4. Si calidad insuficiente → Intentar OCR con Tesseract
        5. Seleccionar mejor resultado disponible
        6. Calcular métricas finales de calidad y confianza
        7. Retornar resultado estructurado con metadatos completos
        
        Args:
            pdf_path: Ruta al archivo PDF a procesar
            
        Returns:
            ExtractionResult con texto, calidad, metadatos y estadísticas
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el archivo no es un PDF válido
            TimeoutError: Si el procesamiento excede el límite de tiempo
        """
        start_time = time.time()
        self.stats['extractions_total'] += 1
        
        try:
            # 1. Validaciones de entrada
            self._validate_pdf_input(pdf_path)
            self.logger.info(f"Iniciando extracción de: {pdf_path}")
            
            # 2. Intentar extracción nativa
            native_result = self._extract_native_text(pdf_path)
            
            # 3. Evaluar calidad nativa
            native_acceptable = self._is_text_quality_acceptable(native_result)
            
            # 4. Decidir si usar OCR como fallback
            final_result = native_result
            method_used = ExtractionMethod.NATIVE
            
            if not native_acceptable and TESSERACT_AVAILABLE:
                self.logger.info("Calidad nativa insuficiente, intentando OCR...")
                ocr_result = self._extract_with_ocr(pdf_path)
                
                if ocr_result and self._is_text_quality_acceptable(ocr_result):
                    final_result = ocr_result
                    method_used = ExtractionMethod.OCR
                    self.stats['ocr_success'] += 1
                else:
                    # Usar nativo aunque sea de baja calidad
                    method_used = ExtractionMethod.FALLBACK
                    self.stats['native_success'] += 1
            else:
                self.stats['native_success'] += 1
            
            # 5. Evaluar calidad final
            quality, confidence = self._assess_text_quality(final_result['text'])
            
            # 6. Construir resultado completo
            processing_time = time.time() - start_time
            self._update_processing_time(processing_time)
            
            # Calcular estadísticas del texto extraído
            text_content = final_result['text']
            
            metadata = ExtractionMetadata(
                method=method_used,
                methods_attempted=final_result.get('methods_attempted', [method_used]),
                processing_time_seconds=processing_time,
                page_count=final_result.get('page_count', 0),
                file_size_mb=Path(pdf_path).stat().st_size / (1024 * 1024),
                has_embedded_text=final_result.get('has_embedded_text'),
                char_count=len(text_content) if text_content else 0,
                word_count=len(text_content.split()) if text_content else 0,
                tesseract_available=TESSERACT_AVAILABLE,
                errors=final_result.get('errors', []),
                warnings=final_result.get('warnings', [])
            )
            
            result = ExtractionResult(
                text=text_content,
                quality=quality,
                confidence=confidence,
                status=ProcessingStatus.COMPLETED,
                metadata=metadata
            )
            
            self.logger.info(f"Extracción completada: {quality.value}, {confidence:.2f} confianza")
            return result
            
        except Exception as e:
            # Error handling
            self.stats['failures'] += 1
            self.logger.error(f"Error en extracción: {e}")
            
            error_type = ErrorType.UNKNOWN_ERROR
            if isinstance(e, FileNotFoundError):
                error_type = ErrorType.FILE_NOT_FOUND
            elif isinstance(e, ValueError):
                error_type = ErrorType.INVALID_PDF
            elif isinstance(e, TimeoutError):
                error_type = ErrorType.PROCESSING_TIMEOUT
            
            # Intentar calcular tamaño de archivo para metadatos de error
            try:
                file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            except:
                file_size_mb = 0.0
            
            metadata = ExtractionMetadata(
                method=ExtractionMethod.NATIVE,
                methods_attempted=[ExtractionMethod.NATIVE],
                processing_time_seconds=time.time() - start_time,
                page_count=0,
                file_size_mb=file_size_mb,
                char_count=0,
                word_count=0,
                tesseract_available=TESSERACT_AVAILABLE,
                errors=[str(e)]
            )
            
            return ExtractionResult(
                text="",
                quality=ExtractionQuality.UNUSABLE,
                confidence=0.0,
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error_type=error_type,
                error_message=str(e)
            )
    
    def _update_processing_time(self, processing_time: float) -> None:
        """Actualizar estadística de tiempo promedio de procesamiento."""
        total = self.stats['extractions_total']
        current_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = ((current_avg * (total - 1)) + processing_time) / total
    
    def _extract_native_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extractor nativo optimizado para fichas académicas y horarios.

        OBJETIVO: Extraer texto nativo y devolver métricas para que extract_from_pdf decida si usar OCR como fallback.

        Returns:
            Dict con texto, métricas de calidad y metadatos para decisión OCR
        """
        self.logger.debug(f"Iniciando extracción nativa de: {pdf_path}")
        
        # ESTRUCTURA DE RESULTADO - Solo campos esenciales
        result = {
            'text': '',                                    
            'page_count': 0,                              
            'methods_attempted': [ExtractionMethod.NATIVE],
            'errors': [],                                 
            'warnings': [],                              
            'quality_metrics': {
                'total_chars': 0,           
                'pages_with_text': 0,       
                'text_density': 0.0,        
                'text_coverage': 0.0       
            }
        }
        
        try:
            # Abrir y validar PDF
            with open(pdf_path, 'rb') as file:
                try: 
                    reader = PyPDF2.PdfReader(file)
                    total_pages = len(reader.pages)
                    result['page_count'] = total_pages
                    self.logger.debug(f"PDF abierto exitosamente: {total_pages} páginas")

                except Exception as e:
                    self.logger.error(f"Error al abrir PDF: {str(e)}")
                    result['errors'].append(f"Error al abrir PDF: {str(e)}")
                    return result

            # Extraer texto página por página
            page_texts = []
            total_chars = 0
            pages_with_text = 0
            
            for page_num, page in enumerate(reader.pages):
                try:
                    clean_text = self._text_cleaner(page.extract_text())

                    if len(clean_text.strip()) > MIN_CHARACTERS_FOR_USEFUL_TEXT: 
                        page_texts.append(clean_text)
                        pages_with_text += 1
                        total_chars += len(clean_text)
                    else:
                        page_texts.append("")
                        result['warnings'].append(f"Página {page_num + 1}: Poco o ningún texto extraído")
                        
                except Exception as e:
                    page_texts.append("")
                    error_msg = f"Página {page_num + 1}: Error de extracción - {str(e)}"
                    result['warnings'].append(error_msg)
                    self.logger.warning(error_msg)
            
            # Combinar texto de todas las páginas
            non_empty_pages = [page for page in page_texts if page.strip()]
            
            if non_empty_pages:
                combined_text = '\n\n'.join(non_empty_pages)
                final_text = self._text_cleaner(combined_text)
            else:
                final_text = ""
                result['warnings'].append("Ninguna página contiene texto extraíble")
            
            # Calcular métricas de calidad
            result['quality_metrics'] = self._calculate_text_quality_metrics(
                total_chars, pages_with_text, total_pages
            )
            
            # Construir resultado final
            result['text'] = final_text
            result['page_count'] = total_pages
            
            # Logging informativo del proceso de extracción
            self.logger.debug(f"Extracción nativa completada: {total_chars} chars, ")
            
            return result
            
        except Exception as e:
            # MANEJO DE ERRORES GENERALES
            error_msg = f"Error general en extracción nativa: {str(e)}"
            result['errors'].append(error_msg)
            self.logger.error(error_msg)
            return result
    
    def _extract_with_ocr(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """
        Extractor OCR usando Tesseract para documentos escaneados o de baja calidad.

        OBJETIVO: Aplicar OCR cuando la extracción nativa falla o produce resultados insuficientes.
        ENFOQUE: Similar a _extract_native_text pero usando Tesseract sobre imágenes del PDF.

        PROCESO DETALLADO:
        1. Convertir PDF completo a imágenes (pdf2image)
        2. Configurar Tesseract para documentos académicos españoles
        3. Aplicar OCR página por página con manejo de errores
        4. Limpiar y combinar texto de todas las páginas
        5. Calcular métricas de calidad OCR
        6. Construir resultado con mismo formato que extracción nativa

        Returns:
            Dict con estructura idéntica a _extract_native_text o None si falla completamente
        """
        self.logger.debug(f"Iniciando extracción OCR de: {pdf_path}")
        
        result = {
            'text': '',                                   
            'page_count': 0,                           
            'methods_attempted': [ExtractionMethod.OCR],  
            'errors': [],                                 
            'warnings': [],                              
            'quality_metrics': {
                'total_chars': 0,         
                'pages_with_text': 0,       
                'text_density': 0.0,      
                'text_coverage': 0.0       
            }
        }
        
        try:
            # Convertir PDF a imágenes
            try:
                # Configuración optimizada para OCR académico
                dpi = self.config.get('ocr_dpi', 300)  # 300 DPI para buena calidad
                
                self.logger.debug(f"Convirtiendo PDF a imágenes: DPI={dpi}")
                
                # Convertir PDF completo a imágenes
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    fmt='RGB',  # Formato compatible con Tesseract
                    thread_count=1,  # Control de memoria y estabilidad
                    use_pdftocairo=False,  # Usar poppler por compatibilidad
                )
                
                if not images:
                    result['errors'].append("No se generaron imágenes del PDF")
                    self.logger.error("No se generaron imágenes del PDF")
                    return result
                
                # Validar imágenes generadas
                valid_images = []
                for i, img in enumerate(images):
                    try:
                        if img.size[0] > 0 and img.size[1] > 0:
                            valid_images.append(img)
                        else:
                            result['warnings'].append(f"Página {i + 1}: Imagen con dimensiones inválidas")
                    except Exception as e:
                        result['warnings'].append(f"Página {i + 1}: Error validando imagen - {str(e)}")
                
                if not valid_images:
                    result['errors'].append("Ninguna imagen válida generada del PDF")
                    self.logger.error("Ninguna imagen válida generada del PDF")
                    return result
                
                images = valid_images
                result['page_count'] = len(images)
                
                if len(images) < len(valid_images):
                    result['warnings'].append(f"Solo {len(images)} de {len(valid_images)} páginas convertidas exitosamente")
                
                self.logger.debug(f"PDF convertido exitosamente: {len(images)} imágenes válidas")
                
            except Exception as e:
                error_msg = f"Error convirtiendo PDF a imágenes: {str(e)}"
                result['errors'].append(error_msg)
                self.logger.error(error_msg)
                return result

            # Configurar Tesseract para documentos académicos
            tesseract_config = {
                'lang': self.config.get('ocr_lang', 'spa'),      # Idioma español
                'psm': self.config.get('ocr_psm', 6),            # PSM 6: Bloque uniforme de texto
                'oem': self.config.get('ocr_oem', 3),            # OEM 3: Por defecto (mejor balance)
                'preserve_interword_spaces': 1,                   # Mantener espacios entre palabras
                'tessdit_char_whitelist': '',                     # Sin restricciones de caracteres
            }
            
            # Construir string de configuración para pytesseract
            config_string = f"--psm {tesseract_config['psm']} --oem {tesseract_config['oem']}"
            if tesseract_config['preserve_interword_spaces']:
                config_string += " -c preserve_interword_spaces=1"
            
            self.logger.debug(f"Configuración Tesseract: idioma={tesseract_config['lang']}, {config_string}")
            
            # Procesar cada imagen con OCR
            page_texts = []
            total_chars = 0
            pages_with_text = 0
            
            self.logger.debug(f"Iniciando procesamiento OCR de {len(images)} imágenes")
            
            for page_num, img in enumerate(images):
                try:
                    # Aplicar OCR a la imagen con configuración optimizada
                    raw_text = pytesseract.image_to_string(
                        img, 
                        lang=tesseract_config['lang'], 
                        config=config_string
                    )
                    
                    clean_text = self._text_cleaner(raw_text)
                    
                    if len(clean_text.strip()) > MIN_CHARACTERS_FOR_USEFUL_TEXT:
                        page_texts.append(clean_text)
                        pages_with_text += 1
                        total_chars += len(clean_text)
                        self.logger.debug(f"Página {page_num + 1}: {len(clean_text)} caracteres extraídos")
                    else:
                        page_texts.append("")
                        result['warnings'].append(f"Página {page_num + 1}: Poco o ningún texto extraído por OCR")
                        
                except Exception as e:
                    page_texts.append("")
                    error_msg = f"Página {page_num + 1}: Error de OCR - {str(e)}"
                    result['warnings'].append(error_msg)
                    self.logger.warning(error_msg)
            
            self.logger.debug(f"OCR completado: {pages_with_text}/{len(images)} páginas con contenido, {total_chars} caracteres total")
            
            # Combinar y procesar texto final
            non_empty_pages = [page for page in page_texts if page.strip()]
            
            if non_empty_pages:
                combined_text = '\n\n'.join(non_empty_pages)
                final_text = self._text_cleaner(combined_text)
                self.logger.debug(f"Texto OCR combinado: {len(final_text)} caracteres finales")
            else:
                final_text = ""
                result['warnings'].append("Ninguna página contiene texto extraíble por OCR")
                self.logger.warning("OCR no produjo contenido útil en ninguna página")
            
            # Calcular métricas de calidad OCR
            result['quality_metrics'] = self._calculate_text_quality_metrics(
                total_chars, pages_with_text, len(images)
            )
            
            self.logger.debug(f"Métricas OCR calculadas: densidad={result['quality_metrics']['text_density']:.1f}, cobertura={result['quality_metrics']['text_coverage']:.2%}")
            
            # Construir resultado final
            result['text'] = final_text
            result['page_count'] = len(images)
            
            self.logger.debug(f"Extracción OCR completada: {len(final_text)} caracteres finales, {result['quality_metrics']['pages_with_text']}/{len(images)} páginas útiles")
            
            # Retornar resultado para evaluación en extract_from_pdf
            return result
            
        except Exception as e:
            # MANEJO DE ERRORES GENERALES OCR
            error_msg = f"Error general en extracción OCR: {str(e)}"
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
            
            # Calcular score ponderado final
            # Score de métricas básicas
            structure_component = (
                min(basic_metrics.get('paragraph_count', 0) / 3.0, 1.0) * 
                BASIC_WEIGHT_STRUCTURE
            )
            char_quality_component = (
                basic_metrics.get('alpha_ratio', 0) * 0.5 +
                (1.0 - basic_metrics.get('short_words_ratio', 1.0)) * 0.3 +
                min(basic_metrics.get('punct_ratio', 0) * 10, 1.0) * 0.2
            ) * BASIC_WEIGHT_CHAR_QUALITY
            # Cálculo gradual de calidad de palabras (óptimo: 4-8 caracteres)
            avg_len = basic_metrics.get('avg_word_length', 0)
            if avg_len < 1.5:
                word_score = 0.1  # Palabras demasiado cortas (errores OCR)
            elif avg_len > 15:
                word_score = 0.2  # Palabras demasiado largas (posible corrupción)
            elif 4 <= avg_len <= 8:
                word_score = 1.0  # Rango óptimo para español
            elif 2 <= avg_len < 4:
                word_score = 0.4 + (avg_len - 2) * 0.3  # Transición gradual 0.4-1.0
            elif 8 < avg_len <= 12:
                word_score = 1.0 - (avg_len - 8) * 0.15  # Transición gradual 1.0-0.4
            else:  # 12 < avg_len <= 15
                word_score = 0.4 - (avg_len - 12) * 0.1  # Transición gradual 0.4-0.2
            word_quality_component = word_score * BASIC_WEIGHT_WORD_QUALITY
            basic_score = structure_component + char_quality_component + word_quality_component
            
            # Score de patrones académicos
            codes_component = (
                min(academic_metrics.get('subject_code_count', 0) / 3.0, 1.0) * 
                ACADEMIC_WEIGHT_CODES
            )
            terminology_component = (
                min(academic_metrics.get('academic_density', 0) / 100.0, 1.0) * 0.7 +
                (1.0 if academic_metrics.get('academic_term_matches', 0) > 0 else 0.0) * 0.3
            ) * ACADEMIC_WEIGHT_TERMINOLOGY
            schedule_component = (
                (1.0 if academic_metrics.get('has_schedule_format', False) else 0.0) * 0.6 +
                min(academic_metrics.get('time_pattern_count', 0) / 2.0, 1.0) * 0.4
            ) * ACADEMIC_WEIGHT_SCHEDULE
            academic_score = codes_component + terminology_component + schedule_component
            
            # Score de indicadores de calidad
            coherence_component = (
                quality_indicators.get('coherence_score', 0) * 
                QUALITY_WEIGHT_COHERENCE
            )
            error_absence_component = (
                (1.0 - quality_indicators.get('char_corruption_ratio', 1.0)) *
                QUALITY_WEIGHT_ERROR_ABSENCE
            )
            quality_score = coherence_component + error_absence_component
            
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
            # Validaciones de seguridad para evitar división por cero
            if THRESHOLD_EXCELLENT <= THRESHOLD_GOOD:
                self.logger.error("Configuración inválida: THRESHOLD_EXCELLENT debe ser > THRESHOLD_GOOD")
                return ExtractionQuality.UNUSABLE, 0.0
            if THRESHOLD_GOOD <= THRESHOLD_ACCEPTABLE:
                self.logger.error("Configuración inválida: THRESHOLD_GOOD debe ser > THRESHOLD_ACCEPTABLE") 
                return ExtractionQuality.UNUSABLE, 0.0
            if THRESHOLD_ACCEPTABLE <= THRESHOLD_POOR:
                self.logger.error("Configuración inválida: THRESHOLD_ACCEPTABLE debe ser > THRESHOLD_POOR")
                return ExtractionQuality.UNUSABLE, 0.0
            
            # Mapeo seguro a categorías ExtractionQuality
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
                # Confianza baja con descuentos por errores OCR
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
    
    def _is_text_quality_acceptable(self, extraction_result: Dict[str, Any]) -> bool:
        """
        Evaluación rápida de calidad para decisiones de fallback.
        
        PROPÓSITO:
        - Decidir rápidamente si intentar método alternativo
        - Filtros básicos para evitar procesamiento innecesario
        - Umbral mínimo de aceptabilidad
        
        CRITERIOS BÁSICOS:
        - Longitud mínima del texto
        - Proporción mínima de caracteres válidos
        - Ausencia de errores críticos de extracción
        """
        try:
            # Verificar que hay resultado válido
            if not extraction_result or 'text' not in extraction_result:
                return False
            
            text = extraction_result.get('text', '')
            
            # 1. Filtro básico de longitud
            if len(text.strip()) < MIN_CHARACTERS_FOR_USEFUL_TEXT:
                return False
            
            # 2. Verificar errores críticos de extracción
            errors = extraction_result.get('errors', [])
            if errors:
                self.logger.debug(f"Texto rechazado por errores: {len(errors)} errores")
                return False
            
            # 3. Análisis rápido de calidad de caracteres
            char_count = len(text)
            if char_count == 0:
                return False
            
            alpha_chars = sum(1 for c in text if c.isalpha())
            alpha_ratio = alpha_chars / char_count
            
            # 4. Umbral mínimo de caracteres alfabéticos (50% para documentos académicos)
            if alpha_ratio < 0.5:
                self.logger.debug(f"Texto rechazado por bajo ratio alfabético: {alpha_ratio:.2f}")
                return False
            
            # 5. Verificar que no sea principalmente ruido
            words = text.split()
            if not words:
                return False
            
            # Ratio de palabras muy cortas (posibles errores OCR)
            short_words = sum(1 for w in words if len(w) <= 2)
            short_ratio = short_words / len(words)
            
            # Si más del 70% son palabras muy cortas, probablemente es ruido OCR
            if short_ratio > 0.7:
                self.logger.debug(f"Texto rechazado por exceso de palabras cortas: {short_ratio:.2f}")
                return False
            
            # 6. Verificar métricas de cobertura del PDF
            quality_metrics = extraction_result.get('quality_metrics', {})
            text_coverage = quality_metrics.get('text_coverage', 0)
            
            # Si menos del 30% de las páginas tienen texto, probablemente es un PDF escaneado
            if text_coverage < 0.3:
                self.logger.debug(f"Texto rechazado por baja cobertura de páginas: {text_coverage:.2f}")
                return False
            
            # Si llegamos aquí, el texto parece aceptable
            return True
            
        except Exception as e:
            self.logger.error(f"Error en evaluación rápida de calidad: {e}")
            return False
    
    # =============================================================================
    # FUNCIONES AUXILIARES PARA MODULARIDAD
    # =============================================================================
    
    def _calculate_text_quality_metrics(
        self, total_chars: int, pages_with_text: int, total_pages: int
    ) -> Dict[str, Any]:
        """
        Calcular métricas de calidad para decisión de OCR.
        
        Args:
            total_chars: Total de caracteres extraídos
            pages_with_text: Número de páginas con contenido
            total_pages: Total de páginas del PDF
            
        Returns:
            Dict con métricas de calidad (solo datos, sin evaluación)
        """
        # Calcular métricas básicas
        text_density = total_chars / total_pages if total_pages > 0 else 0.0
        text_coverage = pages_with_text / total_pages if total_pages > 0 else 0.0
        
        # Construir diccionario de métricas
        quality_metrics = {
            'total_chars': total_chars,
            'pages_with_text': pages_with_text,
            'text_density': text_density,
            'text_coverage': text_coverage
        }
        
        return quality_metrics
    
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
            short_words = sum(1 for w in words if len(w) <= 2)  # Posibles errores OCR
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
        # 1. Detección de códigos de asignatura (G111, M123, A456, B789, etc.)
        subject_codes = re.findall(r'\b[A-Z]\d{2,4}\b', text, re.IGNORECASE)
        subject_code_count = len(subject_codes)
        has_subject_codes = subject_code_count > 0
        
        # 2. Términos académicos españoles comunes
        academic_terms = [
            'asignatura', 'créditos', 'ects', 'profesor', 'docente', 'catedrático',
            'curso', 'semestre', 'cuatrimestre', 'grado', 'máster', 'optativa',
            'obligatoria', 'troncal', 'práctica', 'teoría', 'laboratorio',
            'departamento', 'facultad', 'universidad', 'titulación', 'plan',
            'evaluación', 'examen', 'convocatoria', 'matrícula', 'horario'
        ]
        
        text_lower = text.lower()
        academic_term_matches = sum(1 for term in academic_terms if term in text_lower)
        
        # Calcular densidad académica (términos por cada 100 palabras)
        word_count = len(text.split()) if text.strip() else 1
        academic_density = (academic_term_matches / word_count) * 100 if word_count > 0 else 0
        
        # 3. Formatos de horarios y fechas
        # Detectar patrones de horario (HH:MM, H:MM)
        time_patterns = re.findall(r'\b\d{1,2}:\d{2}\b', text)
        
        # Detectar días de la semana en español (completos y abreviados)
        weekdays = re.findall(
            r'\b(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo|'
            r'L|M|X|J|V|S|D|Lu|Ma|Mi|Ju|Vi|Sa|Do)\b', 
            text, re.IGNORECASE
        )
        
        # Detectar aulas/espacios académicos (A1.01, Lab-001, Aula 101, etc.)
        classroom_patterns = re.findall(
            r'\b[A-Z]\d+\.\d+\b|\bLab[-\s]?\d+\b|\bAula[-\s]?\d+\b|\bSalón[-\s]?\d+\b|'
            r'\bSeminario[-\s]?\d+\b|\bDespacho[-\s]?\d+\b', 
            text, re.IGNORECASE
        )
        
        # 4. Información docente y académica
        # Detectar títulos y menciones de profesores
        title_patterns = re.findall(
            r'\b(Dr\.?|Dra\.?|Prof\.?|Profesor|Profesora|Catedrático|Catedrática|'
            r'Coordinador|Coordinadora)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', 
            text
        )
        
        # Detectar emails académicos (.es, .edu, universidad)
        academic_emails = re.findall(
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*(?:universidad|\.es|\.edu|upm\.es|ucm\.es)\b', 
            text, re.IGNORECASE
        )
        
        # 5. Indicadores de calidad académica compuestos
        has_schedule_format = len(time_patterns) > 0 and len(weekdays) > 0
        has_academic_structure = academic_term_matches > 2 and has_subject_codes
        
        # Construir diccionario de métricas académicas
        academic_metrics = {
            # Códigos académicos
            'subject_code_count': subject_code_count,
            'has_subject_codes': has_subject_codes,
            
            # Terminología académica
            'academic_term_matches': academic_term_matches,
            'academic_density': academic_density,
            
            # Elementos de horario
            'time_pattern_count': len(time_patterns),
            'weekday_count': len(weekdays),
            'classroom_count': len(classroom_patterns),
            
            # Información docente
            'professor_mention_count': len(title_patterns),
            'academic_email_count': len(academic_emails),
            
            # Indicadores de calidad académica
            'has_schedule_format': has_schedule_format,
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
        - Ausencia de errores OCR: ocr_error_indicators, char_corruption_ratio
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
        has_time_structure = academic_metrics.get('has_schedule_format', False)
        has_academic_terms = academic_metrics.get('academic_term_matches', 0) > 0
        
        structure_indicators = sum([
            has_paragraphs,
            has_academic_codes, 
            has_time_structure,
            has_academic_terms,
            basic_metrics.get('has_structure', False)
        ])
        
        has_structured_content = structure_indicators >= 2
        structure_score = min(structure_indicators / 5.0, 1.0)  # Normalizado 0-1
        
        # 2. Evaluación de coherencia semántica
        # Detectar patrones que indican texto coherente vs ruido OCR
        char_count = basic_metrics.get('char_count', 0)
        word_count = basic_metrics.get('word_count', 0)
        
        # Ratio de caracteres alfabéticos (texto real vs símbolos extraños)
        alpha_ratio = basic_metrics.get('alpha_ratio', 0)
        
        # Longitud promedio de palabra razonable (2-12 caracteres típico español)
        avg_word_length = basic_metrics.get('avg_word_length', 0)
        reasonable_word_length = 2 <= avg_word_length <= 12
        
        # Ratio de palabras muy cortas (posibles errores OCR)
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
        
        # 3. Detección de errores OCR característicos
        # Patrones típicos de errores de OCR en textos academicos
        text_lower = text.lower()
        
        # Caracteres problemáticos comunes en errores OCR
        ocr_error_patterns = [
            r'[|]{2,}',          # Líneas verticales múltiples
            r'[_]{3,}',          # Guiones bajos múltiples  
            r'[\.]{4,}',         # Puntos múltiples
            r'[ij]{3,}',         # Repeticiones de i/j
            r'[0O]{2,}[0O]',     # Confusión O/0 múltiple
            r'\b[a-z]{1}[A-Z]{1}[a-z]', # Mayúsculas intercaladas extrañas
            r'[^\w\s\.,;:!?\-()áéíóúñ]{2,}' # Símbolos extraños múltiples
        ]
        
        ocr_error_count = sum(len(re.findall(pattern, text)) for pattern in ocr_error_patterns)
        ocr_error_indicators = ocr_error_count
        
        # Ratio de corrupción de caracteres
        char_corruption_ratio = min(ocr_error_count / char_count, 1.0) if char_count > 0 else 0
        
        # 4. Evaluación de proporción útil vs ruido
        # Determinar qué porcentaje del texto es contenido académico útil
        
        # Contenido útil: términos académicos + códigos + estructura (normalizado)
        useful_indicators = [
            min(academic_metrics.get('academic_term_matches', 0) / 3.0, 1.0),  # Max 3 términos = 1.0
            min(academic_metrics.get('subject_code_count', 0) / 2.0, 1.0),     # Max 2 códigos = 1.0  
            min(academic_metrics.get('time_pattern_count', 0) / 2.0, 1.0),     # Max 2 horarios = 1.0
            min(academic_metrics.get('professor_mention_count', 0) / 1.0, 1.0), # Max 1 profesor = 1.0
            1.0 if has_structured_content else 0.0  # Estructura binaria
        ]
        
        # Promedio ponderado de indicadores útiles
        weights = [0.3, 0.3, 0.15, 0.1, 0.15]  # Suma = 1.0
        useful_content_ratio = sum(indicator * weight for indicator, weight in zip(useful_indicators, weights))
        
        # Nivel de ruido inverso (menos ruido = mejor calidad)
        # Cálculo corregido de ruido por espacios
        normal_space_ratio = 0.15  # Ratio normal de espacios en texto español
        current_space_ratio = basic_metrics.get('space_ratio', 0)
        space_deviation = abs(current_space_ratio - normal_space_ratio)
        space_noise = min(space_deviation * 3.0, 1.0)  # Penalizar desviación significativa
        
        noise_factors = [
            char_corruption_ratio,      # 0-1 (más = peor)
            short_words_ratio,         # 0-1 (más = peor) 
            1.0 - alpha_ratio,         # 0-1 (más = peor)
            space_noise               # 0-1 (desviación de espacios normales)
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
            
            # Ausencia de errores OCR
            'ocr_error_indicators': ocr_error_indicators,
            'char_corruption_ratio': char_corruption_ratio,
            
            # Proporción útil vs ruido
            'useful_content_ratio': useful_content_ratio,
            'noise_level': noise_level,
            
            # Indicadores compuestos adicionales
            'overall_structure_quality': structure_score * (1 - noise_level),
            'content_reliability': coherence_score * useful_content_ratio
        }
        
        return quality_indicators

    def get_stats(self) -> Dict[str, Any]:
        """
        Estadísticas de uso para monitoreo y debugging.
        
        MÉTRICAS ÚTILES:
        - Total de extracciones realizadas
        - Tasa de éxito por método (nativo vs OCR)
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
        
        return clean(text,
            fix_unicode=True,           # Corregir problemas de encoding
            to_ascii=False,             # MANTENER acentos españoles
            lower=False,                # PRESERVAR mayúsculas (códigos, nombres)
            normalize_whitespace=True,   # Normalizar espacios múltiples
            no_line_breaks=False,       # Mantener estructura de párrafos
            strip_lines=True,           # Limpiar espacios al inicio/final
            no_urls=True,               # Limpiar URLs
            no_emails=False,            # MANTENER emails de profesorado
            no_phone_numbers=True,      # Limpiar teléfonos
            no_numbers=False,           # MANTENER números (códigos, créditos)
            no_digits=False,            # MANTENER dígitos
            no_currency_symbols=True,   # Eliminar símbolos de moneda
            no_punct=False,             # MANTENER puntuación estructural
            no_emoji=True,              # Eliminar emojis
            lang="es"
        )



# =============================================================================
# INSTANCIA GLOBAL PARA FACILIDAD DE USO
# =============================================================================

# Instancia global del extractor para uso conveniente
# Se inicializa con configuración por defecto
ocr_extractor = None  # TODO: Inicializar cuando se implemente la clase