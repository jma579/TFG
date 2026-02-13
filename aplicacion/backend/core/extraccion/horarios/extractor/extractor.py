"""
PDF Text Extraction Module — HORARIOS (GRIDMASTER)
"""

from typing import Dict, Optional, List, Set
import logging
from pathlib import Path
import time
import pdfplumber
import re

from core.extraccion.common.entities import (
    ExtractionQuality, ProcessingStatus, ExtractionMetadata
)
from core.extraccion.horarios.entities import (
    HorarioExtractionResult, TablaHorario
)
from core.extraccion.horarios.extractor.constants import (
    DEFAULT_EXTRACTOR_CONFIG, ATOM_EXTRACT_SETTINGS, 
    RX_CURSO, RX_MENCION, DIAS_REGEX, DAYS_MAP, RX_HORA, VALID_TIME_CHARS, PATRONES_RADAR,
    DIAS_SEMANA, LABEL_PERIODO_1, LABEL_PERIODO_2, 
    LABEL_GRADO_FISICA, LABEL_GRADO_MATEMATICAS, 
    LABEL_GRADO_INFORMATICA, LABEL_GRADO_DOBLE, LABEL_GRADO_UNKNOWN,
    KEYWORDS_PERIODO_1, KEYWORDS_PERIODO_2,
    KEYWORDS_FISICA, KEYWORDS_MATEMATICAS, KEYWORDS_DOBLE, KEYWORDS_INFORMATICA,
    MAPA_CURSOS, KEYWORDS_TABLE_CONTENT, RX_FOOTER_CUTOFF
)

from core.extraccion.horarios.extractor.internal_models import TextAtom, GridCell
from core.extraccion.horarios.extractor.grid_detector import GridDetector
from core.extraccion.horarios.extractor.spatial_mapper import SpatialMapper

