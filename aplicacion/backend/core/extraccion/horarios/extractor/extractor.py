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

# Componentes internos
from core.extraccion.horarios.extractor.internal_models import TextAtom, GridCell
from core.extraccion.horarios.extractor.grid_detector import GridDetector
from core.extraccion.horarios.extractor.spatial_mapper import SpatialMapper

class HorarioExtractor:
    
    def __init__(self, config: Optional[Dict] = None):
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
        start_time = time.time()
        tablas_resultado = []
        
        try:
            self._validate_pdf(pdf_path)
            titulo_global = self._extract_title_global(pdf_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    
                    # 1. DETECCIÓN DE CELDAS
                    cells = self.detector.detect(page)
                    if not cells: continue
                    
                    # 2. ESCANEO DE ÁTOMOS
                    raw_words = page.extract_words(**ATOM_EXTRACT_SETTINGS)
                    atoms = [
                        TextAtom(
                            text=w['text'], 
                            x0=w['x0'], top=w['top'], x1=w['x1'], bottom=w['bottom']
                        ) for w in raw_words
                    ]
                    
                    # --- NUEVO: FOOTER CROPPER (LA GUILLOTINA) ---
                    # Calculamos dónde empieza el pie de página
                    cutoff_y = self._calculate_footer_cutoff(atoms, page.height)
                    
                    # Filtramos celdas y átomos que estén por debajo de la línea roja
                    # Damos un margen de 5px por si acaso
                    valid_cells = [c for c in cells if c.bottom <= cutoff_y + 5]
                    valid_atoms = [a for a in atoms if a.top <= cutoff_y]
                    
                    if not valid_cells:
                        continue
                        
                    # 3. MAPEO (Usamos las listas filtradas)
                    self.mapper.map_and_stitch(valid_cells, valid_atoms)
                    
                    # 4. CONVERSIÓN
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
        """
        Estrategia V3.2 (Clean Code con Constantes):
        Detecta Grado y Periodo usando configuraciones centralizadas en constants.py.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = pdf.pages[0].extract_text() or ""
                text_upper = text.upper().replace('\n', ' ')

                # 1. DETECCIÓN DE PERIODO
                periodo = LABEL_PERIODO_1 # Default
                
                if any(kw in text_upper for kw in KEYWORDS_PERIODO_2):
                    periodo = LABEL_PERIODO_2
                elif any(kw in text_upper for kw in KEYWORDS_PERIODO_1):
                    periodo = LABEL_PERIODO_1

                # 2. DETECCIÓN DE GRADO (Lógica Refinada)
                grado = LABEL_GRADO_UNKNOWN
                
                # Banderas
                is_doble = any(kw in text_upper for kw in KEYWORDS_DOBLE) 
                has_fisica = any(kw in text_upper for kw in KEYWORDS_FISICA)
                has_mate = any(kw in text_upper for kw in KEYWORDS_MATEMATICAS)
                
                # El archivo de Física solo tiene "DOBLE" (en nota al pie) y "FÍSICA", pero no "MATEMÁTICAS".
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
        """
        Estrategia V5 (Scoring System):
        Escanea la página buscando candidatos para Curso y Mención.
        Asigna puntaje basada en la calidad de la coincidencia para evitar
        falsos positivos por ruido (ej: números de página).
        """
        try:
            # 1. Extracción completa preservando layout
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3) or ""
            
            # 2. Limpieza de Cuatrimestre (Vital para no confundir 'Segundo Cuatrimestre')
            text = re.sub(r'(?:PRIMER|SEGUNDO|1º|2º)\s+CUATRIMESTRE', '', text, flags=re.IGNORECASE)
            
            lines = text.split('\n')
            
            # Variables para el "Campeón" actual
            best_curso = None
            best_curso_score = 0
            
            # Para mención, usaremos la más larga encontrada (más específica)
            longest_mencion = None
            
            for line in lines:
                line_clean = line.strip()
                line_upper = line_clean.upper()
                
                if not line_clean: continue
                
                # A. FILTRO DE TABLA Y RUIDO
                # Si la línea parece parte del horario o pie de página técnico, la ignoramos.
                if any(kw in line_upper for kw in KEYWORDS_TABLE_CONTENT):
                    continue

                # B. BUSCAR CURSO (SISTEMA DE PUNTOS CORREGIDO)
                m_c = RX_CURSO.search(line_clean)
                if m_c:
                    raw_match = m_c.group(0).upper()
                    
                    # CORRECCIÓN DE BUG CRÍTICO:
                    # Eliminamos "CURSO", "º", "°". 
                    # YA NO ELIMINAMOS "ER" CIEGAMENTE para no romper "PRIMER"/"TERCER".
                    # Si viene "1ER", el mapa lo gestionará (MAPA_CURSOS["1ER"] = "1º").
                    token = re.sub(r'\s*CURSO\s*|º|°', '', raw_match).strip()
                    
                    current_score = 0
                    candidate_val = None

                    # Validar en mapa
                    if token in MAPA_CURSOS:
                        candidate_val = MAPA_CURSOS[token]
                    else:
                        # Búsqueda palabra completa en claves del mapa
                        # Esto ayuda si el token es "GRADO TERCER" (raro, pero posible)
                        for k, v in MAPA_CURSOS.items():
                            # Usamos bordes de palabra \b para evitar falsos positivos
                            if re.search(rf'\b{k}\b', token):
                                candidate_val = v
                                break
                    
                    if candidate_val:
                        # --- ASIGNACIÓN DE PUNTOS ---
                        # 1. Si contiene la palabra "CURSO" explícita -> Puntuación Máxima (Certeza)
                        if "CURSO" in raw_match:
                            current_score = 100
                        # 2. Si es una palabra larga (PRIMER, SEGUNDO...) -> Puntuación Media
                        elif len(token) > 2: 
                            current_score = 50
                        # 3. Si es ordinal corto (1º, 2º) -> Puntuación Baja
                        # (Sirve de fallback si no hay título explícito "CURSO")
                        else:
                            current_score = 20
                        
                        # Actualizar si encontramos un mejor candidato
                        if current_score > best_curso_score:
                            best_curso = candidate_val
                            best_curso_score = current_score

                # C. BUSCAR MENCIÓN
                m_m = RX_MENCION.search(line_clean)
                if m_m:
                    if m_m.lastindex and m_m.lastindex >= 1:
                        raw_mencion = m_m.group(1).strip()
                    else:
                        raw_mencion = m_m.group(0).strip()
                    
                    # Limpieza
                    clean_mencion = re.split(r'\s{3,}', raw_mencion)[0].strip()
                    
                    # Nos quedamos con la mención más larga encontrada (evita fragmentos)
                    if not longest_mencion or len(clean_mencion) > len(longest_mencion):
                        longest_mencion = clean_mencion

            # Si después de todo no hay curso (score 0), devolvemos "1º" por defecto lógico
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
        # Ordenamos átomos por posición vertical para leer en orden
        sorted_atoms = sorted(atoms, key=lambda a: (a.top, a.x0))
        
        # Reconstruimos líneas de texto aproximadas para aplicar regex
        current_line_text = ""
        current_line_top = 0
        
        # Umbral para considerar que estamos en la misma línea
        line_threshold = 5 
        
        cutoff_candidate = page_height

        for atom in sorted_atoms:
            # Si cambiamos de línea visualmente
            if atom.top - current_line_top > line_threshold:
                # Procesamos la línea anterior
                for rx in RX_FOOTER_CUTOFF:
                    if rx.search(current_line_text):
                        # ¡ENCONTRADO! El corte es el inicio de esta línea
                        # Retornamos un poco antes para no cortar justo en el texto
                        return current_line_top - 2 
                
                # Reseteamos para nueva línea
                current_line_text = atom.text
                current_line_top = atom.top
            else:
                current_line_text += " " + atom.text
        
        # Comprobar la última línea
        for rx in RX_FOOTER_CUTOFF:
            if rx.search(current_line_text):
                return current_line_top - 2

        return cutoff_candidate
        
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