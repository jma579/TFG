"""Detección de estructura de rejilla (grid) en tablas de horarios PDF."""

from typing import List
import logging
from core.extraccion.horarios.extractor.constants import PDFPLUMBER_GRID_SETTINGS, GRID_CONFIG
from core.extraccion.horarios.extractor.internal_models import GridCell

class GridDetector:
    """Detecta y construye la estructura de rejilla de una tabla de horario.
    
    Utiliza las líneas detectadas por pdfplumber para construir una matriz
    de celdas geométricas que representan la estructura de la tabla.
    """
    
    def __init__(self):
        """Inicializa el detector de rejilla."""
        self.logger = logging.getLogger(__name__)

    def detect(self, page) -> List[GridCell]:
        """Detecta y construye las celdas de la rejilla en una página."""
        tables = page.find_tables(PDFPLUMBER_GRID_SETTINGS)
        
        if not tables: return []
            
        cells = []
        
        for table in tables:
            if not table.cells: continue

            raw_v_lines = []
            raw_h_lines = []
            
            for cell in table.cells:
                if cell:
                    raw_v_lines.extend([cell[0], cell[2]])
                    raw_h_lines.extend([cell[1], cell[3]])
            
            unique_v = self._deduplicate_lines(sorted(raw_v_lines), tolerance=5)
            unique_h = self._deduplicate_lines(sorted(raw_h_lines), tolerance=5)
            
            if len(unique_v) < 2 or len(unique_h) < 2: continue

            for r_idx in range(len(unique_h) - 1):
                y0 = unique_h[r_idx]
                y1 = unique_h[r_idx + 1]
                
                if (y1 - y0) < GRID_CONFIG['min_row_height']:
                    continue
                    
                for c_idx in range(len(unique_v) - 1):
                    x0 = unique_v[c_idx]
                    x1 = unique_v[c_idx + 1]
                    
                    if (x1 - x0) < GRID_CONFIG['min_col_width']:
                        continue
                    
                    cell = GridCell(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        bbox=(x0, y0, x1, y1)
                    )
                    cells.append(cell)
                    
        return cells

    def _deduplicate_lines(self, lines: List[float], tolerance: float) -> List[float]:
        """Fusiona líneas cercanas."""
        if not lines: return []
        
        unique = [lines[0]]
        for val in lines[1:]:
            if val - unique[-1] > tolerance:
                unique.append(val)
            else:
                unique[-1] = (unique[-1] + val) / 2
        return unique