"""Mapeo espacial y reconstrucción de texto en celdas de rejilla."""

from typing import List, Optional
import re
import logging

from core.extraccion.horarios.extractor.internal_models import GridCell, TextAtom
from core.extraccion.horarios.extractor.constants import (
    STITCHING_CONFIG, REPAIRS_BROKEN_WORDS
)

class SpatialMapper:
    """Mapea átomos de texto a celdas y reconstruye texto coherente.
    
    Responsable de dos tareas principales:
    1. BUCKETING: Asignar átomos de texto a sus celdas geométricas correspondientes
    2. STITCHING: Reconstruir palabras y frases dentro de cada celda
    """
    
    def __init__(self):
        """Inicializa el mapeador espacial."""
        self.logger = logging.getLogger(__name__)

    def map_and_stitch(self, cells: List[GridCell], atoms: List[TextAtom]) -> None:
        """Ejecuta el proceso completo de mapeo y cosido de texto."""
        for atom in atoms:
            for cell in cells:
                if cell.contains(atom):
                    cell.atoms.append(atom)
                    break 
        
        for cell in cells:
            cell.final_text = self._build_cell_text(cell)

    def _build_cell_text(self, cell: GridCell) -> Optional[str]:
        """Reconstruye el string de una celda analizando distancias entre átomos."""
        if not cell.atoms:
            return None
            
        atoms = sorted(cell.atoms, key=lambda a: (int(a.top / 5), a.x0))
        
        lines = []
        current_line = []
        last_atom = None
        
        for atom in atoms:
            if last_atom is None:
                current_line.append(atom.text)
                last_atom = atom
                continue
            
            dist_x = atom.x0 - last_atom.x1
            dist_y = atom.top - last_atom.top
            
            # Deteccion de nueva linea
            if dist_y > STITCHING_CONFIG['newline_threshold']:
                lines.append(" ".join(current_line))
                current_line = [atom.text]
            
            # Logica de cosido horizontal
            else:
                if dist_x < STITCHING_CONFIG['stitch_threshold']:
                    current_line[-1] += atom.text
                elif dist_x < STITCHING_CONFIG['space_threshold']:
                    current_line.append(atom.text)
                else:
                    current_line.append(atom.text)
            
            last_atom = atom
            
        if current_line:
            lines.append(" ".join(current_line))
            
        full_text = "\n".join(lines).strip()
        
        # Reparaciones finales (regex)
        full_text = self._apply_global_repairs(full_text)
        
        return full_text if full_text else None

    def _apply_global_repairs(self, text: str) -> str:
        """Aplica correcciones de glosario y limpieza final."""
        for pat, repl in REPAIRS_BROKEN_WORDS:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        
        text = re.sub(r'([a-zñáéíóú])([A-ZÑÁÉÍÓÚ])', r'\1 \2', text)
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text