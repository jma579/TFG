"""
Entidades tipadas para representar horarios académicos y sus sesiones.
Pensadas para ser la salida intermedia del parser y facilitar la
posterior normalización/persistencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import List, Optional

from core.extraccion.entities.extractor import ExtractionMetadata


@dataclass
class ScheduleEntry:
    """
    Representa una sesión docente semanal de una asignatura en un día concreto.

    Atributos:
        asignatura: Nombre de la asignatura (texto tal cual aparece en el horario).
        curso: Curso académico (1..5) si el bloque lo indica; None si no se detecta.
        grupo: Código o etiqueta del grupo (p. ej., "Grupo 2"); si no hay, suele usarse "G0".
        dia_semana: Día de la semana en MAYÚSCULAS (p. ej., "LUNES", "MIÉRCOLES").
        hora_inicio: Hora de inicio (objeto datetime.time).
        hora_fin: Hora de fin (objeto datetime.time).
        aula: Identificador de aula (p. ej., "AULA 4", "LSC 1").
        modalidad: "TEORIA" o "LAB" (o None si el parser no pudo inferirla).
        recurrencia: Frecuencia de repetición; por defecto "SEMANAL".
    """
    asignatura: str
    curso: Optional[int]
    grupo: Optional[str]
    dia_semana: str
    hora_inicio: time
    hora_fin: time
    aula: str
    modalidad: Optional[str]
    recurrencia: str = "SEMANAL"


@dataclass
class ScheduleSheet:
    """
    Resultado global del parseo de un documento de horario.

    Atributos:
        programa: Nombre del programa/título si se detecta (p. ej., "DOBLE GRADO EN ...").
        periodo_text: Texto del periodo si aparece (p. ej., "PRIMER CUATRIMESTRE").
        entries: Lista de sesiones detectadas.
        raw_text: Texto original (pre o post-procesado) para auditoría.
        metadata: Metadatos de extracción (fuente, confianza, etc.).
    """
    programa: Optional[str]
    periodo_text: Optional[str]
    entries: List[ScheduleEntry]
    raw_text: Optional[str] = None
    metadata: Optional[ExtractionMetadata] = None


__all__ = ["ScheduleEntry", "ScheduleSheet"]
