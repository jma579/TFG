from typing import List
import logging
from core.extraccion.horarios.extractor.constants import PDFPLUMBER_GRID_SETTINGS, GRID_CONFIG
from core.extraccion.horarios.extractor.internal_models import GridCell

class GridDetector:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect(self, page) -> List[GridCell]:
        tables = page.find_tables(PDFPLUMBER_GRID_SETTINGS)
        
        if not tables: return []
            
        cells = []
        
        for table in tables:
            if not table.cells: continue

            # Recolectar todas las líneas posibles
            raw_v_lines = []
            raw_h_lines = []
            
            for cell in table.cells:
                if cell:
                    raw_v_lines.extend([cell[0], cell[2]])
                    raw_h_lines.extend([cell[1], cell[3]])
            
            # Ordenar y DEDUPLICAR AGRESIVAMENTE
            # Usamos tolerancia 5 para fusionar bordes dobles visuales
            unique_v = self._deduplicate_lines(sorted(raw_v_lines), tolerance=5)
            unique_h = self._deduplicate_lines(sorted(raw_h_lines), tolerance=5)
            
            if len(unique_v) < 2 or len(unique_h) < 2: continue

            # Construir Celdas
            for r_idx in range(len(unique_h) - 1):
                y0 = unique_h[r_idx]
                y1 = unique_h[r_idx + 1]
                
                # Descartar filas muy finas
                if (y1 - y0) < GRID_CONFIG['min_row_height']:
                    continue
                    
                for c_idx in range(len(unique_v) - 1):
                    x0 = unique_v[c_idx]
                    x1 = unique_v[c_idx + 1]
                    
                    # Descartar columnas muy estrechas (CRÍTICO para eliminar dobles bordes)
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
                # Si están muy cerca, promediamos la posición (opcional, pero mejora precisión)
                unique[-1] = (unique[-1] + val) / 2
        return unique