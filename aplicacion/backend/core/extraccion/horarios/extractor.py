from __future__ import annotations
import re
import os
import camelot
from PyPDF2 import PdfReader
import time
from typing import Any, Dict, List, Optional
import logging
import warnings as _w

from .constants import (
    DEFAULT_EXTRACTOR_CONFIG, TITULACION_PATTERNS, DAYS_CANONICAL, DAY_ALIASES,
    TIME_WINDOW, CONFIDENCE_ERR_MAX, CONFIDENCE_ERR_STEP,
    CONFIDENCE_SEVERE_MAX, CONFIDENCE_SEVERE_STEP,
    CONFIDENCE_MODERATE_MAX, CONFIDENCE_MODERATE_STEP,
    CONFIDENCE_MINOR_MAX, CONFIDENCE_MINOR_STEP,
    CONFIDENCE_CELL_COVERAGE, CONFIDENCE_PAGE_COVERAGE,
    CONFIDENCE_NO_TEXT_PENALTY, BLACKLIST_TOKENS, TIME_LIKE_REGEX,
    QUALITY_UNUSABLE_CELL_COVERAGE, QUALITY_UNUSABLE_PAGE_RATIO,
    QUALITY_POOR_PAGE_RATIO, QUALITY_POOR_CELL_COVERAGE, QUALITY_POOR_SEVERE_PER_PAGE,
    QUALITY_ACCEPTABLE_PAGE_RATIO, QUALITY_ACCEPTABLE_CELL_COVERAGE, QUALITY_ACCEPTABLE_SEVERE_PER_PAGE,
    QUALITY_GOOD_PAGE_RATIO, QUALITY_GOOD_CELL_COVERAGE, QUALITY_GOOD_CONFIDENCE,
    QUALITY_EXCELLENT_PAGE_RATIO, QUALITY_EXCELLENT_CELL_COVERAGE, QUALITY_EXCELLENT_CONFIDENCE,
)

from .entities import (
    CleanTable, ExtractionResult, RawTable, Warning
) 

from core.extraccion.common.entities import (
    ExtractionMetadata, ExtractionQuality, ProcessingStatus 
)

