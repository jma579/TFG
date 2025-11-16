"""
PDF Text Extraction Module — HORARIOS

FINALIDAD:
- Convertir documentos PDF de horarios académicos en estructuras de datos procesables
- Extraer tablas de horarios y su información asociada
- Detectar días, horas y bloques de sesiones
- Base del pipeline de extracción de HORARIOS

ESTRATEGIA:
- Extracción de tablas con PyMuPDF/pdfplumber
- Detección de estructura tabular (días/horas)
- Identificación de bloques de texto
- Manejo de metadatos y calidad
"""

# Python stdlib
from typing import Dict, Any, Optional, List, Tuple
import logging
from pathlib import Path
import time
import fitz  # PyMuPDF
import pdfplumber
import re

from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ErrorType,
    ExtractionMetadata, Warning
)
from core.extraccion.newhorarios.entities import (
    HorarioExtractionResult, TablaHorario
)
from core.extraccion.newhorarios.constants import (
    DEFAULT_EXTRACTOR_CONFIG, PDFPLUMBER_TABLE_SETTINGS_TEXT,
    DIAS_SEMANA, DAYS_MAP, TIME_CONFIG, VALID_TIME_CHARS,
    PATRONES, TABLE_QUALITY_WEIGHTS, PDFPLUMBER_TABLE_SETTINGS_LINES,
    RX_HORA, RX_CURSO, RX_MENCION, PATRON_HORA
)
from core.extraccion.common.constants import (
    THRESHOLD_EXCELLENT, THRESHOLD_GOOD, 
    THRESHOLD_ACCEPTABLE, THRESHOLD_POOR
)


