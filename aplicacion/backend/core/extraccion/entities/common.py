"""
Entidades y tipos de datos compartidos para el sistema de extracción académica.

Este módulo contiene los enums, dataclasses y tipos base utilizados
en todo el sistema de extracción de PDFs académicos.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple


# =========================
# Excepciones y reportes
# =========================
class ParserError(Exception):
    """Error de parsing (distinto a errores de extracción)."""
    pass


@dataclass
class ParseReport:
    """
    Informe homogéneo del proceso de parsing para logging/diagnóstico.
    """
    parser_name: str
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)