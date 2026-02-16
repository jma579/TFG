"""
Definiciones de tipos para el sistema de detección de conflictos.
"""

from typing import Optional, List, Literal
from datetime import datetime, time
from pydantic import BaseModel, field_validator, model_validator, Field
from constants.enums import TipoConflicto, SeveridadConflicto


# Value Objects (tiempo)

class Intervalo(BaseModel):
    """Intervalo de tiempo con inicio y fin."""
    inicio: datetime
    fin: datetime
    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _check_order(self):
        if not self.inicio < self.fin:
            raise ValueError("Intervalo: fin debe ser posterior a inicio")
        return self


class SlotSemanal(BaseModel):
    """Slot semanal recurrente (día y horario)."""
    dia_semana: int  # 0=Lunes, 6=Domingo
    hora_inicio: time
    hora_fin: time
    model_config = {"frozen": True}

    @field_validator("dia_semana")
    @classmethod
    def _check_day(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError("SlotSemanal: dia_semana debe estar en [0..6]")
        return v

    @model_validator(mode="after")
    def _check_order(self):
        if not self.hora_inicio < self.hora_fin:
            raise ValueError("SlotSemanal: hora_fin debe ser posterior a hora_inicio")
        return self


# Entidades de entrada al motor (DTOs)

class SesionRef(BaseModel):
    """Referencia a una sesión para el motor de detección."""
    id: int
    aula_id: Optional[int] = None
    profesor_ids: List[int] = Field(default_factory=list)
    asignatura_id: int 
    grupo_id: int
    curso: int = 0
    periodo: str = "" 
    tipo_grupo: str = "TEORIA"
    grupo_codigo: str = "UNICO"
    mencion_ids: List[int] = Field(default_factory=list)
    
    grado_nombre: str = "Plan de Estudios"
    mencion_nombre: Optional[str] = None
    periodo_nombre: str = ""

    tipo_recurrencia: Literal["SEMANAL", "FECHADA"]
    slot: Optional[SlotSemanal] = None
    intervalo: Optional[Intervalo] = None

    model_config = {"frozen": True}


class RestriccionRef(BaseModel):
    """Referencia a una restricción de profesor para el motor de detección."""
    id: int
    profesor_id: int
    slot: SlotSemanal

    model_config = {"frozen": True}
    

# Resultados

class ParametrosDeteccion(BaseModel):
    """Parámetros de configuración para la detección."""
    incluir_solapamientos_profesor: bool = True
    incluir_solapamientos_aula: bool = True
    incluir_violaciones_restriccion: bool = True
    incluir_solapamientos_grupo: bool = True
    severidad_minima: SeveridadConflicto = SeveridadConflicto.LEVE
    rango_fechas: Optional[tuple[datetime, datetime]] = None
    model_config = {"frozen": True}


class ResultadoDeteccion(BaseModel):
    """Resultado de la detección de un conflicto."""
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    sesion_id: int
    sesion_2_id: Optional[int] = None
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    restriccion_id: Optional[int] = None
    grupo_id: Optional[int] = None
    asignatura_id: Optional[int] = None
    descripcion: str
    hash_deteccion: str
    model_config = {"frozen": False}