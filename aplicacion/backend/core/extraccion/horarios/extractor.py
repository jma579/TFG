"""
PDF Text Extraction Module — HORARIOS (GRIDMASTER V1.8)
Mejoras: Inferencia geométrica precisa y limpieza de filas vacías.
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
from core.extraccion.horarios.constants import (
    DEFAULT_EXTRACTOR_CONFIG, ATOM_EXTRACT_SETTINGS, 
    RX_CURSO, RX_MENCION, DIAS_REGEX, DAYS_MAP, RX_HORA, VALID_TIME_CHARS, PATRONES_RADAR,
    DIAS_SEMANA
)

# Componentes internos
from core.extraccion.horarios.internal_models import TextAtom, GridCell
from core.extraccion.horarios.grid_detector import GridDetector
from core.extraccion.horarios.spatial_mapper import SpatialMapper

class HorarioExtractor:
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
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
        start_time = time.time()
        tablas_resultado = []
        
        try:
            self._validate_pdf(pdf_path)
            titulo_global = self._extract_title_global(pdf_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    
                    # 1. DETECCIÓN
                    cells = self.detector.detect(page)
                    if not cells: continue
                        
                    # 2. ESCANEO
                    raw_words = page.extract_words(**ATOM_EXTRACT_SETTINGS)
                    atoms = [
                        TextAtom(
                            text=w['text'], 
                            x0=w['x0'], top=w['top'], x1=w['x1'], bottom=w['bottom']
                        ) for w in raw_words
                    ]
                    
                    # 3. MAPEO
                    self.mapper.map_and_stitch(cells, atoms)
                    
                    # 4. CONVERSIÓN
                    tabla = self._convert_grid_to_output(cells, page, page_num)
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
        rows = {}
        grid_col_indices = set(c.col_idx for c in cells)
        for c in cells:
            rows.setdefault(c.row_idx, []).append(c)

        # A. IDENTIFICAR DÍAS
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
        # Inferencia geométrica (Recupera LUNES vacío)
        day_map = self._infer_missing_days_geometric(day_map, grid_col_indices)

        # Fallback Agresivo
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

        # B. IDENTIFICAR HORAS Y DATOS
        first_day_col_idx = min(day_map.keys())
        time_rows = []     
        celdas_matrix = []
        
        sorted_day_cols = sorted(day_map.keys())
        
        for r_idx in sorted(rows.keys()):
            # Detectar Hora
            left_cells = [c for c in rows[r_idx] if c.col_idx < first_day_col_idx]
            left_cells.sort(key=lambda c: c.col_idx, reverse=True)
            
            row_time = None
            for lc in left_cells:
                if not lc.final_text: continue
                t = self._normalize_time(lc.final_text.replace('\n', ' '))
                if t:
                    row_time = t
                    break
            
            # Recopilar Datos
            row_data = []
            current_cells = {c.col_idx: c for c in rows[r_idx]}
            has_content = False
            
            for c_idx in sorted_day_cols:
                cell = current_cells.get(c_idx)
                txt = cell.final_text if cell else None
                if txt: has_content = True
                row_data.append(txt)
            
            # Añadir fila cruda (la filtraremos después)
            time_rows.append(row_time) # Puede ser None
            celdas_matrix.append(row_data)

        # C. LIMPIEZA DE FILAS VACÍAS
        clean_times, clean_matrix = self._clean_empty_rows(time_rows, celdas_matrix)
        
        if not clean_times:
            return None

        # D. METADATA
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

    # --- Helpers Lógicos ---

    def _clean_empty_rows(self, time_rows: List[Optional[str]], matrix: List[List[Optional[str]]]):
        """Elimina filas que no tienen hora Y no tienen contenido."""
        final_times = []
        final_matrix = []
        
        # Propagar horas hacia abajo si hay huecos en filas con datos
        last_valid_time = None
        
        for i, row_data in enumerate(matrix):
            t = time_rows[i]
            
            # Verificar si la fila tiene contenido real
            is_empty = all(not c or not c.strip() for c in row_data)
            
            # CRITERIO DE CONSERVACIÓN:
            # 1. Tiene hora explícita
            # 2. O tiene datos (aunque no tenga hora, quizás es continuación)
            if t or not is_empty:
                # Si tenemos datos pero no hora, intentamos inferir o dejar null
                final_times.append(t if t else last_valid_time) # O dejar None
                final_matrix.append(row_data)
                
                if t: last_valid_time = t
        
        return final_times, final_matrix

    def _check_if_has_hours(self, rows) -> bool:
        hours_detected = 0
        for r_idx in rows:
            for cell in rows[r_idx]:
                if cell.final_text and self._normalize_time(cell.final_text.replace('\n', ' ')):
                    hours_detected += 1
        return hours_detected >= 3

    def _find_hour_column(self, rows, sorted_cols) -> Optional[int]:
        col_scores = {c: 0 for c in sorted_cols}
        for r_idx in rows:
            for cell in rows[r_idx]:
                if cell.final_text and self._normalize_time(cell.final_text.replace('\n', ' ')):
                    col_scores[cell.col_idx] += 1
        best_col = max(col_scores, key=col_scores.get)
        if col_scores[best_col] >= 3: return best_col
        return None

    def _deduplicate_columns(self, day_map: Dict[int, str], cells: List[GridCell]) -> Dict[int, str]:
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

    # --- Helpers ---
    def _validate_pdf(self, path):
        if not Path(path).exists(): raise ValueError("PDF not found")

    def _identify_day_regex(self, text):
        for key, rx in DIAS_REGEX.items():
            if rx.search(text): return DAYS_MAP[key]
        return None

    def _normalize_time(self, text):
        clean = text.replace('\n', ' ').strip()
        match = RX_HORA.search(clean)
        if match:
            t = match.group(0).replace('.', ':')
            parts = t.split(':')
            if len(parts) == 2:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return None

    def _extract_title_global(self, pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                txt = first_page.within_bbox((0,0, first_page.width, first_page.height/3)).extract_text()
                if txt:
                    rx = re.compile(PATRONES_RADAR['titulo'], re.IGNORECASE | re.DOTALL)
                    m = rx.search(txt)
                    if m: return m.group(0).replace('\n', ' ').strip()
        except: pass
        return "Horario Académico"

    def _extract_metadata_radar(self, page, table_bbox):
        try:
            _, y0, _, _ = table_bbox
            search_area = (0, max(0, y0 - 250), page.width, y0)
            txt = page.within_bbox(search_area).extract_text(x_tolerance=3) or ""
            txt = txt.replace('\n', ' ')
            
            curso = "1º"
            m_c = RX_CURSO.search(txt)
            if m_c: curso = m_c.group(0).strip()
            
            mencion = None
            m_m = RX_MENCION.search(txt)
            if m_m:
                raw = m_m.group(0)
                mencion = re.sub(r'MENCI[ÓO]N\s+EN\s+', '', raw, flags=re.IGNORECASE).strip()
            return curso, mencion
        except: return "1º", None

    def _build_error_result(self, error, start_time):
        return HorarioExtractionResult(
            titulo="Error", tablas=[],
            metadata=ExtractionMetadata(
                quality=ExtractionQuality.UNUSABLE, confidence=0.0, 
                status=ProcessingStatus.FAILED, processing_time_seconds=time.time()-start_time,
                page_count=0, file_size_mb=0, has_embedded_text=False, char_count=0, word_count=0,
                errors=[str(error)], warnings=[], pages_with_text=0
            )
        )