class HorarioExtractor:
    """
    Extractor de horarios académicos desde PDFs.
    
    Esta clase implementa la extracción y procesamiento de horarios académicos
    desde documentos PDF, utilizando una combinación de PyMuPDF y pdfplumber
    para una detección robusta de tablas y contenido.
    
    ARQUITECTURA:
    1. Inicialización:
       - Configuración y logging
       - Validación de entradas
       - Preparación de estadísticas
       
    2. Extracción:
       - Detección de tablas mediante pdfplumber
       - Identificación de estructura tabular
       - Extracción de metadatos del documento
       
    3. Procesamiento:
       - Normalización de días y horas
       - Validación de estructura temporal
       - Extracción de curso y mención
       
    4. Evaluación:
       - Assessment de calidad
       - Cálculo de confianza
       - Generación de warnings
       
    La clase mantiene estadísticas de uso y proporciona logging detallado
    para facilitar el diagnóstico y monitorización del proceso de extracción.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializar extractor con configuración.
        
        Args:
            config: Diccionario de configuración personalizada
        """
        # 1. Configurar logging
        self.logger = logging.getLogger(__name__)
        
        # 2. Aplicar configuración
        self.config = DEFAULT_EXTRACTOR_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # 3. Configurar nivel de logging
        if 'log_level' in self.config:
            self.logger.setLevel(getattr(logging, self.config['log_level'].upper(), logging.INFO))
        
        # 4. Inicializar estadísticas
        self.stats = {
            'extractions_total': 0,
            'tables_detected': 0,
            'failures': 0,
            'avg_processing_time': 0.0
        }
        
        self.logger.info("HorarioExtractor inicializado correctamente")


    def extract(self, pdf_path: str) -> HorarioExtractionResult:
        """
        MÉTODO PRINCIPAL: Extraer tablas de horarios del PDF.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            HorarioExtractionResult con las tablas extraídas y metadatos
        """
        start_time = time.time()
        self.stats['extractions_total'] += 1
        
        try:
            # 1. Validación inicial con PyMuPDF
            self._validate_pdf_input(pdf_path)
            
            # 2. Extracción de tablas con pdfplumber
            tablas = self._extract_tables(pdf_path)
            
            # 3. Procesamiento de metadatos y evaluación
            titulo = self._extract_title(pdf_path)
            quality, confidence = self._assess_extraction_quality(tablas)
            
            # 4. Construcción del resultado
            processing_time = time.time() - start_time
            self._update_processing_time(processing_time)
            
            if not tablas:
                # marca fallo “lógico”
                metadata = self._build_success_metadata(quality, confidence, processing_time, pdf_path, len(tablas))
                metadata.status = ProcessingStatus.FAILED
                return HorarioExtractionResult(titulo=titulo, tablas=[], metadata=metadata)
            
            metadata = self._build_success_metadata(
                quality, confidence, processing_time, pdf_path, len(tablas)
            )
            
            return HorarioExtractionResult(
                titulo=titulo,
                tablas=tablas,
                metadata=metadata
            )
        
        except Exception as e:
            return self._handle_extraction_error(e, pdf_path, start_time)


    # Funciones auxiliares base (similar a FichaExtractor)
    def _validate_pdf_input(self, pdf_path: str) -> None:
        """
        Validar archivo PDF de entrada.
        
        Args:
            pdf_path: Ruta al archivo PDF a validar
            
        Raises:
            ValueError: Si el archivo no existe o no es válido
            RuntimeError: Si el archivo está corrupto o es demasiado grande
        """
        # Convertir string a Path
        path = Path(pdf_path)
        
        # 1. Verificar existencia
        if not path.exists():
            self.stats['failures'] += 1
            raise ValueError(f"No se encontró el archivo: {pdf_path}")
        
        # 2. Verificar extensión
        if path.suffix.lower() != '.pdf':
            self.stats['failures'] += 1
            raise ValueError(f"El archivo debe ser PDF: {pdf_path}")
        
        # 3. Verificar tamaño
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config['max_file_size_mb']:
            self.stats['failures'] += 1
            raise RuntimeError(
                f"PDF demasiado grande ({file_size_mb:.1f}MB). "
                f"Máximo permitido: {self.config['max_file_size_mb']}MB"
            )

        # 4. Verificar que se puede abrir (no está corrupto)
        try:
            doc = fitz.open(pdf_path)
            doc.close()
        except Exception as e:
            self.stats['failures'] += 1
            raise RuntimeError(f"Error al abrir el PDF: {str(e)}")
        
        self.logger.debug(f"Validación exitosa de {pdf_path}")

    def _extract_tables(self, pdf_path: str) -> List[TablaHorario]:
        """Extracción principal de tablas usando pdfplumber."""
        tablas: List[TablaHorario] = []
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            self.logger.info(f"Procesando {total_pages} páginas")

            for page_num, page in enumerate(pdf.pages):
                page_tablas: List[TablaHorario] = []

                # 1) Intento con 'lines'
                try:
                    found = page.find_tables(PDFPLUMBER_TABLE_SETTINGS_LINES)
                    for tb in found:
                        t = self._process_table_from_tableobj(tb, page, page_num)
                        if t: page_tablas.append(t)
                except Exception as e:
                    self.logger.debug(f"find_tables(lines) falló en p{page_num}: {e}")

                # 2) Si nada útil, intento con 'text'
                if not page_tablas:
                    try:
                        found = page.find_tables(PDFPLUMBER_TABLE_SETTINGS_TEXT)
                        for tb in found:
                            t = self._process_table_from_tableobj(tb, page, page_num)
                            if t: page_tablas.append(t)
                    except Exception as e:
                        self.logger.debug(f"find_tables(text) falló en p{page_num}: {e}")

                # 3) Fallback geométrico por palabras (sin tablas)
                if not page_tablas:
                    try:
                        t = self._process_page_by_words(page, page_num)
                        if t: page_tablas.append(t)
                    except Exception as e:
                        self.logger.warning(f"Fallback por palabras falló en p{page_num}: {e}")

                tablas.extend(page_tablas)

        return tablas

    def _extract_title(self, pdf_path: str) -> str:
        rx = re.compile(PATRONES['titulo'], flags=re.IGNORECASE | re.DOTALL)
        # 1) Intento pdfplumber (página 1)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                txt = pdf.pages[0].extract_text() or ""
                txt = " ".join(txt.split())
                m = rx.search(txt)
                if m:
                    return m.group(0).strip()
                # mirar primeras líneas por si hay separadores
                for line in (txt.splitlines()[:6] if txt else []):
                    if "GRADO" in line.upper() and ("PRIMER" in line.upper() or "SEGUNDO" in line.upper()):
                        return line.strip()
        except Exception:
            pass

        # 2) Fallback PyMuPDF (une bloques/espacios)
        try:
            doc = fitz.open(pdf_path)
            txt = ""
            for i in range(min(2, doc.page_count)):
                txt += doc[i].get_text("text") + "\n"
            doc.close()
            txt = " ".join(txt.split())
            m = rx.search(txt)
            if m:
                return m.group(0).strip()
        except Exception:
            pass

        raise ValueError("No se encontró un título válido en el documento")

    def _assess_extraction_quality(self, tablas: List[TablaHorario]) -> tuple[ExtractionQuality, float]:
        """
        Evalúa la calidad de la extracción basándose en las tablas extraídas.
        
        La calidad se determina por:
        1. Número de tablas encontradas
        2. Completitud de las tablas (días, horas, celdas)
        3. Coherencia de la estructura
        
        Args:
            tablas: Lista de tablas extraídas
            
        Returns:
            tuple[ExtractionQuality, float]: Par (calidad, confianza)
                - calidad: Enum ExtractionQuality (EXCELLENT, GOOD, ACCEPTABLE, POOR, UNUSABLE)
                - confianza: Float entre 0 y 1
        """
        if not tablas:
            return ExtractionQuality.UNUSABLE, 0.0
    
        # 1. Evaluar cada tabla
        table_scores = []
        for tabla in tablas:
            score = 0.0
            
            # Verificar días completos
            if len(tabla.day_columns) == 5:  # L-V
                score += TABLE_QUALITY_WEIGHTS['days_structure']
            
            # Verificar franjas horarias
            if len(tabla.time_rows) >= TIME_CONFIG['min_franjas']:
                score += TABLE_QUALITY_WEIGHTS['time_structure']
            
            # Verificar celdas con contenido
            cells_with_content = sum(1 for row in tabla.celdas for cell in row if cell is not None)
            total_cells = (len(tabla.celdas) * len(tabla.celdas[0])) if (tabla.celdas and tabla.celdas[0]) else 0
            content_ratio = (cells_with_content / total_cells) if total_cells else 0.0
            score += TABLE_QUALITY_WEIGHTS['content_density'] * content_ratio
            
            table_scores.append(score)
        
        # 2. Calcular puntuación global
        avg_score = sum(table_scores) / len(table_scores)
        
        # 3. Determinar calidad usando umbrales compartidos
        if avg_score >= THRESHOLD_EXCELLENT:
            quality = ExtractionQuality.EXCELLENT
        elif avg_score >= THRESHOLD_GOOD:
            quality = ExtractionQuality.GOOD
        elif avg_score >= THRESHOLD_ACCEPTABLE:
            quality = ExtractionQuality.ACCEPTABLE
        elif avg_score >= THRESHOLD_POOR:
            quality = ExtractionQuality.POOR
        else:
            quality = ExtractionQuality.UNUSABLE
        
        self.logger.debug(f"Calidad evaluada: {quality.value} (confianza: {avg_score:.2f})")
        return quality, avg_score

    def _update_processing_time(self, processing_time: float) -> None:
        """
        Actualiza las estadísticas de tiempo de procesamiento.
        
        Args:
            processing_time: Tiempo de procesamiento en segundos
        """
        total_extractions = self.stats['extractions_total']
        current_avg = self.stats['avg_processing_time']
        
        # Actualizar media móvil
        if total_extractions == 1:
            self.stats['avg_processing_time'] = processing_time
        else:
            # Fórmula: nuevo_promedio = viejo_promedio * (n-1)/n + nuevo_valor/n
            self.stats['avg_processing_time'] = (
                current_avg * (total_extractions - 1) / total_extractions +
                processing_time / total_extractions
            )
        
        self.logger.debug(
            f"Tiempo de procesamiento actualizado: {processing_time:.2f}s "
            f"(media: {self.stats['avg_processing_time']:.2f}s)"
        )

    def _build_success_metadata(self, quality: ExtractionQuality, confidence: float,
                              processing_time: float, pdf_path: str, 
                              num_tablas: int) -> ExtractionMetadata:
        """
        Construye los metadatos para una extracción exitosa.
        
        Args:
            quality: Calidad de la extracción
            confidence: Nivel de confianza (0-1)
            processing_time: Tiempo de procesamiento en segundos
            pdf_path: Ruta al archivo PDF
            num_tablas: Número de tablas extraídas
            
        Returns:
            ExtractionMetadata: Metadatos de la extracción
        """
        warnings = []
    
        # Verificar calidad mínima
        if quality in [ExtractionQuality.POOR, ExtractionQuality.UNUSABLE]:
            warnings.append(
                Warning(
                    message="Calidad de extracción por debajo del umbral aceptable",
                    severity="severe"  # Cambiado de "high" a "severe"
                )
            )
        
        # Obtener tamaño del archivo
        file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)

        pages, chars, words, has_text = self._quick_pdf_stats(pdf_path)
        
        # Construir metadatos según la estructura correcta
        return ExtractionMetadata(
            quality=quality,
            confidence=confidence,
            status=ProcessingStatus.COMPLETED,
            processing_time_seconds=processing_time,
            page_count=pages,
            file_size_mb=file_size_mb,
            has_embedded_text=has_text,
            char_count=chars,
            word_count=words,
            errors=[],
            warnings=warnings,
            pages_with_text=pages if has_text else 0,
        )

    def _handle_extraction_error(self, error: Exception, pdf_path: str, 
                               start_time: float) -> HorarioExtractionResult:
        """
        Maneja los errores durante la extracción y construye un resultado de error.
        
        Args:
            error: Excepción capturada
            pdf_path: Ruta al archivo PDF
            start_time: Tiempo de inicio del procesamiento
            
        Returns:
            HorarioExtractionResult: Resultado con metadata de error
        """
        self.stats['failures'] += 1
        processing_time = time.time() - start_time
        
        # Construir warning con severidad correcta
        error_warning = Warning(
            message=str(error),
            severity="severe"  # Cambiado de "high" a "severe"
        )
        
        try:
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        except:
            file_size_mb = 0.0
        
        # Construir metadata con la estructura correcta
        error_metadata = ExtractionMetadata(
            quality=ExtractionQuality.UNUSABLE,
            confidence=0.0,
            status=ProcessingStatus.FAILED,
            processing_time_seconds=processing_time,
            page_count=0,
            file_size_mb=file_size_mb,
            has_embedded_text=False,
            char_count=0,
            word_count=0,
            errors=[str(error)],
            warnings=[error_warning],
            pages_with_text=0
        )
        
        return HorarioExtractionResult(
            titulo="",
            tablas=[],
            metadata=error_metadata
        )


    # FUNCIONES AUXILIARES 

    def _process_table_from_tableobj(self, table, page, page_num: int) -> Optional[TablaHorario]:
        """
        Procesa una tabla detectada por pdfplumber (ruta 'por líneas'):
        - Detecta cabeceras de días, filas de horas y celdas.
        - Limpieza: horas sueltas, notas, asteriscos, fusiones entre columnas.
        - MEJORA: Corrige nombres multilínea y texto pegado.
        - Compacta filas duplicadas por hora y valida orden temporal.
        - Fusiona asignaturas con aulas/grupos en celdas consecutivas.
        - Metadata tolerante (no lanza al faltar curso).
        """
        data = table.extract()
        if not data or len(data) < 2:
            return None

        # 1) Cabecera de días en primeras filas
        header_row = None
        for row in data[:4]:
            cells = (row or [])[1:]  # col 0 son horas
            norm = [self._normalize_day((c or "").strip().upper()) for c in cells]
            got = [d for d in norm if d]
            if len(got) >= 3:
                header_row = [d for d in norm if d][:5]
                break

        day_columns: List[str] = header_row or []

        # 2) Fallback: inferir días de palabras si la cabecera no es válida
        if not self._validate_days(day_columns):
            inferred = self._infer_day_columns_from_words(page, table.bbox)
            if inferred and self._validate_days(inferred):
                day_columns = inferred
            else:
                self.logger.warning(f"Tabla descartada: encabezados inválidos en página {page_num}")
                return None

        # 3) Filas de horas (col 0)
        time_rows: List[str] = []
        for r in data[1:]:
            label = (r[0] or "").strip() if r and len(r) > 0 else ""
            t = self._normalize_time(label)
            if t:
                time_rows.append(t)

        # 4) Celdas (limpieza por celda + fusión entre columnas)
        num_day_cols = len(day_columns)
        celdas: List[List[Optional[str]]] = []
        for r in data[1:]:
            cols = (r[1:1+num_day_cols] if r and len(r) > 1 else [])
            row_vals: List[Optional[str]] = []
            for c in cols:
                raw = (c or "").strip()
                # NUEVA LIMPIEZA: Corregir nombres multilínea ANTES de otras limpiezas
                clean = self._fix_multiline_names(raw) if raw else None
                clean = self._strip_spurious_hour(clean) if clean else None
                clean = self._remove_inline_hours(clean) if clean else None
                clean = self._strip_inline_asterisk_notes(clean) if clean else None
                row_vals.append(clean)
            # fusión entre columnas si procede
            row_vals = self._merge_split_across_columns(row_vals)
            # padding a nº de días
            while len(row_vals) < num_day_cols:
                row_vals.append(None)
            celdas.append(row_vals)

        # 5) Quitar notas largas + etiquetas de cabecera en primeras filas + vaciar filas-nota
        for i in range(len(celdas)):
            for j in range(len(celdas[i])):
                celdas[i][j] = self._demote_footnote(celdas[i][j])
        
        # ✅ CORRECCIÓN: Eliminar condicional y usar directamente la función con valor aumentado
        self._clear_header_labels_early_rows(day_columns, celdas, upto_rows=5)  # Aumentado de 2 a 5
        
        celdas = self._blank_footnote_rows(celdas)

        # 6) Compactar por hora y validar orden temporal
        time_rows, celdas = self._compact_grid_by_time(time_rows, celdas)
        if not self._validate_times(time_rows):
            return None

        # 6.5) Fusionar asignaturas con aulas/grupos en celdas consecutivas
        celdas = self._merge_subject_and_room_cells(celdas)

        # 7) Metadata tolerante
        curso, mencion = self._extract_table_metadata(page, table)

        return TablaHorario(
            curso=curso,
            day_columns=day_columns,
            time_rows=time_rows,
            celdas=celdas,
            mencion=mencion,
            pagina=page_num
        )

    def _process_page_by_words(self, page, page_num: int) -> Optional[TablaHorario]:
        """
        Fallback geométrico (ruta 'por palabras'):
        - Infere días (banda superior) y horas (banda izquierda anclada al 1er día).
        - Segmenta rejilla con bordes X/Y robustos.
        - Extrae celdas por PALABRAS + limpieza y fusiones entre columnas.
        """
        words = page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=False) or []
        if not words:
            return None

        W = page.width
        H = page.height

        # 1) Cabeceras de día arriba
        top_band = 0.35 * H
        day_candidates: List[Tuple[str, Tuple[float, float, float, float]]] = []
        for w in words:
            txt = (w.get("text") or "").strip().upper()
            day = self._normalize_day(txt)
            if day and w.get("top", 0) < top_band:
                day_candidates.append((day, (w["x0"], w["top"], w["x1"], w["bottom"])))

        day_candidates.sort(key=lambda d: (d[1][0], d[1][1]))
        columns: List[Tuple[str, float]] = []
        seen = set()
        for day, bbox in day_candidates:
            x0 = bbox[0]
            if any(abs(x0 - cx) < 18 for (_, cx) in columns):
                continue
            if day not in seen:
                columns.append((day, x0))
                seen.add(day)
            if len(columns) == 5:
                break

        columns.sort(key=lambda t: t[1])
        day_columns = [d for (d, _) in columns]
        if not self._validate_days(day_columns):
            return None

        # 2) Horas (banda izquierda anclada al 1er día)
        first_day_x = columns[0][1]
        left_band = min(0.25 * W, first_day_x - 10)

        time_hits: List[Tuple[str, Tuple[float, float, float, float]]] = []
        for w in words:
            txt = (w.get("text") or "").strip()
            if w.get("x0", 0) < left_band and RX_HORA.fullmatch(re.sub(r"\s+", "", txt)):
                t = self._normalize_time(txt)
                if t:
                    time_hits.append((t, (w["x0"], w["top"], w["x1"], w["bottom"])))
        time_hits.sort(key=lambda t: (t[1][1], t[0]))
        time_hits = self._compact_time_hits(time_hits)
        time_rows = [t for (t, _) in time_hits]
        if not self._validate_times(time_rows):
            return None

        # 3) Bordes X
        xs = [x for (_, x) in columns]
        x_edges = [0] + [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)] + [W]

        # 4) Bordes Y (evitar cabecera en 1ª fila)
        y_pairs = [(bb[1], bb[3]) for (_, bb) in time_hits]
        y_pairs.sort(key=lambda z: z[0])

        y_edges: List[float] = []
        first_top, first_bottom = y_pairs[0]
        y_edges.append(min(H, first_bottom + 2))
        for i in range(1, len(y_pairs)):
            prev_bottom = y_pairs[i - 1][1]
            cur_top = y_pairs[i][0]
            y_edges.append((prev_bottom + cur_top) / 2)
        last_bottom = y_pairs[-1][1]
        y_edges.append(min(H, last_bottom + 18))

        # 5) Celdas por PALABRAS + limpieza + fusiones entre columnas
        celdas: List[List[Optional[str]]] = []
        pad_x = 6
        pad_y = 2
        for r in range(len(time_rows)):
            row_vals: List[Optional[str]] = []
            for c in range(len(day_columns)):
                x0 = max(0, x_edges[c] + pad_x)
                x1 = max(x0, x_edges[c + 1] - pad_x)
                y0 = max(0, y_edges[r] + pad_y)
                y1 = max(y0, y_edges[r + 1] - pad_y)
                bbox = (x0, y0, x1, y1)
                raw = self._cell_text_from_words(words, bbox)  # ya agrupa líneas con tolerancia
                clean = self._strip_spurious_hour(raw) if raw else None
                clean = self._remove_inline_hours(clean) if clean else None
                clean = self._strip_inline_asterisk_notes(clean) if clean else None
                row_vals.append(clean)
            # fusión entre columnas si procede
            row_vals = self._merge_split_across_columns(row_vals)
            celdas.append(row_vals)

        # 6) Quitar notas + etiquetas de cabecera en primeras filas + vaciar filas-nota
        for i in range(len(celdas)):
            for j in range(len(celdas[i])):
                celdas[i][j] = self._demote_footnote(celdas[i][j])
        if hasattr(self, "_clear_header_labels_early_rows"):
            self._clear_header_labels_early_rows(day_columns, celdas, upto_rows=2)
        else:
            self._clear_header_labels_in_first_row(day_columns, celdas)
        celdas = self._blank_footnote_rows(celdas)

        # 7) Metadata (caption)
        top_of_grid = y_edges[0]
        cap_bbox = (0, max(0, top_of_grid - 180), W, top_of_grid)  # ventana más generosa
        cropped = page.within_bbox(cap_bbox)
        caption = (cropped.extract_text() or "")
        curso_match = RX_CURSO.search(caption or "")
        curso = curso_match.group(0).strip() if curso_match else "1º"
        mencion = self._clean_mencion(caption) if hasattr(self, "_clean_mencion") else None

        # 8) Sanity de forma (columnas == nº de días)
        num_day_cols = len(day_columns)
        for i in range(len(celdas)):
            if len(celdas[i]) < num_day_cols:
                celdas[i].extend([None] * (num_day_cols - len(celdas[i])))
            elif len(celdas[i]) > num_day_cols:
                celdas[i] = celdas[i][:num_day_cols]

        return TablaHorario(
            curso=curso,
            day_columns=day_columns,
            time_rows=time_rows,
            celdas=celdas,
            mencion=mencion,
            pagina=page_num
        )

    def _first_row_with_days(self, data: list[list[str]]) -> Optional[list[str]]:
    # Mira las 4 primeras filas por si la cabecera no está en la fila 0
        for row in data[:4]:
            cells = (row or [])[1:]  # salta la col 0 de horas
            norm = []
            for c in cells:
                d = self._normalize_day((c or "").strip().upper())
                norm.append(d if d else None)
            got = [d for d in norm if d]
            if len(got) >= 3:
                # Devuelve las 5 primeras etiquetas válidas si existieran
                # (rellenarás con None si hiciera falta más adelante)
                return [d for d in norm if d][:5]
        return None

    def _normalize_day(self, day_text: str) -> Optional[str]:
        """
        Normaliza el texto del día de la semana.
        
        Args:
            day_text: Texto del día a normalizar
            
        Returns:
            Día normalizado o None si no es válido
        """
        # Limpiar y convertir a mayúsculas
        day = day_text.upper().strip()
        
        # Buscar coincidencia exacta
        if day in DAYS_MAP.values():
            return day
            
        # Buscar por prefijo
        for prefix, full_day in DAYS_MAP.items():
            if day.startswith(prefix):
                return full_day
                
        return None
    
    def _validate_days(self, days: List[str]) -> bool:
        """
        Acepta 5 o más columnas, verifica que las 5 primeras sean L-V en orden.
        """
        if len(days) < len(DIAS_SEMANA):
            self.logger.warning(f"Número incorrecto de días: {len(days)}")
            return False
        # Compara solo las 5 primeras
        for expected, found in zip(DIAS_SEMANA, days[:5]):
            if expected != found:
                self.logger.warning(f"Día incorrecto: esperado {expected}, encontrado {found}")
                return False
        return True
    
    def _normalize_time(self, time_text: str) -> Optional[str]:
        """
        Normaliza tiempos a HH:MM aceptando 1630, 16:30, 16.30, ' 16 : 30 '.
        Valida contra TIME_CONFIG.
        """
        if not time_text:
            return None
        # Solo caracteres válidos
        t = "".join(ch for ch in time_text.strip() if ch in VALID_TIME_CHARS)
        if not t:
            return None

        t = t.replace(".", ":")
        # 830 -> 8:30 ; 1630 -> 16:30
        if ":" not in t and len(t) in (3, 4):
            t = t[:-2] + ":" + t[-2:]

        parts = t.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return None

        hh, mm = int(parts[0]), int(parts[1])

        if not (TIME_CONFIG['min_hour'] <= hh <= TIME_CONFIG['max_hour']):
            return None
        if not (TIME_CONFIG['min_minute'] <= mm <= TIME_CONFIG['max_minute']):
            return None

        return f"{hh:02d}:{mm:02d}"

    def _validate_times(self, times: List[str]) -> bool:
        """
        Valida la secuencia de horas:
        - Compacta duplicados consecutivos (09:30, 09:30 -> 09:30)
        - Exige al menos TIME_CONFIG['min_franjas'] marcas únicas
        - Verifica orden no decreciente
        """
        if not times:
            self.logger.warning("Pocas franjas horarias: 0")
            return False

        # 1) Compactar duplicados consecutivos
        uniq: List[str] = []
        last = None
        for t in times:
            if not t:
                continue
            if t != last:
                uniq.append(t)
                last = t

        if len(uniq) < TIME_CONFIG['min_franjas']:
            self.logger.warning(f"Pocas franjas horarias: {len(uniq)}")
            return False

        # 2) Orden no decreciente (permitimos igualdad si hubiera ruido residual)
        def to_minutes(s: str) -> int:
            h, m = s.split(":")
            return int(h)*60 + int(m)

        mins = [to_minutes(t) for t in uniq]
        for i in range(len(mins) - 1):
            if mins[i] > mins[i+1]:
                self.logger.warning(f"Orden temporal incorrecto: {uniq[i]} -> {uniq[i+1]}")
                return False

        return True
    
    def _compact_grid_by_time(self, time_rows: List[str], celdas: List[List[Optional[str]]]) -> tuple[List[str], List[List[Optional[str]]]]:
        """
        Compacta filas consecutivas con la misma hora, fusionando contenido columna a columna.
        La regla de fusión es "primero no vacío".
        """
        if not time_rows or not celdas:
            return time_rows, celdas

        new_times: List[str] = []
        new_rows: List[List[Optional[str]]] = []

        for idx, t in enumerate(time_rows):
            if not new_times or t != new_times[-1]:
                new_times.append(t)
                new_rows.append(celdas[idx])
            else:
                # fusionar con la última fila
                prev = new_rows[-1]
                cur = celdas[idx]
                merged = []
                for j in range(max(len(prev), len(cur))):
                    a = prev[j] if j < len(prev) else None
                    b = cur[j] if j < len(cur) else None
                    merged.append(a if (a and a.strip()) else (b if (b and b.strip()) else None))
                new_rows[-1] = merged

        return new_times, new_rows
    
    def _fix_multiline_names(self, text: str) -> Optional[str]:
        """
        Corrige nombres de asignaturas fragmentados en múltiples líneas.
        
        CORRECCIÓN v2:
        - NO procesa "en" para evitar fragmentar "Diferencial", "General", etc.
        
        Casos a corregir:
        1. "Estructura de\nMoléculas y Sólidos" → "Estructura de Moléculas y Sólidos"
        2. "Mecánica Clásica\ny relatividad" → "Mecánica Clásica y relatividad"
        3. "MecánicaClásica yrelatividad" → "Mecánica Clásica y relatividad"
        4. "Física\nAtómica y Molecular" → "Física Atómica y Molecular"
        
        Args:
            text: Texto potencialmente fragmentado
            
        Returns:
            Texto corregido o None si está vacío
        """
        if not text:
            return None
        
        # 1. Unir líneas que son continuación de nombre
        # Patrón: minúscula + \n + Mayúscula (ej: "Clásica\nY")
        text = re.sub(r'([a-záéíóúñ])\n([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
        
        # 2. Caso específico: preposiciones al final de línea
        # "Estructura de\nMoléculas" → "Estructura de Moléculas"
        # IMPORTANTE: NO incluir "en" para evitar "Difer-en-cial"
        text = re.sub(r'\b(de|y|con|para)\s*\n', r'\1 ', text, flags=re.IGNORECASE)
        
        # 3. Caso específico: preposiciones al inicio de línea
        # "Física\ny Molecular" → "Física y Molecular"
        text = re.sub(r'\n\s*(de|y|con|para)\b', r' \1', text, flags=re.IGNORECASE)
        
        # 4. Unir palabras pegadas (sin espacio)
        # "MecánicaClásica" → "Mecánica Clásica"
        text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
        
        # 5. Preposiciones pegadas: "yrelatividad" → "y relatividad"
        text = re.sub(r'([a-záéíóúñ])([yY])([A-ZÁÉÍÓÚÑ])', r'\1 \2 \3', text)
        text = re.sub(r'([a-záéíóúñ])(de|con|para)([A-ZÁÉÍÓÚÑ])', r'\1 \2 \3', text, flags=re.IGNORECASE)
        
        # 6. Normalizar múltiples espacios
        text = re.sub(r'\s{2,}', ' ', text)
        
        return text.strip() or None

    def _merge_subject_and_room_cells(self, celdas: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
        """
        Post-procesa celdas para fusionar asignaturas con sus aulas/grupos.
        
        MEJORAS v2:
        - Condiciones de fusión menos restrictivas
        - Mejor detección de fragmentos inválidos
        - Logging detallado para debugging
        
        Estrategia:
        1. Iterar por columna (día) para mantener contexto vertical
        2. Para cada celda con contenido SIN aula:
        - Buscar en fila N+1 si tiene solo aula → fusionar
        - Buscar en fila N+2 si tiene solo grupo → fusionar también
        3. Vaciar celdas fusionadas para evitar duplicados
        
        Args:
            celdas: Matriz de celdas [fila][columna]
        
        Returns:
            Matriz de celdas con fusiones aplicadas
        """
        from core.extraccion.newhorarios.constants import MIN_FRAGMENT_LENGTH
        
        if not celdas:
            return celdas
        
        num_rows = len(celdas)
        num_cols = len(celdas[0]) if celdas else 0
        
        fusiones_aplicadas = 0
        
        # Procesar por COLUMNA (día) para mantener contexto temporal
        for col in range(num_cols):
            row = 0
            while row < num_rows - 1:  # -1 porque miramos row+1
                current_cell = celdas[row][col]
                
                # Saltar si celda vacía
                if not current_cell or not current_cell.strip():
                    row += 1
                    continue
                
                # Saltar si es un fragmento muy corto sin sentido ("de", "y", "en")
                if len(current_cell.strip()) < MIN_FRAGMENT_LENGTH:
                    row += 1
                    continue
                
                # Saltar si la celda ES solo aula o solo grupo (no hay nada que fusionar)
                if self._is_only_room(current_cell) or self._is_only_group(current_cell):
                    row += 1
                    continue
                
                # Si la celda actual YA tiene aula, verificar si necesita fusión adicional
                current_has_room = self._has_room(current_cell)
                
                # Buscar aula en fila siguiente (solo si no tiene aula aún)
                if not current_has_room:
                    next_cell = celdas[row + 1][col] if row + 1 < num_rows else None
                    
                    if next_cell and self._is_only_room(next_cell):
                        # FUSIÓN ENCONTRADA
                        merged_text = f"{current_cell}\n{next_cell}"
                        
                        # Buscar grupo en fila N+2 si existe
                        if row + 2 < num_rows:
                            third_cell = celdas[row + 2][col]
                            if third_cell and self._is_only_group(third_cell):
                                merged_text += f"\n{third_cell}"
                                celdas[row + 2][col] = None  # Vaciar fila N+2
                                self.logger.debug(
                                    f"Fusión TRIPLE aplicada en col={col}, row={row}: "
                                    f"'{current_cell[:20]}...' + '{next_cell}' + '{third_cell}'"
                                )
                        
                        # Aplicar fusión
                        celdas[row][col] = merged_text
                        celdas[row + 1][col] = None  # Vaciar fila N+1
                        fusiones_aplicadas += 1
                        
                        self.logger.debug(
                            f"Fusión aplicada en col={col}, row={row}: "
                            f"'{current_cell[:30]}...' + '{next_cell}'"
                        )
                
                row += 1
        
        if fusiones_aplicadas > 0:
            self.logger.info(f"Total de fusiones aplicadas: {fusiones_aplicadas}")
        
        return celdas

    def _compact_time_hits(self, time_hits):
        """
        Une 'time_hits' consecutivos con la misma hora.
        Entrada: [(time, (x0, top, x1, bottom)), ...] ordenados por top.
        Salida: misma estructura pero sin duplicados consecutivos; el bbox se une.
        """
        if not time_hits:
            return time_hits
        compacted = []
        last_t, last_bb = time_hits[0]
        for t, bb in time_hits[1:]:
            if t == last_t:
                # unir verticalmente
                x0 = min(last_bb[0], bb[0]); y0 = min(last_bb[1], bb[1])
                x1 = max(last_bb[2], bb[2]); y1 = max(last_bb[3], bb[3])
                last_bb = (x0, y0, x1, y1)
            else:
                compacted.append((last_t, last_bb))
                last_t, last_bb = t, bb
        compacted.append((last_t, last_bb))
        return compacted


    def _infer_day_columns_from_words(self, page, bbox) -> List[str]:
        """
        Busca etiquetas de día dentro del bbox de la tabla, en la banda superior de esa región,
        y devuelve hasta 5 columnas ordenadas por X.
        """
        x0, y0, x1, y1 = bbox
        H = y1 - y0
        top_band_abs = y0 + 0.35 * H

        region = page.within_bbox(bbox)  
        words = region.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=False) or []

        cand: List[tuple[str, float]] = []
        for w in words:
            txt = (w.get("text") or "").strip().upper()
            day = self._normalize_day(txt)
            # 'top' es relativo a la region, así que lo subimos a coords de página
            if day and (w.get("top", 0) + y0) < top_band_abs:
                cand.append((day, w["x0"]))

        cand.sort(key=lambda t: t[1])
        cols: List[tuple[str, float]] = []
        for d, x in cand:
            if not cols or abs(x - cols[-1][1]) > 18:
                if d not in [dd for dd, _ in cols]:
                    cols.append((d, x))
            if len(cols) == 5:
                break

        return [d for d, _ in cols]
    
    def _strip_spurious_hour(self, text: Optional[str]) -> Optional[str]:
        """
        Elimina horas sueltas al inicio/fin de la celda aunque haya saltos de línea.
        Si la celda es SOLO una hora, vacía.
        """
        if not text:
            return None
        s = text.strip()

        # Si TODO es una hora (ignorando espacios/saltos), vacía
        if RX_HORA.fullmatch(re.sub(r'\s+', '', s)):
            return None

        # Si empieza con hora (permitiendo \s), corta esa hora y devuelve el resto
        m = re.match(r'^\s*' + PATRON_HORA + r'\s*(.*)$', s, flags=re.DOTALL | re.IGNORECASE)
        if m:
            rest = m.group(1).strip()
            if rest:
                return rest

        # Si termina con hora aislada, elimínala
        s2 = re.sub(r'(?:^|\s)' + PATRON_HORA + r'(?:\s*$)', ' ', s, flags=re.IGNORECASE).strip()
        return s2 or None
    
    def _remove_inline_hours(self, text: Optional[str]) -> Optional[str]:
        """
        Elimina horas que queden como tokens aislados EN MEDIO del contenido (líneas sueltas).
        """
        if not text:
            return None
        # borra horas como tokens aislados (respetando letras alrededor)
        s = re.sub(r'(?<!\S)' + PATRON_HORA + r'(?!\S)', '', text, flags=re.IGNORECASE)
        s = re.sub(r'\s{2,}', ' ', s).strip()
        return s or None

    def _is_only_room(self, text: str) -> bool:
        """
        Detecta si una celda contiene SOLO un aula.
        
        MEJORAS v2:
        - Mayor tolerancia en cobertura (60%)
        - Manejo de casos como "AULA 4 bis"
        
        Criterios:
        1. Coincide con PATRON_AULA_COMBINADO
        2. NO contiene texto adicional significativo
        3. Longitud razonable (< MAX_ROOM_LENGTH)
        
        Returns:
            True si la celda contiene solo un aula, False en caso contrario
        """
        from core.extraccion.newhorarios.constants import (
            PATRON_AULA_COMBINADO, MAX_ROOM_LENGTH, MIN_ROOM_PATTERN_COVERAGE
        )
        
        if not text:
            return False
        
        clean = text.strip()
        
        # Verificar longitud razonable
        if len(clean) > MAX_ROOM_LENGTH:
            return False
        
        # Verificar patrón de aula
        match = PATRON_AULA_COMBINADO.search(clean)
        
        # Si hay coincidencia, verificar que sea la mayor parte del texto
        if match:
            matched_text = match.group(0)
            coverage = len(matched_text) / len(clean)
            
            # Logging para debugging
            if coverage < MIN_ROOM_PATTERN_COVERAGE:
                self.logger.debug(
                    f"Aula rechazada por baja cobertura ({coverage:.0%}): '{clean}'"
                )
            
            return coverage >= MIN_ROOM_PATTERN_COVERAGE
        
        return False


    def _is_only_group(self, text: str) -> bool:
        """
        Detecta si una celda contiene SOLO un grupo (PL1, PA2, etc).
        
        Criterios:
        1. Coincide con patrones de grupo
        2. Texto corto (< MAX_GROUP_LENGTH)
        3. NO contiene aula ni asignatura
        
        Returns:
            True si la celda contiene solo un grupo, False en caso contrario
        """
        from core.extraccion.newhorarios.constants import (
            PATRON_GRUPO_PL, PATRON_GRUPO_PA, PATRON_GRUPO_GENERICO, MAX_GROUP_LENGTH
        )
        
        if not text:
            return False
        
        clean = text.strip()
        
        # Verificar longitud
        if len(clean) > MAX_GROUP_LENGTH:
            return False
        
        # Verificar patrones de grupo
        if (PATRON_GRUPO_PL.search(clean) or 
            PATRON_GRUPO_PA.search(clean) or
            PATRON_GRUPO_GENERICO.search(clean)):
            # Verificar que NO tenga aula mezclada
            if not self._has_room(clean):
                return True
        
        return False


    def _has_room(self, text: str) -> bool:
        """
        Detecta si el texto YA contiene un aula.
        
        Returns:
            True si el texto contiene un aula, False en caso contrario
        """
        from core.extraccion.newhorarios.constants import PATRON_AULA_COMBINADO
        
        if not text:
            return False
        return PATRON_AULA_COMBINADO.search(text) is not None

    def _clean_mencion(self, txt: str) -> Optional[str]:
        if not txt:
            return None
        s = " ".join(txt.split())
        # corta a partir de la primera aparición de un día para no arrastrarlos
        for d in ("LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES"):
            pos = s.upper().find(d)
            if pos > -1:
                s = s[:pos].strip()
                break
        m = RX_MENCION.search(s or "")
        return m.group(0).strip() if m else None


    def _extract_table_metadata(self, page, table) -> Tuple[str, Optional[str]]:
        """
        Lee cadena superior a la tabla para extraer curso/mención.
        No lanza excepción: si no encuentra curso, retorna '1º' y mención None.
        """
        try:
            x0, y0, x1, y1 = table.bbox
            above_bbox = (x0, max(0, y0 - 120), x1, y0)
            cropped = page.within_bbox(above_bbox)
            txt = cropped.extract_text() or ""

            curso_match = re.search(PATRONES['curso'], txt, flags=re.IGNORECASE)
            curso = curso_match.group(0).strip() if curso_match else "1º"

            mencion = self._clean_mencion(txt) if hasattr(self, "_clean_mencion") else None
            self.logger.debug(f"Metadata extraída - Curso: {curso}, Mención: {mencion}")
            return curso, mencion

        except Exception as e:
            self.logger.debug(f"Metadata fallback por error ({e}); usando curso=1º, sin mención")
            return "1º", None

        
    def _cell_text_from_words(self, words, bbox, margin: float = 1.5) -> Optional[str]:
        """
        Devuelve el texto de una celda juntando PALABRAS cuyo centro cae dentro del bbox.
        Reduce el 'sangrado' típico de extract_text() en límites de celda.
        """
        x0, y0, x1, y1 = bbox

        def inside(w):
            wx0, wt, wx1, wb = w["x0"], w["top"], w["x1"], w["bottom"]
            cx = (wx0 + wx1) / 2.0
            cy = (wt + wb) / 2.0
            return (x0 + margin) <= cx <= (x1 - margin) and (y0 + margin) <= cy <= (y1 - margin)

        items = [w for w in words if inside(w)]
        if not items:
            return None

        items.sort(key=lambda w: (w["top"], w["x0"]))

        lines = []
        cur = []
        last_top = None
        for w in items:
            ttop = w["top"]
            if last_top is None or abs(ttop - last_top) <= 5:  # ← antes 3
                cur.append(w["text"])
            else:
                lines.append(" ".join(cur))
                cur = [w["text"]]
            last_top = ttop
        if cur:
            lines.append(" ".join(cur))

        text = "\n".join(lines).strip()
        if not text:
            return None

        # Pegar tokens partidos verticalmente: "Computati\non" -> "Computati on"
        # y casos “Laboratori\no” -> “Laboratorio”
        text = re.sub(r'([A-Za-zÁÉÍÓÚÜáéíóúüñÑ])\n([a-záéíóúüñ])', r'\1\2', text)
        return text or None


    def _demote_footnote(self, s: Optional[str]) -> Optional[str]:
        """
        Filtra notas largas tipo 'La programación de prácticas...' que no son sesiones.
        """
        if not s:
            return None
        flat = " ".join(s.split())
        if len(flat) > 120 and any(k in flat.lower() for k in ("prácticas", "practicas", "programación", "programacion")):
            return None
        return s

    def _clear_header_labels_early_rows(self, day_columns: List[str],
                                    celdas: List[List[Optional[str]]],
                                    upto_rows: int = 2) -> None:
        """
        Si por sangrado se colaron etiquetas 'LUNES/MARTES/...' en las
        primeras filas (p.ej. 08:30 y 09:30), bórralas.
        """
        if not celdas:
            return
        days_upper = set(d.upper() for d in day_columns if d)
        limit = min(len(celdas), max(1, upto_rows))
        for i in range(limit):
            row = celdas[i]
            for j, val in enumerate(row):
                if val and val.strip().upper() in days_upper:
                    row[j] = None

    def _merge_split_across_columns(self, row: List[Optional[str]]) -> List[Optional[str]]:
        """
        Une palabras que han quedado partidas entre columnas adyacentes.
        Casos típicos: ['R', 'adiofísica'] -> [None, 'Radiofísica']
                    ['AULA', '8']      -> [None, 'AULA8']
        """
        if not row:
            return row
        for j in range(len(row) - 1):
            a = (row[j] or "").strip()
            b = (row[j + 1] or "").strip()
            if not a or not b:
                continue

            # Izquierda 1 char + derecha empieza en minúscula -> pégalo a la derecha
            if len(a) == 1 and re.match(r'^[a-záéíóúüñ]', b):
                row[j + 1] = a + b
                row[j] = None
                continue

            # Derecha 1 char + izquierda termina en minúscula -> pégalo a la izquierda
            if len(b) == 1 and re.search(r'[a-záéíóúüñ]$', a):
                row[j] = a + b
                row[j + 1] = None
                continue
        return row

    def _is_footnote_row(self, row: List[Optional[str]]) -> bool:
        """
        Considera que una fila es 'nota' si su texto agregado contiene patrones típicos
        y es lo suficientemente larga (para no borrar celdas normales).
        """
        text = " ".join([c or "" for c in row])
        flat = re.sub(r'\s+', ' ', text).lower().strip()
        if not flat:
            return False
        needles = ["(*)", "prácticas", "practicas", "semanas", "programación", "programacion", "inicio del curso"]
        return any(n in flat for n in needles) and len(flat) >= 30

    def _blank_footnote_rows(self, celdas: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
        """
        Reemplaza por None todas las celdas de filas que parezcan notas de pie.
        (Se mantiene la franja horaria, sólo se limpian celdas de días.)
        """
        for i, row in enumerate(celdas):
            if self._is_footnote_row(row):
                celdas[i] = [None] * len(row)
        return celdas
    
    def _strip_inline_asterisk_notes(self, text: Optional[str]) -> Optional[str]:
        """
        Elimina marcas de nota dentro de la celda del estilo '(*) ...' o asterisco final.
        No borra el resto del contenido útil.
        """
        if not text:
            return None
        s = re.sub(r'\(\*\).*$', '', text, flags=re.IGNORECASE).strip()
        s = re.sub(r'\s*\*\s*$', '', s).strip()
        return s or None

    def _quick_pdf_stats(self, pdf_path: str) -> tuple[int, int, int, bool]:
        """(pages, chars, words, has_text) rápido con PyMuPDF o pdfplumber."""
        pages = 0; chars = 0; words = 0; has_text = False
        try:
            doc = fitz.open(pdf_path)
            pages = doc.page_count
            for i in range(pages):
                txt = doc.load_page(i).get_text("text") or ""
                chars += len(txt)
                words += len(txt.split())
                if txt.strip():
                    has_text = True
            doc.close()
        except Exception:
            with pdfplumber.open(pdf_path) as pdf:
                pages = len(pdf.pages)
                for p in pdf.pages:
                    txt = p.extract_text() or ""
                    chars += len(txt)
                    words += len(txt.split())
                    if txt.strip():
                        has_text = True
        return pages, chars, words, has_text

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de uso."""
        return self.stats.copy()


# Instancia global tipada
horario_extractor: Optional[HorarioExtractor] = None

def get_horario_extractor() -> HorarioExtractor:
    """Factory function para obtener instancia global."""
    global horario_extractor
    if horario_extractor is None:
        horario_extractor = HorarioExtractor()
    return horario_extractor