class ScheduleExtractor:
    """
    Flujo del extractor:
      - Fase 1: contar páginas y detectar 'titulacion'
      - Fase 2: extraer tablas por página (lattice → stream fallback)
      - Fase 3: normalizar y construir RawTable
      - Fase 4: detectar cabecera de días + construir time_axis
      - Fase 5: alinear a CleanTable (cells con forma [T x 5])
      - Fase 6: chequear calidad + metadatos
      - Fase 7: ensamblar ExtractionResult
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Inicializa el extractor mapeando únicamente los parámetros de configuración
        a atributos de instancia. No realiza validaciones ni lógica pesada.

        Parámetros esperados en DEFAULT_EXTRACTOR_CONFIG / config:
          - prefer_lattice: bool
          - lattice_opts: dict
          - stream_opts: dict
          - table_areas_by_page: dict[int, list[str]]
          - columns_by_page: dict[int, list[str]]
          - max_header_scan_rows: int
          - window_strict: bool

        Las constantes de dominio (TIME_WINDOW, DAYS_CANONICAL, etc.) se importarán
        cuando sean necesarias dentro de los métodos del extractor, no aquí.
        """
        cfg = DEFAULT_EXTRACTOR_CONFIG.copy()
        if config:
            cfg.update(config)

        # Mapear 1:1 a atributos de instancia
        self.prefer_lattice = cfg.get("prefer_lattice", True)
        self.lattice_opts = cfg.get("lattice_opts", {})
        self.stream_opts = cfg.get("stream_opts", {})
        self.table_areas_by_page = cfg.get("table_areas_by_page", {})
        self.columns_by_page = cfg.get("columns_by_page", {})
        self.max_header_scan_rows = cfg.get("max_header_scan_rows", 5)
        self.window_strict = cfg.get("window_strict", True)

        self.config = cfg
        self.name = self.__class__.__name__



    # ------------------------- API pública -------------------------

    def extract(self, pdf_path: str) -> ExtractionResult:
        """
        Ejecuta el flujo completo y devuelve un ExtractionResult con:
          - titulacion: str
          - raw_tables: List[RawTable]
          - clean_tables: List[CleanTable]
          - extraccion_metadata: ExtractionReport (o dict equivalente)
        """
        _w.filterwarnings("ignore", category=UserWarning, module="camelot.utils")
        
        # Inicializacion de contenedores y metadatos
        start_time = time.time()
        titulacion = ""
        raw_tables: List[RawTable] = []
        clean_tables: List[CleanTable] = []
        warnings: List[Warning] = []
        errors: List[str] = []
        page_count = 0

        try:
            # Fase 1: Contar páginas y detectar titulacion
            page_count = self._count_pages(pdf_path)
            titulacion = self._read_titulacion(pdf_path)
            pdf_metrics = self._compute_pdf_metrics(pdf_path)

            # Fase 2–6: procesar página a página
            for page_no in range(1, page_count + 1):
                try:
                    # 2) Camelot: lattice → stream (fallback)
                    tables = self._run_camelot(
                        pdf_path, page_no,
                        "lattice" if self.prefer_lattice else "stream"
                    )
                    if not tables and self.prefer_lattice:
                        tables = self._run_camelot(pdf_path, page_no, "stream")

                    if not tables:
                        warnings.append(Warning(f"No se detectó tabla válida en la página {page_no}", "severe"))
                        continue

                    # Volcar SIEMPRE todas las tablas crudas a raw_tables
                    for t in tables:
                        raw_tables.append(RawTable(page=page_no, grid=self._to_raw_grid(t)))

                    best_table = self._choose_best_table(tables)
                    if not best_table:
                        warnings.append(Warning(f"No se pudo seleccionar tabla principal en la página {page_no}", "severe"))
                        continue

                    # 3) Normalizar y construir RawTable
                    grid = self._to_raw_grid(best_table)

                    # 4) Detectar cabecera + time axis
                    header_row_idx = self._detect_header_row(grid)
                    if header_row_idx is None:
                        warnings.append(Warning(f"No se detectó cabecera de días en la página {page_no}", "severe"))
                        continue

                    header_row = grid[header_row_idx]
                    header_days = self._build_header_days(header_row)

                    # acceso seguro a la primera columna (horas)
                    time_col = [(row[0] if (row and len(row) > 0) else "")
                                for row in grid[header_row_idx + 1:]]
                    time_axis = self._build_time_axis(time_col)
                    if not time_axis:
                        warnings.append(Warning(f"Eje temporal vacío o fuera de ventana en la página {page_no}", "severe"))
                        continue

                    # 5) Alinear a CleanTable [T x 5]
                    day_col_indices = self._find_day_columns(header_row)
                    if len(day_col_indices) < 3:
                        warnings.append(Warning(f"Cabecera de días insuficiente (cols={len(day_col_indices)}) en la página {page_no}", "severe"))
                        continue

                    cells = self._align_cells(grid, header_row_idx, day_col_indices, time_axis)

                    # 6) Chequeos de forma
                    table_warnings = self._validate_clean_table(header_days, time_axis, cells)
                    warnings.extend(table_warnings)

                    clean_tables.append(
                        CleanTable(
                            page=page_no,
                            header_days=header_days,
                            time_axis=time_axis,
                            cells=cells
                        )
                    )

                except Exception as e:
                    # Error aislado de página: seguir con la siguiente
                    errors.append(f"page_{page_no}: {e!r}")
                    continue

                del tables  # liberar memoria

            # Fase 7: Chequear calidad global + metadatos
            quality, confidence, status = self._compute_quality_and_confidence(
                errors, warnings, clean_tables, page_count, pdf_metrics
            )

            # Fase 8: Ensamblar resultado + metadatos
            processing_time = time.time() - start_time
            metadata = ExtractionMetadata(
                quality=quality,
                confidence=confidence,
                status=status,
                processing_time_seconds=processing_time,
                page_count=page_count,
                file_size_mb=pdf_metrics.get("file_size_mb"),
                has_embedded_text=pdf_metrics.get("has_embedded_text"),
                char_count=pdf_metrics.get("char_count"),
                word_count=pdf_metrics.get("word_count"),
                pages_with_text=pdf_metrics.get("pages_with_text") or None,
                errors=errors,
                warnings=warnings,
            )
            return ExtractionResult(
                titulacion=titulacion,
                raw_tables=raw_tables,
                clean_tables=clean_tables,
                extraccion_metadata=metadata
            )

        except Exception as e:
            # Error global no recuperable: devolvemos lo acumulado
            processing_time = time.time() - start_time
            errors.append(str(e))
            # Intenta obtener métricas básicas si es posible
            try:
                pdf_metrics = self._compute_pdf_metrics(pdf_path)
            except Exception:
                pdf_metrics = {
                    "file_size_mb": None,
                    "has_embedded_text": None,
                    "char_count": None,
                    "word_count": None,
                    "pages_with_text": None,
                }
            metadata = ExtractionMetadata(
                quality=ExtractionQuality.UNUSABLE,
                confidence=0.0,
                status=ProcessingStatus.FAILED,
                processing_time_seconds=processing_time,
                page_count=page_count,
                file_size_mb=pdf_metrics.get("file_size_mb"),
                has_embedded_text=pdf_metrics.get("has_embedded_text"),
                char_count=pdf_metrics.get("char_count"),
                word_count=pdf_metrics.get("word_count"),
                pages_with_text=pdf_metrics.get("pages_with_text"),
                errors=errors,
                warnings=warnings,
            )
            return ExtractionResult(
                titulacion=titulacion,
                raw_tables=raw_tables,
                clean_tables=clean_tables,
                extraccion_metadata=metadata
            )

    # ------------------------- Etapas internas (por implementar) -------------------------

    # Fase 1
    def _count_pages(self, pdf_path: str) -> int:
        """
        Devuelve el número de páginas del PDF.
        """
        reader = PdfReader(pdf_path)  # puede lanzar si el archivo está corrupto/inaccesible
        if getattr(reader, "is_encrypted", False):
            raise ValueError(f"El PDF está encriptado y no puede procesarse: {pdf_path}")

        return len(reader.pages)

    def _read_titulacion(self, pdf_path: str) -> str:
        """
        Intenta extraer una cadena identificativa de la titulación.
        """
        reader = PdfReader(pdf_path)
        # Si está encriptado, reportamos error
        if getattr(reader, "is_encrypted", False):
            raise ValueError(f"El PDF está encriptado y no puede procesarse: {pdf_path}")

        max_pages = min(2, len(reader.pages))
        time_like = re.compile(TIME_LIKE_REGEX)
        days_upper = set(d.upper() for d in DAYS_CANONICAL)

        # 1) Patrones directos
        for i in range(max_pages):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                continue

            text_flat = " ".join(text.split())
            for rx in TITULACION_PATTERNS:
                m = rx.search(text) or rx.search(text_flat)
                if m:
                    val = m.group(1) if m.lastindex else m.group(0)
                    return val.strip(" :-\t")

        # 2) Fallback: línea “mayúscula e informativa” más larga
        candidatas = []
        for i in range(max_pages):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                continue

            # líneas originales + una versión aplanada para capturar títulos partidos por saltos
            lines = [ln for ln in (text.replace("\r", "\n").split("\n")) if ln.strip()]
            lines.append(" ".join(text.split()))

            for ln in lines:
                u = " ".join(ln.split()).upper()
                if len(u) < 12:
                    continue
                if any(tok in u for tok in BLACKLIST_TOKENS):
                    continue
                if u in days_upper or any(dw in u for dw in days_upper):
                    continue
                if time_like.search(u):
                    continue
                if ("GRADO" in u) or ("DOBLE" in u) or ("MÁSTER" in u) or ("MASTER" in u):
                    candidatas.append(u)

        if candidatas:
            # Escoge la más larga; devuélvela “title-cased” como salida legible
            return max(candidatas, key=len).title()

        return ""

    def _compute_pdf_metrics(self, pdf_path: str) -> dict:
        """
        Calcula métricas básicas del PDF:
        - file_size_mb
        - has_embedded_text
        - char_count
        - word_count
        - pages_with_text
        """
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        char_count = 0
        word_count = 0
        pages_with_text = 0
        has_embedded_text = False
    
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text.strip():
                    pages_with_text += 1
                    char_count += len(text)
                    word_count += len(text.split())
                    has_embedded_text = True  # Basta con que una página tenga texto
        return {
            "file_size_mb": file_size_mb,
            "has_embedded_text": has_embedded_text,
            "char_count": char_count,
            "word_count": word_count,
            "pages_with_text": pages_with_text,
        }
    

    # Fase 2
    def _run_camelot(self, pdf_path: str, page_no: int, flavor: str):
        """
        Ejecuta camelot.read_pdf en una página concreta con el flavor indicado.
        - flavor: "lattice" | "stream"
        - Usa opciones de self.lattice_opts / self.stream_opts sin mutarlas.
        - Inyecta pages=str(page_no) y, si existen, table_areas (ambos sabores) y columns (solo stream).
        - Devuelve TableList o [] si no hay tablas o si ocurre un error.
        """
        # Validaciones ligeras
        if flavor not in ("lattice", "stream"):
            # Mantenemos el contrato de devolver [] (no lanzar) para integrarse con extract()
            return []
        if not isinstance(page_no, int) or page_no < 1:
            return []

        # Copiamos opts base y limpiamos posibles claves conflictivas
        base_opts = self.lattice_opts if flavor == "lattice" else self.stream_opts
        opts = dict(base_opts or {})
        # Forzamos flavor y pages (por si venían en opts)
        opts.pop("flavor", None)
        opts.pop("pages", None)
        opts["flavor"] = flavor
        opts["pages"] = str(page_no)

        # Geometría por página
        table_areas = self.table_areas_by_page.get(page_no)
        if table_areas:
            opts["table_areas"] = table_areas

        # Columns solo tiene sentido en stream
        if flavor == "stream":
            columns = self.columns_by_page.get(page_no)
            if columns:
                opts["columns"] = columns
        else:
            # Por higiene, aseguramos no pasar columns en lattice
            opts.pop("columns", None)

        # Llamada a Camelot
        try:
            tables = camelot.read_pdf(pdf_path, **opts)
            # TableList puede ser truthy/falsy; devolvemos [] si está vacío o None
            return tables if tables and len(tables) > 0 else []
        except Exception:
            # No log aquí por mantenerlo minimalista; el caller ya añade errores/alerts por página
            return []

    def _choose_best_table(self, tables) -> Optional[Any]: # TODO: Mirar si se pueden declarar algunas constantes
        """
        Selecciona la mejor tabla de Camelot:
        1) Filtra tablas viables: tienen .df, ≥6 columnas (hora+5 días) y ≥3 filas.
        2) Puntuación: más 'day hits' en la primera fila (≥3 deseable), luego más columnas y más filas.
        3) Devuelve la candidata con mayor puntuación o None si no hay viables.
        """
        if not tables or len(tables) == 0:
            return None
        
        canon_days = {d.upper() for d in DAYS_CANONICAL}
        alias_map = {k.upper(): v.upper() for k, v in DAY_ALIASES.items()}

        def _norm(s):
            return " ".join(str(s or "").replace("\r", "\n").replace("\r\n", "\n").split()).upper()

        def _day_hits(df):
            if getattr(df, "shape", None) is None or df.shape[0] == 0:
                return 0
            header = [_norm(x) for x in list(df.iloc[0, :])]
            hits = set()
            for cell in header:
                for alias, canon in alias_map.items():
                    if alias in cell:
                        hits.add(canon)
            return len(hits & canon_days)

        candidates = []
        for t in tables:
            df = getattr(t, "df", None)
            if df is None or getattr(df, "shape", None) is None:
                continue
            rows, cols = df.shape
            # Viabilidad mínima: Hora + 5 días ⇒ 6 columnas, y al menos 3 filas útiles
            if cols < 6 or rows < 3:
                continue
            hits = _day_hits(df)
            area = rows * cols
            score = (hits, area)
            candidates.append((score, t))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]


    # Fase 3
    def _to_raw_grid(self, table) -> List[List[str]]:
        """
        Convierte una tabla Camelot a grid[str] con limpieza mínima:
        - None/NaN -> ""
        - \r/\r\n/\n -> " " (espacio)
        - colapsa espacios y hace strip
        No interpreta contenido ni elimina filas/columnas.
        """
        df = getattr(table, "df", None)
        if df is None:
            return []

        # Si por alguna razón df no expone shape, devolvemos vacío
        try:
            rows, cols = df.shape
        except Exception:
            return []

        def _norm_cell(val) -> str:
            s = "" if val is None else str(val)
            # Unificar saltos y colapsar espacios
            s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
            s = " ".join(s.split()).strip()
            return s

        grid: list[list[str]] = [
            [_norm_cell(df.iat[r, c]) for c in range(cols)]
            for r in range(rows)
        ]
        return grid


    # Fase 4
    def _detect_header_row(self, grid: list[list[str]]) -> int | None:
        """
        Localiza el índice de la fila de cabecera de días.
        Regla: en las primeras `self.max_header_scan_rows` filas,
        la primera que contenga ≥3 nombres de día (contando alias) es la cabecera.
        Si no se alcanza el umbral, devuelve el índice con más hits (>0), o None si no hay ninguno.
        """
        if not grid:
            return None

        def _norm(s: str) -> str:
            # aplana saltos y mayúsculas para facilitar el match por substring
            return " ".join(str(s or "").replace("\r", "\n").replace("\r\n", "\n").split()).upper()

        alias_map = {k.upper(): v.upper() for k, v in DAY_ALIASES.items()}
        days_set = set(d.upper() for d in DAYS_CANONICAL)

        scan_rows = min(self.max_header_scan_rows, len(grid))
        best_idx = None
        best_hits = 0

        for i in range(scan_rows):
            row = grid[i]
            if not row:
                continue

            cells = [_norm(c) for c in row]

            hits = set()
            for cell in cells:
                for alias, canon in alias_map.items():
                    if alias in cell:
                        hits.add(canon)

            hit_count = len(hits & days_set)
            if hit_count > best_hits:
                best_hits = hit_count
                best_idx = i

            # Umbral de aceptación
            if hit_count >= 3:
                return i

        # Si no se alcanzó el umbral, devolvemos el mejor (si hay alguno)
        return best_idx if best_hits > 0 else None

    def _build_header_days(self, header_row: list[str]) -> list[str]:
        """
        Devuelve la lista canónica de días en orden L→V para la CleanTable.
        Nota: el mapeo de columnas reales se resuelve en _find_day_columns().
        Aquí no dependemos del contenido de 'header_row' para el orden/forma del resultado.

        Si mañana quisieras validar cuántos días aparecen realmente en la fila,
        puedes usar el bloque de 'hits' que dejo preparado.
        """
        # --- (opcional) detección ligera de días presentes en la fila ---
        # Esto no afecta al retorno; queda listo por si quieres emitir warnings después.
        alias_map = {k.upper(): v.upper() for k, v in DAY_ALIASES.items()}
        days_set = set(d.upper() for d in DAYS_CANONICAL)

        def _norm(s: str) -> str:
            return " ".join(str(s or "").replace("\r\n", "\n").replace("\r", "\n").split()).upper()

        try:
            cells = [_norm(c) for c in (header_row or [])]
            hits = set()
            for cell in cells:
                for alias, canon in alias_map.items():
                    if alias in cell:
                        hits.add(canon)
            _present_days = hits & days_set  # <- usable para warnings si lo necesitas
            # (no lo usamos aquí; el validador de tabla puede revisar esta info si quieres)
        except Exception as e:
            logging.warning(f"Error analizando días en la cabecera: {e!r}")

        # Retorno estable en orden canónico para la CleanTable
        return list(DAYS_CANONICAL)

    def _build_time_axis(self, time_col_cells: list[str]) -> list[str]: # TODO: Añadir patrones en las celdas
        """
        Construye la lista de marcas HH:MM a partir de la primera columna bajo la cabecera.
        - Extrae como máximo UNA hora por fila (la primera que encuentre).
        - Si self.window_strict es True, filtra a la ventana TIME_WINDOW.
        - Preserva el orden de aparición (no ordena ni de-duplica).
        - Omite filas sin marca válida.
        """
        # hh:mm / h:mm / hh.mm / hh h mm
        rx_hhmm = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:h\.]([0-5]\d)(?!\d)")
        # 800 / 0830 / 930 (3-4 dígitos)
        rx_compact = re.compile(r"\b([01]?\d|2[0-3])([0-5]\d)\b")

        def _canon_hhmm(h: int, m: int) -> str:
            return f"{h:02d}:{m:02d}"

        def _all_times(text: str) -> list[str]:
            s = " ".join((text or "").replace("\r\n","\n").replace("\r","\n").split())
            out = [ _canon_hhmm(int(h), int(m)) for h,m in rx_hhmm.findall(s) ]
            out += [ _canon_hhmm(int(h), int(m)) for h,m in rx_compact.findall(s) ]
            return out

        lo, hi = TIME_WINDOW
        raw = []
        for cell in time_col_cells:
            for t in _all_times(cell):
                if lo <= t <= hi:
                    raw.append(t)

        if not raw:
            return []

        # minuto dominante (00 vs 30) por mayoría
        mins = [int(t[-2:]) for t in raw]
        dom_min = 30 if mins.count(30) >= mins.count(0) else 0
        filtered = [t for t in raw if int(t[-2:]) == dom_min]

        # deduplicar preservando orden + monotonía suave
        seen, axis = set(), []
        last = None
        for t in filtered:
            if t in seen:
                continue
            if last and t < last:
                # si hay regresión por ruido, la saltamos
                continue
            axis.append(t); seen.add(t); last = t

        return axis


    # Fase 5
    def _find_day_columns(self, header_row: List[str]) -> List[int]:
        """
        Devuelve los índices de columna asociados a [LUNES..VIERNES], en ese orden.
        - Busca por alias en la fila de cabecera.
        - Si falta algún día, completa con columnas libres de izquierda a derecha (saltando col 0).
        - Puede devolver <5 si la fila es demasiado corta.
        """
        if not header_row:
            return []

        def _norm(s: str) -> str:
            return " ".join(str(s or "").replace("\r\n","\n").replace("\r","\n").split()).upper()

        alias_map = {k.upper(): v.upper() for k,v in DAY_ALIASES.items()}
        canon_days = [d.upper() for d in DAYS_CANONICAL]

        # 1) recolectar días por columna (permitiendo múltiples en una misma celda)
        col_days: dict[int, list[str]] = {}
        for j, raw in enumerate(header_row):
            txt = _norm(raw)
            hits = []
            for alias, canon in alias_map.items():
                if alias in txt and canon not in hits:
                    hits.append(canon)
            if hits:
                col_days[j] = hits

        # 2) asignación primaria: primer día de cada columna
        assigned: dict[str, int] = {}
        used_cols = set()
        for j in sorted(col_days.keys()):
            if col_days[j]:
                d = col_days[j][0]
                if d not in assigned:
                    assigned[d] = j
                    used_cols.add(j)

        # 3) columnas libres (saltando 0 por ser HORA)
        free_cols = [j for j in range(1, len(header_row)) if j not in used_cols]

        # 4) reasignar colisiones: días adicionales de la misma columna → siguiente libre
        for j in sorted(col_days.keys()):
            extras = col_days[j][1:]  # días extra en esta celda
            for d in extras:
                if d not in assigned and free_cols:
                    assigned[d] = free_cols.pop(0)

        # 5) construir índices en orden canónico; completar con libres si falta algo
        indices: List[int] = []
        for d in canon_days:
            if d in assigned:
                indices.append(assigned[d])
            elif free_cols:
                indices.append(free_cols.pop(0))

        return indices

    def _align_cells(
        self,
        grid: list[list[str]],
        header_row_idx: int,
        day_col_indices: list[int],
        time_axis: list[str],
    ) -> list[list[str]]:
        """
        Construye la matriz 'cells' [len(time_axis) × 5] a partir del grid:
        - Recorre las filas desde header_row_idx+1 y empareja en orden con cada marca de time_axis.
        - Para cada marca, toma los textos de las columnas de días indicadas.
        - Si faltan filas para completar time_axis, rellena con "".
        """
        # Helper para extraer HH:MM de la columna 0 (misma lógica que _build_time_axis)
        rx_hhmm = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:h\.]([0-5]\d)(?!\d)")
        rx_compact = re.compile(r"\b([01]?\d|2[0-3])([0-5]\d)\b")

        def _parse_first(text: str) -> str | None:
            s = " ".join((text or "").replace("\r\n", "\n").replace("\r", "\n").split())
            m = rx_hhmm.search(s)
            if m:
                return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
            m2 = rx_compact.search(s)
            if m2:
                return f"{int(m2.group(1)):02d}:{int(m2.group(2)):02d}"
            return None

        out: list[list[str]] = []
        r = header_row_idx + 1
        t_idx = 0

        while t_idx < len(time_axis):
            # avanzar hasta encontrar una fila cuya col 0 tenga la marca esperada
            found = False
            while r < len(grid):
                row = grid[r]
                col0 = row[0] if (row and len(row) > 0) else ""
                hhmm = _parse_first(col0)
                if hhmm == time_axis[t_idx]:
                    # construir la fila de cells para los 5 días
                    row_cells: list[str] = []
                    for c_idx in day_col_indices[:5]:
                        val = row[c_idx] if (c_idx < len(row)) else ""
                        row_cells.append(val)
                    out.append(row_cells)
                    r += 1
                    t_idx += 1
                    found = True
                    break
                else:
                    r += 1
            if not found:
                # no encontramos fila para esta marca; rellenamos vacío y pasamos a la siguiente
                out.append([""] * min(5, len(day_col_indices)))
                t_idx += 1

        # Si por alguna razón se devolvieron menos de 5 columnas, normalizamos a 5 con vacío
        for i in range(len(out)):
            if len(out[i]) < 5:
                out[i] = out[i] + [""] * (5 - len(out[i]))

        return out


    # Fase 6
    def _validate_clean_table(
        self,
        header_days: list[str],
        time_axis: list[str],
        cells: list[list[str]],
    ) -> list[str]:
        """
        Chequeos de forma y consistencia. Devuelve lista de warnings (no lanza).
        - header_days debe tener 5 elementos.
        - time_axis no vacío y con formato HH:MM; si window_strict, dentro de TIME_WINDOW.
        - cells debe ser rectangular [len(time_axis) × 5].
        """
        warnings: list[Warning] = []

        # 1) header_days
        if not isinstance(header_days, list) or len(header_days) != 5:
            warnings.append(Warning(
                f"header_days_expected_5_got_{len(header_days) if isinstance(header_days, list) else 'invalid'}",
                "severe"
            ))


        # 2) time_axis
        rx = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")
        if not isinstance(time_axis, list) or len(time_axis) == 0:
            warnings.append(Warning("time_axis_empty", "severe"))
        else:
            for t in time_axis:
                if not isinstance(t, str) or not rx.match(t):
                    warnings.append(Warning(f"time_axis_bad_token:{t!r}", "minor"))
                    continue
                if self.window_strict:
                    lo, hi = TIME_WINDOW
                    if not (lo <= t <= hi):
                        warnings.append(Warning(f"time_axis_out_of_window:{t}", "moderate"))

        # 3) cells shape
        expected_rows = len(time_axis) if isinstance(time_axis, list) else 0
        if not isinstance(cells, list) or len(cells) != expected_rows:
            warnings.append(Warning(
                f"cells_row_mismatch_expected_{expected_rows}_got_{len(cells) if isinstance(cells, list) else 'invalid'}",
                "severe"
            ))
        else:
            for i, row in enumerate(cells):
                if not isinstance(row, list) or len(row) != 5:
                    warnings.append(Warning(
                        f"cells_col_mismatch_row_{i}_expected_5_got_{len(row) if isinstance(row, list) else 'invalid'}",
                        "severe"
                    ))

        return warnings


    # Fase 7
    def _compute_quality_and_confidence(self, errors: list[str], warnings: list[Warning],
                                        clean_tables: list, page_count: int, pdf_metrics: dict
                                        ) -> tuple[ExtractionQuality, float, ProcessingStatus]:
        """
        Calcula quality, confidence y status para ExtractionMetadata.
        """
        # Clasificación de avisos
        severe = [w for w in warnings if w.severity == "severe"]
        moderate = [w for w in warnings if w.severity == "moderate"]
        minor = [w for w in warnings if w.severity == "minor"]

        # Cobertura
        pages_with_clean = len({t.page for t in clean_tables}) if clean_tables else 0
        pages_with_clean_ratio = pages_with_clean / page_count if page_count else 0

        total_cells = sum(len(t.time_axis) * 5 for t in clean_tables)
        filled_cells = sum(sum(1 for cell in row if cell.strip()) for t in clean_tables for row in t.cells)
        cell_coverage = filled_cells / total_cells if total_cells else 0

        # Penalizaciones
        err_count = len(errors)
        severe_count = len(severe)
        moderate_count = len(moderate)
        minor_count = len(minor)

        confidence = 1.0
        confidence -= min(CONFIDENCE_ERR_MAX, CONFIDENCE_ERR_STEP * min(2, err_count))
        confidence -= min(CONFIDENCE_SEVERE_MAX, CONFIDENCE_SEVERE_STEP * severe_count)
        confidence -= min(CONFIDENCE_MODERATE_MAX, CONFIDENCE_MODERATE_STEP * moderate_count)
        confidence -= min(CONFIDENCE_MINOR_MAX, CONFIDENCE_MINOR_STEP * minor_count)
        confidence -= CONFIDENCE_CELL_COVERAGE * (1 - cell_coverage)
        confidence -= CONFIDENCE_PAGE_COVERAGE * (1 - pages_with_clean_ratio)
        if not pdf_metrics.get("has_embedded_text", True):
            confidence -= CONFIDENCE_NO_TEXT_PENALTY
        confidence = max(0.0, min(1.0, confidence))

        # Calidad
        quality = ExtractionQuality.UNUSABLE
        if (
            not clean_tables
            or cell_coverage < QUALITY_UNUSABLE_CELL_COVERAGE
            or (err_count > 0 and pages_with_clean_ratio < QUALITY_UNUSABLE_PAGE_RATIO)
        ):
            quality = ExtractionQuality.UNUSABLE
        elif (
            pages_with_clean_ratio >= QUALITY_EXCELLENT_PAGE_RATIO
            and cell_coverage >= QUALITY_EXCELLENT_CELL_COVERAGE
            and err_count == 0
            and severe_count == 0
            and confidence >= QUALITY_EXCELLENT_CONFIDENCE
        ):
            quality = ExtractionQuality.EXCELLENT
        elif (
            pages_with_clean_ratio >= QUALITY_GOOD_PAGE_RATIO
            and cell_coverage >= QUALITY_GOOD_CELL_COVERAGE
            and err_count == 0
            and severe_count <= 1
            and confidence >= QUALITY_GOOD_CONFIDENCE
        ):
            quality = ExtractionQuality.GOOD
        elif (
            pages_with_clean_ratio >= QUALITY_ACCEPTABLE_PAGE_RATIO
            and cell_coverage >= QUALITY_ACCEPTABLE_CELL_COVERAGE
            and severe_count <= QUALITY_ACCEPTABLE_SEVERE_PER_PAGE * page_count
        ):
            quality = ExtractionQuality.ACCEPTABLE
        elif (
            pages_with_clean_ratio < QUALITY_POOR_PAGE_RATIO
            or cell_coverage < QUALITY_POOR_CELL_COVERAGE
            or severe_count >= QUALITY_POOR_SEVERE_PER_PAGE * page_count
        ):
            quality = ExtractionQuality.POOR
        elif (
            pages_with_clean_ratio < QUALITY_POOR_PAGE_RATIO
            or cell_coverage < QUALITY_POOR_CELL_COVERAGE
            or severe_count >= QUALITY_POOR_SEVERE_PER_PAGE * page_count
        ):
            quality = ExtractionQuality.POOR
        else:
            # Fallback coherente: si hay tablas limpias pero no llegas a ACCEPTABLE,
            # clasifica por confianza: >=0.60 → ACCEPTABLE; si no, POOR.
            quality = ExtractionQuality.ACCEPTABLE if confidence >= 0.60 else ExtractionQuality.POOR

        # Estado
        if quality in (ExtractionQuality.EXCELLENT, ExtractionQuality.GOOD, ExtractionQuality.ACCEPTABLE):
            status = ProcessingStatus.COMPLETED
        elif quality == ExtractionQuality.POOR:
            status = ProcessingStatus.LOW_QUALITY
        else:
            status = ProcessingStatus.FAILED

        return quality, confidence, status  


# INSTANCIA PARA USO GENERAL
extractor = None

def get_schedule_extractor(config: dict = None) -> ScheduleExtractor:
    """
    Devuelve una instancia singleton de ScheduleExtractor.
    Si se llama con config, se crea una nueva instancia con esa configuración.
    """
    global extractor
    if extractor is None or config is not None:
        extractor = ScheduleExtractor(config)
    return extractor