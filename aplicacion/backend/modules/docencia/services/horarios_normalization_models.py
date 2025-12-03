from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from modules.docencia.schemas.horarios import (
    HorarioTemporalConfirmIn,
    HorarioTablaTemporal,
    HorarioSesionTemporal,
)


@dataclass
class ParsedSesionForNormalization:
    """Representación mínima de una sesión para el normalizador.

    Solo contiene los campos que el HorarioDataNormalizer necesita leer,
    con nombres compatibles con las entidades del parser original.
    """
    asignatura: str
    aula: str
    dia: str
    hora_inicio: str
    hora_fin: str
    tipo: str
    grupo: str


@dataclass
class ParsedHorarioForNormalization:
    """Representación mínima de una tabla de horario para el normalizador."""

    curso: str
    periodo: str
    mencion: Optional[str]
    sesiones: List[ParsedSesionForNormalization]


@dataclass
class ParsingResultForNormalization:
    """Representación mínima de un ParsingResult para el normalizador.

    No es el ParsingResult original del parser, pero expone la misma interfaz
    que el normalizador espera: un objeto con `titulo` y una lista de
    `horarios`, donde cada horario tiene `curso`, `periodo`, `mencion` y
    `sesiones`.
    """

    titulo: str
    horarios: List[ParsedHorarioForNormalization]


def _build_sesion_for_normalization(
    ses: HorarioSesionTemporal,
) -> ParsedSesionForNormalization:
    """Construir una sesión adaptada al normalizador a partir del DTO temporal."""

    return ParsedSesionForNormalization(
        asignatura=ses.asignatura or "",
        aula=ses.aula or "",
        dia=ses.dia or "",
        hora_inicio=ses.hora_inicio or "",
        hora_fin=ses.hora_fin or "",
        tipo=ses.tipo or "",
        grupo=ses.grupo or "",
    )


def _build_horario_for_normalization(
    tabla: HorarioTablaTemporal,
    periodo_global: Optional[str],
) -> ParsedHorarioForNormalization:
    """Construir un horario adaptado al normalizador a partir de una tabla DTO."""

    sesiones = [
        _build_sesion_for_normalization(ses)
        for ses in (tabla.sesiones or [])
    ]

    # Determinar periodo textual: primero el de la propia tabla, luego el global
    periodo_text = tabla.periodo or periodo_global or ""

    return ParsedHorarioForNormalization(
        curso=tabla.curso or "",
        periodo=periodo_text,
        mencion=tabla.mencion,
        sesiones=sesiones,
    )


def build_parsing_result_for_normalization(
    data: HorarioTemporalConfirmIn,
) -> ParsingResultForNormalization:
    """Construir una estructura tipo ParsingResult a partir del DTO confirm.

    Esta función actúa como adaptador entre el DTO que maneja la API
    (`HorarioTemporalConfirmIn`) y la interfaz que espera el
    `HorarioDataNormalizer`.
    """

    horarios = [
        _build_horario_for_normalization(tabla, data.periodo)
        for tabla in data.horarios
    ]

    titulo_text = data.titulo or data.plan or ""

    return ParsingResultForNormalization(
        titulo=titulo_text,
        horarios=horarios,
    )
