from typing import List, Optional
import re
import logging

from core.extraccion.horarios.internal_models import GridCell, TextAtom
from core.extraccion.horarios.constants import (
    STITCHING_CONFIG, REPAIRS_BROKEN_WORDS
)

class SpatialMapper:
    """
    Responsable de:
    1. BUCKETING: Asignar átomos de texto a sus celdas geométricas.
    2. STITCHING: Reconstruir palabras partidas y frases dentro de cada celda.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def map_and_stitch(self, cells: List[GridCell], atoms: List[TextAtom]) -> None:
        """
        Proceso completo: Llena las celdas y luego genera su texto final.
        """
        # 1. Bucketing (Fuerza bruta optimizada)
        # Iteramos sobre átomos y buscamos su celda
        for atom in atoms:
            for cell in cells:
                if cell.contains(atom):
                    cell.atoms.append(atom)
                    break 
        
        # 2. Stitching (Procesar cada celda llena)
        for cell in cells:
            cell.final_text = self._build_cell_text(cell)

    def _build_cell_text(self, cell: GridCell) -> Optional[str]:
        """
        Reconstruye el string de una celda analizando distancias entre átomos.
        """
        if not cell.atoms:
            return None
            
        # Ordenar: Primero Arriba-Abajo (top), luego Izquierda-Derecha (x0)
        # Dividimos top/5 para agrupar visualmente renglones
        atoms = sorted(cell.atoms, key=lambda a: (int(a.top / 5), a.x0))
        
        lines = []
        current_line = []
        last_atom = None
        
        for atom in atoms:
            if last_atom is None:
                current_line.append(atom.text)
                last_atom = atom
                continue
            
            # Calcular distancias físicas
            dist_x = atom.x0 - last_atom.x1
            dist_y = atom.top - last_atom.top
            
            # A. DETECCIÓN DE NUEVA LÍNEA (Salto de renglón visual)
            if dist_y > STITCHING_CONFIG['newline_threshold']:
                lines.append(" ".join(current_line))
                current_line = [atom.text]
            
            # B. LOGICA DE COSIDO HORIZONTAL
            else:
                if dist_x < STITCHING_CONFIG['stitch_threshold']:
                    # FUSIÓN: Letras muy pegadas ("Ing" + "en") -> Pegar al token anterior
                    current_line[-1] += atom.text
                elif dist_x < STITCHING_CONFIG['space_threshold']:
                    # ESPACIO NORMAL: ("Sistemas" + "Operativos") -> Nuevo token
                    current_line.append(atom.text)
                else:
                    # ESPACIO GRANDE: (Tabulación o columnas internas) -> Nuevo token
                    current_line.append(atom.text)
            
            last_atom = atom
            
        if current_line:
            lines.append(" ".join(current_line))
            
        full_text = "\n".join(lines).strip()
        
        # C. REPARACIONES FINALES (REGEX)
        full_text = self._apply_global_repairs(full_text)
        
        return full_text if full_text else None

    def _apply_global_repairs(self, text: str) -> str:
        """Aplica correcciones de glosario y limpieza final."""
        # 1. Regex de diccionario
        for pat, repl in REPAIRS_BROKEN_WORDS:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        
        # 2. Corregir CamelCase ("SistemasOperativos" -> "Sistemas Operativos")
        text = re.sub(r'([a-zñáéíóú])([A-ZÑÁÉÍÓÚ])', r'\1 \2', text)
        
        # 3. Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text