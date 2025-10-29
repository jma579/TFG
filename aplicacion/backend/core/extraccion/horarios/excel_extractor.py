import openpyxl
import logging
import time
import unicodedata
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.extraccion.horarios.entities import RawTable, CleanTable, ExtractionResult
from core.extraccion.common.entities import ExtractionMetadata

from core.extraccion.horarios.constants import (
    DEFAULT_EXCEL_EXTRACTOR_CONFIG, DAY_ALIASES, DAYS_CANONICAL
)

class ExcelScheduleExtractor:
    def __init__(self, config: Optional[Dict[str, Any]]):

        # 1. Configurar logging con nivel personalizable
        self.logger = logging.getLogger(__name__)

        # 2. Aplicar configuración personalizada
        self.config = DEFAULT_EXCEL_EXTRACTOR_CONFIG.copy()
        if config:
            self.config.update(config)

        # 3. Configurar nivel de logging si se especifica
        if 'log_level' in self.config:
            self.logger.setLevel(getattr(logging, self.config['log_level'].upper(), logging.INFO))
        
        # 4. Inicializar estadísticas
        self.stats = {
            # === Contadores de extracción ===
            'extractions_total': 0,           # Total de archivos procesados
            'extractions_success': 0,         # Extracciones exitosas
            'extractions_failed': 0,          # Extracciones fallidas
            
            # === Contadores de bloques ===
            'blocks_detected': 0,             # Total de bloques detectados
            'blocks_extracted': 0,            # Bloques extraídos con éxito
            'blocks_rejected': 0,             # Bloques rechazados por calidad
            
            # === Contadores de hojas ===
            'sheets_processed': 0,            # Total de hojas procesadas
            'sheets_with_schedules': 0,       # Hojas que contenían horarios
            'sheets_empty': 0,                # Hojas vacías o sin horarios
            
            # === Métricas de calidad ===
            'avg_quality_score': 0.0,         # Score promedio de calidad
            'avg_cell_coverage': 0.0,         # Cobertura promedio de celdas útiles
            'avg_blocks_per_file': 0.0,       # Promedio de bloques por archivo
            
            # === Métricas de tiempo ===
            'avg_processing_time': 0.0,       # Tiempo promedio de procesamiento
            'total_processing_time': 0.0,     # Tiempo total acumulado
            
            # === Detección de estructura ===
            'merged_cells_detected': 0,       # Total de celdas combinadas detectadas
            'sessions_with_spans': 0,         # Sesiones con duración > 60 min
            
            # === Errores y advertencias ===
            'warnings_total': 0,              # Total de advertencias generadas
            'errors_total': 0,                # Total de errores capturados
        }
        
        self.logger.info("ExcelScheduleExtractor inicializado correctamente")


    def extract(self, path: str) -> ExtractionResult:
        """
        Orquesta el proceso completo de extracción.
        """
        start_time = time.time()
        self.stats['extractions_total'] += 1

        try:
            # 1. Validaciones de entrada
            self._validate_input(path)
            self.logger.info(f"Iniciando extracción de: {path}")

            # 2. Cargar workbook y buscar bloques
            self._load_workbook(path)
            blocks = self._find_blocks()
            if not blocks:
                self.stats['extractions_failed'] += 1
                raise ValueError(
                    "No se encontraron bloques de horarios válidos en el Excel. "
                    "Verifique que el archivo contenga tablas con días de la semana y horas."
                )
            self.logger.debug(f"Detectados {len(blocks)} bloques de horarios")
            
            # 3. Extraer tablas por cada bloque
            raw_tables = []
            clean_tables = []
            for i, block in enumerate(blocks):
                try:
                    raw_tables.append(self._extract_raw_table(block))
                    clean_tables.append(self._extract_clean_table(block))
                    self.stats['blocks_extracted'] += 1
                except Exception as e:
                    self.logger.warning(f"Error extrayendo bloque {i+1}: {e}")
                    self.stats['blocks_rejected'] += 1
                    continue
            if not clean_tables:
                self.stats['extractions_failed'] += 1
                raise ValueError(
                    "Todos los bloques detectados fueron rechazados por baja calidad. "
                    "Verifique la estructura de las tablas en el Excel."
                )
            
            # 4. Evaluar calidad global
            quality_score, cell_coverage = self._evaluate_extraction_quality(clean_tables)
            quality, confidence = self._map_quality_to_enum(quality_score, cell_coverage)
            
            # 5. Verificar umbral mínimo
            if quality == ExtractionQuality.UNUSABLE:
                self.stats['extractions_failed'] += 1
                raise ValueError(
                    "Excel no contiene estructura de horarios con calidad suficiente. "
                    f"Score de calidad: {quality_score:.2f}, Cobertura: {cell_coverage:.2f}. "
                    "Se requiere al menos POOR para continuar."
                )
            
            # 6. Construcción de metadatos
            processing_time = time.time() - start_time
            
            metadata = self._build_success_metadata(
                quality, confidence, clean_tables, processing_time, path
            )
            
            # 7. Actualizar estadísticas de éxito
            self.stats['extractions_success'] += 1
            self._update_stats_success(processing_time, len(blocks), quality_score, cell_coverage)
            
            # 8. Log y retorno
            self.logger.info(
                f"Extracción Excel completada: {quality.value}, "
                f"{confidence:.2f} confianza, {len(clean_tables)} tablas extraídas"
            )
            
            return ExtractionResult(
                raw_tables=raw_tables,
                clean_tables=clean_tables,
                extraccion_metadata=metadata
            )
        except Exception as e:
            return self._handle_extraction_error(e, path, start_time)


    def _validate_input(self, path: str):
        """
        Validar archivo Excel de entrada.
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si no es un Excel válido
        """
        file = Path(path)

        # 1. Verificar que el archivo existe
        if not file.exists():
            raise FileNotFoundError(f"Excel no encontrado: {path}")
        
        # 2. Validar extensión
        valid_extensions = {'.xlsx', '.xlsm'}
        if file.suffix.lower() not in valid_extensions:
            raise ValueError(
                f"Extensión no válida: {file.suffix}. "
                f"Se requiere Excel moderno: {', '.join(valid_extensions)}"
            )
        
        # 3. Validar que es un Excel válido (magic bytes)
        try:
            with open(path, 'rb') as f:
                header = f.read(4)
                # Excel (.xlsx, .xlsm) son archivos ZIP (magic bytes: 50 4B 03 04)
                if not header.startswith(b'PK\x03\x04'):
                    raise ValueError(
                        "El archivo no tiene formato Excel válido. "
                        "Los archivos .xlsx/.xlsm son contenedores ZIP."
                    )
        except IOError as e:
            raise ValueError(f"Error al leer archivo Excel: {e}")

        # 4. Validar que se puede abrir con openpyxl (test rápido)
        try:
            # Intentar abrir sin cargar datos (solo estructura)
            wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
            
            # Verificar que tiene al menos una hoja
            if len(wb.sheetnames) == 0:
                raise ValueError("El Excel no contiene hojas de cálculo")
            
            wb.close()
            
        except openpyxl.utils.exceptions.InvalidFileException:
            raise ValueError(
                "El archivo está corrupto o no es un Excel válido. "
                "Verifique que se puede abrir con Excel/LibreOffice."
            )
        except Exception as e:
            raise ValueError(f"Error validando estructura Excel: {e}")
        
        self.logger.debug(f"Validación exitosa: {file.name}")
    
    def _load_workbook(self, path: str):
        """
        Carga el archivo Excel en memoria.
        
        Args:
            path: Ruta al archivo Excel
            
        Raises:
            ValueError: Si el workbook no se puede cargar o está vacío
        """
        try:
            # Cargar con data_only=True para leer valores, no fórmulas
            self.workbook = openpyxl.load_workbook(path, data_only=True)
            self.filepath = path
            
            # Validar que tiene hojas
            if not self.workbook.sheetnames:
                raise ValueError("El Excel no contiene hojas")
            
            self.logger.info(
                f"Workbook cargado: {len(self.workbook.sheetnames)} hojas "
                f"({', '.join(self.workbook.sheetnames)})"
            )
            
        except Exception as e:
            raise ValueError(f"Error cargando workbook: {e}")
        
    def _find_blocks(self) -> List[Dict[str, Any]]:
        """
        Localiza todos los bloques de horarios en todas las hojas.
        
        Returns:
            Lista de diccionarios con información de cada bloque detectado
        """
        blocks = []
        
        for sheet_name in self.workbook.sheetnames:
            sheet = self.workbook[sheet_name]
            self.stats['sheets_processed'] += 1
            
            self.logger.debug(f"Escaneando hoja: {sheet_name}")
            
            # Buscar bloques en esta hoja
            sheet_blocks = self._find_blocks_in_sheet(sheet, sheet_name)
            
            if sheet_blocks:
                self.stats['sheets_with_schedules'] += 1
                blocks.extend(sheet_blocks)
                self.logger.info(
                    f"Hoja '{sheet_name}': {len(sheet_blocks)} bloques detectados"
                )
            else:
                self.stats['sheets_empty'] += 1
                self.logger.warning(f"Hoja '{sheet_name}': sin bloques detectados")
        
        self.stats['blocks_detected'] = len(blocks)
        self.logger.info(f"Total de bloques detectados: {len(blocks)}")
        
        return blocks
    
    def _extract_raw_table(self, block: Dict[str, Any]) -> RawTable:
        ...


    def _find_blocks_in_sheet(self, sheet, sheet_name: str) -> List[Dict[str, Any]]:
        blocks = []

        max_scan_rows = self.config['max_header_scan_rows']  # ahora sí se usa
        min_days = self.config['min_days_in_header']

        row_idx = 1
        max_row = sheet.max_row

        while row_idx <= max_row:
            row_cells = [cell.value for cell in sheet[row_idx]]

            # Detección EXACTA de días (no substring)
            days_found = self._row_days_exact(row_cells)

            if len(days_found) >= min_days:
                block = self._extract_block_info(sheet, sheet_name, row_idx, days_found, max_row)
                if block:
                    blocks.append(block)
                    row_idx = block['data_end_row'] + 1
                    continue  # sigue con la siguiente zona
            # Tope blando de escaneo superior (evita recorrer miles de filas en hojas problemáticas
            if row_idx >= max_scan_rows and not blocks:
                # seguimos escaneando, pero si quieres hacerlo estricto, podrías break
                pass

            row_idx += 1

        return blocks

    def _extract_block_info(self, sheet, sheet_name: str, header_row: int, days_found: Dict[str, int], max_row: int) -> Optional[Dict[str, Any]]:
        """
        Extrae información completa de un bloque.
        Requiere 5 días canónicos en orden y contiguos.
        Valida que la columna inmediatamente a la izquierda es de 'hora'.
        """

        # 1) Orden canon L->V y exigir 5 días
        ordered = []
        for d in DAYS_CANONICAL:
            col = days_found.get(d)
            if not col:
                self.logger.debug(f"[{sheet_name}!{header_row}] Falta día en cabecera: {d}")
                return None
            ordered.append((d, col))

        # 2) Contigüidad estricta de columnas (L..V consecutivos)
        ordered_cols = [c for _, c in ordered]
        diffs = [ordered_cols[i+1] - ordered_cols[i] for i in range(len(ordered_cols)-1)]
        if any(x != 1 for x in diffs):
            self.logger.debug(f"[{sheet_name}!{header_row}] Días no contiguos: {ordered_cols}")
            return None

        lunes_col = ordered_cols[0]
        time_col = lunes_col - 1
        if time_col < 1:
            self.logger.debug(f"[{sheet_name}!{header_row}] No hay columna de hora a la izquierda de LUNES")
            return None

        # 3) Validar ancho mínimo del bloque
        min_col = time_col
        max_col = ordered_cols[-1]
        min_cols = self.config.get('min_cols_for_block', 6)
        if (max_col - min_col + 1) < min_cols:
            self.logger.debug(f"[{sheet_name}!{header_row}] Bloque demasiado estrecho: {min_col}-{max_col}")
            return None

        # 4) Validar que la columna 'hora' realmente lo parece
        if not self._col_looks_like_time(sheet, time_col, header_row + 1):
            self.logger.debug(f"[{sheet_name}!{header_row}] La columna de hora no parece válida (col {time_col})")
            return None

        # 5) Rango vertical del bloque
        data_start_row = header_row + 1
        data_end_row = self._find_block_end(sheet, data_start_row, max_row, min_col, max_col)

        # 6) Mínimo de filas
        min_rows = self.config['min_rows_for_block']
        if (data_end_row - data_start_row + 1) < min_rows:
            self.logger.debug(f"[{sheet_name}!{header_row}] Bloque con pocas filas: {(data_end_row - data_start_row + 1)}")
            return None

        # 7) Construir map day_cols en orden canónico (por si downstream lo agradece)
        day_cols_map = {d: c for d, c in ordered}

        return {
            'sheet_name': sheet_name,
            'sheet': sheet,
            'header_row': header_row,
            'data_start_row': data_start_row,
            'data_end_row': data_end_row,
            'time_col': time_col,
            'day_cols': day_cols_map,
            'min_col': min_col,
            'max_col': max_col,
        }

    def _find_block_end(self, sheet, start_row: int, max_row: int, min_col: int, max_col: int) -> int:
        """
        Encuentra la última fila del bloque.
        
        Criterios de fin:
        - Se encuentra otra cabecera de días
        - Hay N filas vacías consecutivas
        - Se alcanza el final de la hoja
        
        Args:
            sheet: Worksheet
            start_row: Primera fila de datos del bloque
            max_row: Última fila de la hoja
            min_col: Columna mínima del bloque
            max_col: Columna máxima del bloque
            
        Returns:
            Número de la última fila del bloque
        """
        max_empty_rows = self.config['max_empty_rows_between_blocks']
        empty_row_count = 0
        last_valid_row = start_row
        
        for row_idx in range(start_row, max_row + 1):
            # Leer celdas del rango del bloque
            row_cells = [
                sheet.cell(row_idx, col).value 
                for col in range(min_col, max_col + 1)
            ]
            
            # Verificar si es una nueva cabecera
            days_in_row = self._row_days_exact(row_cells)
            if len(days_in_row) >= self.config['min_days_in_header']:
                # Nueva cabecera encontrada, fin del bloque actual
                return last_valid_row
            
            # Verificar si la fila está vacía
            if all(cell is None or str(cell).strip() == '' for cell in row_cells):
                empty_row_count += 1
                if empty_row_count >= max_empty_rows:
                    # Demasiadas filas vacías, fin del bloque
                    return last_valid_row
            else:
                # Fila con contenido
                empty_row_count = 0
                last_valid_row = row_idx
        
        return last_valid_row


    #========================= Métodos auxiliares (placeholders) ========================#
    def _norm(self, s: str) -> str:
        """Upper + strip + colapso espacios + sin acentos básicos."""
        s = (s or "").strip()
        s = " ".join(s.split())
        s = s.upper()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s

    def _row_days_exact(self, row_cells: list[str]) -> dict:
        """
        Devuelve {canonical_day: col_idx} solo si el contenido de la celda
        es exactamente un día (por alias), no por substring suelto.
        """
        found = {}
        for col_idx, v in enumerate(row_cells, start=1):
            if v is None:
                continue
            cell = self._norm(str(v))
            for alias, canonical in DAY_ALIASES.items():
                if self._norm(alias) == cell:
                    found[canonical] = col_idx
                    break
        return found

    def _col_looks_like_time(self, sheet, col: int, start_row: int, samples: int = 3) -> bool:
        """
        Comprueba si una columna parece de hora (match en 2 de 3 filas siguientes).
        Acepta formas: texto '10:00' o '10:30 - 11:30', datetime/time reales de Excel
        o números con formato de hora (cell.is_date).
        """
        import re, datetime as _dt
        rx = re.compile(r"(?i)\b([01]?\d|2[0-3])[:\.h]?[0-5]\d(?:\s*[-–—]\s*([01]?\d|2[0-3])[:\.h]?[0-5]\d)?\b")
        ok = 0
        r = start_row
        # Probamos un pequeño tramo por debajo del header
        while r <= sheet.max_row and (r - start_row) < 6 and ok < 2 and (r - start_row) < samples + 3:
            cell = sheet.cell(r, col)
            val = cell.value
            # 1) Si es fecha/hora nativa de openpyxl
            if isinstance(val, (_dt.time, _dt.datetime)):
                ok += 1
                r += 1
                continue
            # 2) Si es numérico pero la celda está formateada como fecha/hora
            #    (openpyxl marca is_date cuando el number_format es de fecha/hora)
            try:
                if getattr(cell, "is_date", False):
                    ok += 1
                    r += 1
                    continue
            except Exception:
                pass
            # 3) Texto con horas o rangos
            if isinstance(val, str):
                s = val.strip()
                if s and rx.search(s):
                    ok += 1
            r += 1
        return ok >= 2

