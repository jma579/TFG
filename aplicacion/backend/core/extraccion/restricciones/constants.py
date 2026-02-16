"""
Configuración y constantes para la extracción de restricciones de profesorado.
"""

# Nombres de columnas esperadas en el archivo Excel
COL_PROFESOR = "Profesor"
COL_DIAS = "Dias"
COL_FRANJA = "Franja"

REQUIRED_COLUMNS = [COL_PROFESOR, COL_DIAS, COL_FRANJA]


MAP_DIAS = {
    "L": "LUNES",
    "M": "MARTES",
    "X": "MIERCOLES",
    "MI": "MIERCOLES",
    "J": "JUEVES",
    "V": "VIERNES",
    "S": "SABADO",
    "D": "DOMINGO"
}


PATTERN_FRANJA = r"^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$"