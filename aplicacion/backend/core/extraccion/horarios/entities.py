"""
Entidades del dominio de extracción y normalización de horarios académicos.
"""

from dataclasses import dataclass, field
from datetime import time
from typing import List, Optional

from constants.enums import (
    DiaSemana,
    ModalidadSesion,
    Periodo,
    TipoAula,
    TipoGrupoDocente,
    TipoRecurrencia,
)
from core.extraccion.common.entities import ExtractionMetadata, ParsingMetadata


@dataclass(frozen=True)
class TablaHorario:
    """Representa una tabla individual de horario extraída del PDF."""
    curso: str
    day_columns: List[str]
    time_rows: List[str]
    celdas: List[List[Optional[str]]]
    mencion: Optional[str] = None
    pagina: Optional[int] = None


@dataclass(frozen=True)
class HorarioExtractionResult:
    """Resultado de la extracción completa del PDF de horarios."""
    titulo: str
    tablas: List[TablaHorario]
    metadata: ExtractionMetadata


@dataclass
class Sesion:
    """Sesión individual de clase."""
    asignatura: str
    aula: str
    dia: str
    hora_inicio: time
    hora_fin: time
    tipo: Optional[str] = None
    grupo: Optional[str] = None


@dataclass
class Horario:
    """Horario completo correspondiente a una tabla."""
    curso: str
    periodo: str
    sesiones: List[Sesion] = field(default_factory=list)
    mencion: Optional[str] = None
    pagina: Optional[int] = None


@dataclass
class ParsingResult:
    """Resultado del proceso de parsing de tablas extraídas."""
    titulo: str
    horarios: List[Horario]
    extraction_metadata: ExtractionMetadata
    parsing_metadata: ParsingMetadata


@dataclass
class NormalizedSesionHorarioData:
    """Sesión de horario normalizada, lista para persistir en BD."""
    asignatura_nombre: str
    grupo_codigo: str
    tipo_grupo: TipoGrupoDocente
    dia_semana: DiaSemana
    hora_inicio: time
    hora_fin: time
    aula_nombre: str
    aula_tipo: TipoAula
    modalidad: ModalidadSesion = ModalidadSesion.PRESENCIAL
    tipo_recurrencia: TipoRecurrencia = TipoRecurrencia.SEMANAL


@dataclass
class NormalizedHorarioTablaData:
    """Horario normalizado correspondiente a una tabla completa."""
    programa_nombre: str
    curso: int
    periodo: Periodo
    mencion: Optional[str]
    sesiones: List[NormalizedSesionHorarioData] = field(default_factory=list)