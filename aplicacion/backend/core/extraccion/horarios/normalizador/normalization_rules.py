"""
Reglas y mapeos estáticos para la normalización de horarios.
Aquí se definen las equivalencias entre texto crudo y Enums de negocio.
"""

from typing import Dict, List
from constants.enums import (
    DiaSemana,
    Periodo,
    TipoAula
)

# Mapeo de texto a Enum DiaSemana
DIA_SEMANA_MAP: Dict[str, DiaSemana] = {
    "LUNES": DiaSemana.LUNES, "LUN": DiaSemana.LUNES,
    "MARTES": DiaSemana.MARTES, "MAR": DiaSemana.MARTES,
    "MIERCOLES": DiaSemana.MIERCOLES, "MIE": DiaSemana.MIERCOLES, "X": DiaSemana.MIERCOLES,
    "JUEVES": DiaSemana.JUEVES, "JUE": DiaSemana.JUEVES,
    "VIERNES": DiaSemana.VIERNES, "VIE": DiaSemana.VIERNES,
    "SABADO": DiaSemana.SABADO, "SAB": DiaSemana.SABADO,
    "DOMINGO": DiaSemana.DOMINGO, "DOM": DiaSemana.DOMINGO
}

# Mapeo de texto a Enum Periodo
PERIODO_MAP: Dict[str, Periodo] = {
    "PRIMER CUATRIMESTRE": Periodo.PRIMER_CUATRIMESTRE,
    "1C": Periodo.PRIMER_CUATRIMESTRE,
    "C1": Periodo.PRIMER_CUATRIMESTRE,
    "SEGUNDO CUATRIMESTRE": Periodo.SEGUNDO_CUATRIMESTRE,
    "2C": Periodo.SEGUNDO_CUATRIMESTRE,
    "C2": Periodo.SEGUNDO_CUATRIMESTRE,
    "ANUAL": Periodo.ANUAL,
    "PRIMER SEMESTRE": Periodo.PRIMER_SEMESTRE,
    "SEGUNDO SEMESTRE": Periodo.SEGUNDO_SEMESTRE,
}

# Mapeo de texto a Curso (Entero)
CURSO_MAP: Dict[str, int] = {
    "PRIMER": 1, "PRIMERO": 1, "1": 1, "1º": 1, "I": 1,
    "SEGUNDO": 2, "2": 2, "2º": 2, "II": 2,
    "TERCER": 3, "TERCERO": 3, "3": 3, "3º": 3, "III": 3,
    "CUARTO": 4, "4": 4, "4º": 4, "IV": 4,
    "QUINTO": 5, "5": 5, "5º": 5, "V": 5,
    "SEXTO": 6, "6": 6, "6º": 6, "VI": 6
}

# Palabras clave para inferir TipoAula
KEYWORDS_AULA: Dict[TipoAula, List[str]] = {
    TipoAula.INFORMATICA: ["INF", "ORDENADOR", "COMPUT", "LSC"],
    TipoAula.LABORATORIO: ["LAB", "FÍSICA", "FISICA", "QUÍMICA", "QUIMICA", "BIOLOGÍA", "LATC"],
    TipoAula.SEMINARIO: ["SEM", "SEMINARIO"],
    TipoAula.TALLER: ["TALLER"],
    # El resto se considerará TEORICA por defecto
}

# Constantes de validación
CURSO_MIN = 1
CURSO_MAX = 6