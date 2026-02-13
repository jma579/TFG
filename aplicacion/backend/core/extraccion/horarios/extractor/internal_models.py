"""Modelos internos para la representación espacial de texto y grid."""

from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class TextAtom:
    """
    Representa una unidad mínima de texto (palabra, sílaba o letra)
    con su posición espacial precisa.
    """
    text: str
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

@dataclass
class GridCell:
    """Representa una celda virtual en la rejilla detectada."""
    row_idx: int
    col_idx: int
    bbox: Tuple[float, float, float, float] # (x0, top, x1, bottom)
    
    atoms: List[TextAtom] = field(default_factory=list)
    
    final_text: str = None
    
    @property
    def x0(self): return self.bbox[0]
    @property
    def top(self): return self.bbox[1]
    @property
    def x1(self): return self.bbox[2]
    @property
    def bottom(self): return self.bbox[3]
    
    def contains(self, atom: TextAtom, margin: float = -1.0) -> bool:
        """Verifica si el CENTROIDE del átomo cae en esta celda."""
        cx, cy = atom.center_x, atom.center_y
        return (self.x0 - margin <= cx <= self.x1 + margin) and \
               (self.top - margin <= cy <= self.bottom + margin)