class HorarioExtractor:
    """Extractor principal de horarios académicos desde PDF.
    
    Implementa un pipeline de extracción en múltiples etapas:
    1. Detección de rejilla (grid) de tablas
    2. Extracción de átomos de texto
    3. Mapeo espacial y reconstrucción de contenido
    4. Identificación de metadatos (curso, mención, periodo)
    5. Validación y limpieza de resultados
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Inicializa el extractor con configuración opcional."""
        self.logger = logging.getLogger(__name__)

        # Configuración de silencio para librerías ruidosas
        logging.getLogger("pdfminer").setLevel(logging.ERROR)
        logging.getLogger("python_multipart").setLevel(logging.WARNING)
        logging.getLogger("multipart").setLevel(logging.WARNING)
        
        self.config = DEFAULT_EXTRACTOR_CONFIG.copy()
        if config:
            self.config.update(config)
            
        if 'log_level' in self.config:
            try:
                self.logger.setLevel(getattr(logging, self.config['log_level'].upper(), logging.INFO))
            except: pass

        self.detector = GridDetector()
        self.mapper = SpatialMapper()

    def extract(self, pdf_path: str) -> HorarioExtractionResult:
        """Extrae horarios académicos desde un archivo PDF dado."""
        start_time = time.time()
        tablas_resultado = []
        
        try:
            self._validate_pdf(pdf_path)
            titulo_global = self._extract_title_global(pdf_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    
                    # Deteccion de celdas
                    cells = self.detector.detect(page)
                    if not cells: continue
                    
                    # Escaneo de atomos
                    raw_words = page.extract_words(**ATOM_EXTRACT_SETTINGS)
                    atoms = [
                        TextAtom(
                            text=w['text'], 
                            x0=w['x0'], top=w['top'], x1=w['x1'], bottom=w['bottom']
                        ) for w in raw_words
                    ]
                    
                    cutoff_y = self._calculate_footer_cutoff(atoms, page.height)
                    
                    valid_cells = [c for c in cells if c.bottom <= cutoff_y + 5]
                    valid_atoms = [a for a in atoms if a.top <= cutoff_y]
                    
                    if not valid_cells:
                        continue
                        
                    # Mapeo espacial y reconstrucción de texto
                    self.mapper.map_and_stitch(valid_cells, valid_atoms)
                    
                    # Conversión a formato de salida
                    tabla = self._convert_grid_to_output(valid_cells, page, page_num)
                    if tabla:
                        tablas_resultado.append(tabla)
            
            meta = ExtractionMetadata(
                quality=ExtractionQuality.GOOD if tablas_resultado else ExtractionQuality.UNUSABLE,
                confidence=0.98 if tablas_resultado else 0.0,
                status=ProcessingStatus.COMPLETED if tablas_resultado else ProcessingStatus.FAILED,
                processing_time_seconds=time.time() - start_time,
                page_count=len(tablas_resultado),
                file_size_mb=Path(pdf_path).stat().st_size / (1024*1024),
                has_embedded_text=True, char_count=0, word_count=0, errors=[], warnings=[],
                pages_with_text=len(tablas_resultado)
            )

            return HorarioExtractionResult(
                titulo=titulo_global,
                tablas=tablas_resultado,
                metadata=meta
            )

        except Exception as e:
            self.logger.exception(f"Error Gridmaster: {e}")
            return self._build_error_result(e, start_time)

    def _convert_grid_to_output(self, cells: List[GridCell], page, page_num: int) -> Optional[TablaHorario]:
        """Convierte la estructura de celdas con texto mapeado a una TablaHorario estructurada."""
        rows = {}
        grid_col_indices = set(c.col_idx for c in cells)
        for c in cells:
            rows.setdefault(c.row_idx, []).append(c)

        # Identificar columnas de días usando regex y heurísticas
        day_map = {} 
        header_row_limit = min(12, len(rows))
        
        for r_idx in sorted(rows.keys())[:header_row_limit]:
            for cell in rows[r_idx]:
                if not cell.final_text: continue
                txt = self._identify_day_regex(cell.final_text)
                if txt:
                    if cell.col_idx not in day_map:
                        day_map[cell.col_idx] = txt
        
        day_map = self._deduplicate_columns(day_map, cells)
        day_map = self._infer_missing_days_geometric(day_map, grid_col_indices)

        if len(day_map) < 3:
            has_hours = self._check_if_has_hours(rows)
            if has_hours:
                sorted_cols = sorted(list(grid_col_indices))
                hour_col_idx = self._find_hour_column(rows, sorted_cols)
                if hour_col_idx is not None:
                    try:
                        hour_pos = sorted_cols.index(hour_col_idx)
                        candidate_day_cols = sorted_cols[hour_pos+1:]
                        for i, day_name in enumerate(DIAS_SEMANA):
                            if i < len(candidate_day_cols):
                                day_map[candidate_day_cols[i]] = day_name
                        self.logger.info(f"Página {page_num + 1}: Inferencia agresiva aplicada.")
                    except ValueError: pass

        if len(day_map) < 3:
            return None

        # Identificar horas y datos
        first_day_col_idx = min(day_map.keys())
        time_rows = []     
        celdas_matrix = []
        
        sorted_day_cols = sorted(day_map.keys())
        
        for r_idx in sorted(rows.keys()):
            left_cells = [c for c in rows[r_idx] if c.col_idx < first_day_col_idx]
            left_cells.sort(key=lambda c: c.col_idx, reverse=True)
            
            row_time = None
            for lc in left_cells:
                if not lc.final_text: continue
                t = self._normalize_time(lc.final_text.replace('\n', ' '))
                if t:
                    row_time = t
                    break
            
            row_data = []
            current_cells = {c.col_idx: c for c in rows[r_idx]}
            has_content = False
            
            for c_idx in sorted_day_cols:
                cell = current_cells.get(c_idx)
                txt = cell.final_text if cell else None
                if txt: has_content = True
                row_data.append(txt)
            
            time_rows.append(row_time) 
            celdas_matrix.append(row_data)

        # Limpiar filas vacías
        clean_times, clean_matrix = self._clean_empty_rows(time_rows, celdas_matrix)
        
        if not clean_times:
            return None

        # Metadatos
        all_x0 = min(c.x0 for c in cells)
        all_top = min(c.top for c in cells)
        all_x1 = max(c.x1 for c in cells)
        all_bottom = max(c.bottom for c in cells)
        
        curso, mencion = self._extract_metadata_radar(page, (all_x0, all_top, all_x1, all_bottom))

        return TablaHorario(
            curso=curso,
            mencion=mencion,
            pagina=page_num,
            day_columns=[day_map[k] for k in sorted_day_cols],
            time_rows=clean_times,
            celdas=clean_matrix
        )


    def _clean_empty_rows(self, time_rows: List[Optional[str]], matrix: List[List[Optional[str]]]):
        """Elimina filas que no tienen hora Y no tienen contenido."""
        final_times = []
        final_matrix = []
        
        last_valid_time = None
        
        for i, row_data in enumerate(matrix):
            t = time_rows[i]
            
            is_empty = all(not c or not c.strip() for c in row_data)
            
            if t or not is_empty:
                final_times.append(t if t else last_valid_time)
                final_matrix.append(row_data)
                
                if t: last_valid_time = t
        
        return final_times, final_matrix

    def _check_if_has_hours(self, rows) -> bool:
        """Verifica si hay suficientes celdas con formato de hora para considerar que es un horario."""
        hours_detected = 0
        for r_idx in rows:
            for cell in rows[r_idx]:
                if cell.final_text and self._normalize_time(cell.final_text.replace('\n', ' ')):
                    hours_detected += 1
        return hours_detected >= 3

    def _find_hour_column(self, rows, sorted_cols) -> Optional[int]:
        """Intenta identificar la columna de horas basada en la cantidad de celdas con formato de hora."""
        col_scores = {c: 0 for c in sorted_cols}
        for r_idx in rows:
            for cell in rows[r_idx]:
                if cell.final_text and self._normalize_time(cell.final_text.replace('\n', ' ')):
                    col_scores[cell.col_idx] += 1
        best_col = max(col_scores, key=col_scores.get)
        if col_scores[best_col] >= 3: return best_col
        return None

    def _deduplicate_columns(self, day_map: Dict[int, str], cells: List[GridCell]) -> Dict[int, str]:
        """En caso de detectar el mismo día en múltiples columnas, elige la más probable basada en contenido."""
        day_to_cols = {}
        for col_idx, day_name in day_map.items():
            day_to_cols.setdefault(day_name, []).append(col_idx)
        final_map = {}
        for day_name, col_indices in day_to_cols.items():
            if len(col_indices) == 1:
                final_map[col_indices[0]] = day_name
            else:
                best_col = -1
                max_content = -1
                for c_idx in col_indices:
                    col_cells = [c for c in cells if c.col_idx == c_idx]
                    content_len = sum(len(c.final_text or "") for c in col_cells)
                    if content_len > max_content:
                        max_content = content_len
                        best_col = c_idx
                final_map[best_col] = day_name
        return final_map

    def _infer_missing_days_geometric(self, day_map: Dict[int, str], grid_cols: Set[int]) -> Dict[int, str]:
        """Si faltan días, intenta inferirlos basándose en la posición de las columnas detectadas."""
        if not day_map: return day_map
        sorted_physical_cols = sorted(list(grid_cols))
        canon_days = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES']
        
        anchor_col = -1
        anchor_day_idx = -1
        for col, day_name in day_map.items():
            if day_name in canon_days:
                anchor_col = col
                anchor_day_idx = canon_days.index(day_name)
                break
        
        if anchor_col == -1: return day_map
        
        try:
            anchor_pos_in_grid = sorted_physical_cols.index(anchor_col)
            new_map = day_map.copy()
            for i, col_idx in enumerate(sorted_physical_cols):
                dist = i - anchor_pos_in_grid
                target_day_idx = anchor_day_idx + dist
                if 0 <= target_day_idx < len(canon_days):
                    expected_day = canon_days[target_day_idx]
                    if col_idx not in new_map:
                        new_map[col_idx] = expected_day
                        self.logger.debug(f"Inferido {expected_day} en col {col_idx}")
            return new_map
        except ValueError:
            return day_map


    def _validate_pdf(self, path):
        """Verifica si el archivo PDF existe."""
        if not Path(path).exists(): raise ValueError("PDF not found")

    def _identify_day_regex(self, text):
        """Intenta identificar el día de la semana en un texto usando regex."""
        for key, rx in DIAS_REGEX.items():
            if rx.search(text): return DAYS_MAP[key]
        return None

    def _normalize_time(self, text):
        """Intenta normalizar un string a formato HH:MM usando regex y limpieza."""
        clean = text.replace('\n', ' ').strip()
        match = RX_HORA.search(clean)
        if match:
            t = match.group(0).replace('.', ':')
            parts = t.split(':')
            if len(parts) == 2:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return None

    def _extract_title_global(self, pdf_path):
        """Detecta Grado y Periodo usando configuraciones centralizadas en constants.py."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = pdf.pages[0].extract_text() or ""
                text_upper = text.upper().replace('\n', ' ')

                periodo = LABEL_PERIODO_1 
                
                if any(kw in text_upper for kw in KEYWORDS_PERIODO_2):
                    periodo = LABEL_PERIODO_2
                elif any(kw in text_upper for kw in KEYWORDS_PERIODO_1):
                    periodo = LABEL_PERIODO_1

                grado = LABEL_GRADO_UNKNOWN
                
                is_doble = any(kw in text_upper for kw in KEYWORDS_DOBLE) 
                has_fisica = any(kw in text_upper for kw in KEYWORDS_FISICA)
                has_mate = any(kw in text_upper for kw in KEYWORDS_MATEMATICAS)
                
                if is_doble and has_fisica and has_mate:
                    grado = LABEL_GRADO_DOBLE
                elif any(kw in text_upper for kw in KEYWORDS_INFORMATICA):
                    grado = LABEL_GRADO_INFORMATICA
                elif "GRADO" in text_upper and has_mate:
                    grado = LABEL_GRADO_MATEMATICAS
                elif "GRADO" in text_upper and has_fisica:
                    grado = LABEL_GRADO_FISICA
                
                return f"{grado}|{periodo}"

        except Exception as e:
            self.logger.error(f"Error extrayendo título global: {e}")
            return f"{LABEL_GRADO_UNKNOWN}|{LABEL_PERIODO_1}"

    def _extract_metadata_radar(self, page, table_bbox):
        """Intenta extraer metadatos de curso y mención usando un enfoque de radar que escanea el área alrededor de la tabla."""
        try:
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3) or ""
            
            text = re.sub(r'(?:PRIMER|SEGUNDO|1º|2º)\s+CUATRIMESTRE', '', text, flags=re.IGNORECASE)
            
            lines = text.split('\n')
            
            best_curso = None
            best_curso_score = 0
            
            longest_mencion = None
            
            for line in lines:
                line_clean = line.strip()
                line_upper = line_clean.upper()
                
                if not line_clean: continue
                
                if any(kw in line_upper for kw in KEYWORDS_TABLE_CONTENT):
                    continue

                m_c = RX_CURSO.search(line_clean)
                if m_c:
                    raw_match = m_c.group(0).upper()
                    
                    token = re.sub(r'\s*CURSO\s*|º|°', '', raw_match).strip()
                    
                    current_score = 0
                    candidate_val = None

                    if token in MAPA_CURSOS:
                        candidate_val = MAPA_CURSOS[token]
                    else:
                        for k, v in MAPA_CURSOS.items():
                            if re.search(rf'\b{k}\b', token):
                                candidate_val = v
                                break
                    
                    if candidate_val:
                        if "CURSO" in raw_match:
                            current_score = 100
                        elif len(token) > 2: 
                            current_score = 50
                        else:
                            current_score = 20
                        
                        if current_score > best_curso_score:
                            best_curso = candidate_val
                            best_curso_score = current_score

                m_m = RX_MENCION.search(line_clean)
                if m_m:
                    if m_m.lastindex and m_m.lastindex >= 1:
                        raw_mencion = m_m.group(1).strip()
                    else:
                        raw_mencion = m_m.group(0).strip()
                    
                    clean_mencion = re.split(r'\s{3,}', raw_mencion)[0].strip()
                    
                    if not longest_mencion or len(clean_mencion) > len(longest_mencion):
                        longest_mencion = clean_mencion

            final_curso = best_curso if best_curso else "N.A."
            
            return final_curso, longest_mencion

        except Exception as e:
            self.logger.warning(f"Fallo radar metadata: {e}")
            return "N.A.", None
        
    def _calculate_footer_cutoff(self, atoms: List[TextAtom], page_height: float) -> float:
        """
        Busca frases de pie de página y devuelve la coordenada Y donde empiezan.
        Si no encuentra nada, devuelve la altura de la página (sin corte).
        """
        sorted_atoms = sorted(atoms, key=lambda a: (a.top, a.x0))
        
        current_line_text = ""
        current_line_top = 0
        
        line_threshold = 5 
        
        cutoff_candidate = page_height

        for atom in sorted_atoms:
            if atom.top - current_line_top > line_threshold:
                for rx in RX_FOOTER_CUTOFF:
                    if rx.search(current_line_text):
                        return current_line_top - 2 
                
                current_line_text = atom.text
                current_line_top = atom.top
            else:
                current_line_text += " " + atom.text
        
        for rx in RX_FOOTER_CUTOFF:
            if rx.search(current_line_text):
                return current_line_top - 2

        return cutoff_candidate
        
    def _build_error_result(self, error, start_time):
        """Construye un resultado de extracción con estado de error."""
        return HorarioExtractionResult(
            titulo="Error", tablas=[],
            metadata=ExtractionMetadata(
                quality=ExtractionQuality.UNUSABLE, confidence=0.0, 
                status=ProcessingStatus.FAILED, processing_time_seconds=time.time()-start_time,
                page_count=0, file_size_mb=0, has_embedded_text=False, char_count=0, word_count=0,
                errors=[str(error)], warnings=[], pages_with_text=0
            )
        )