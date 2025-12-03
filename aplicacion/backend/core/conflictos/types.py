"""
Definiciones de tipos para el sistema de detección de conflictos.

Este módulo contiene únicamente las definiciones de estructura de datos
sin lógica de negocio. Las validaciones complejas y operaciones van en
módulos separados para mantener la separación de responsabilidades.
"""

from __future__ import annotations

from typing import Optional, List, Literal
from datetime import datetime, time
from pydantic import BaseModel, field_validator, model_validator, Field

# Importa enums globales desde constants (no redefinir aquí)
from constants.enums import TipoConflicto, SeveridadConflicto  # ajusta rutas si difieren

# -----------------------------------------------------------------------------
# Value Objects (tiempo)
# -----------------------------------------------------------------------------

class Intervalo(BaseModel):
    """Ventana temporal fechada (con fecha y hora)."""
    inicio: datetime
    fin: datetime

    model_config = {"frozen": True}  # opcional: inmutable

    @model_validator(mode="after")
    def _check_order(self):
        if not self.inicio < self.fin:
            raise ValueError("Intervalo: fin debe ser posterior a inicio")
        return self


class SlotSemanal(BaseModel):
    """Ventana temporal semanal recurrente (sin fecha concreta)."""
    # 0=Lunes … 6=Domingo (ajusta a tu convención)
    dia_semana: int
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
        # Reglas típicas de solape consideran contiguos (fin == inicio) como NO solapados
        if not self.hora_inicio < self.hora_fin:
            raise ValueError("SlotSemanal: hora_fin debe ser posterior a hora_inicio")
        return self

# -----------------------------------------------------------------------------
# Entidades de entrada al motor (DTOs)
# -----------------------------------------------------------------------------

class SesionRef(BaseModel):
    """
    DTO de sesión para el motor de conflictos.
    No arrastra ORM; suficiente para decidir solapes y restricciones.
    """
    id: int
    aula_id: int
    profesor_ids: List[int]
    tipo_recurrencia: Literal["SEMANAL", "FECHADA"]
    slot: Optional[SlotSemanal] = None
    intervalo: Optional[Intervalo] = None

    model_config = {"frozen": True}

    @field_validator("profesor_ids")
    @classmethod
    def _clean_profesor_ids(cls, v: List[int]) -> List[int]:
        # Solo limpieza básica de tipo, sin lógica de negocio
        return v if v else []

class RestriccionRef(BaseModel):
    """
    DTO de restricción: aplica a PROFESOR o AULA, y puede ser semanal o fechada.
    """
    id: int
    ambito: Literal["PROFESOR", "AULA"]
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    slot: Optional[SlotSemanal] = None
    intervalo: Optional[Intervalo] = None
    es_blanda: bool = False  # blanda = warning; dura = blocking

    model_config = {"frozen": True}

# -----------------------------------------------------------------------------
# Resultado del motor
# -----------------------------------------------------------------------------

class ParametrosDeteccion(BaseModel):
    """Parámetros para configurar la detección de conflictos"""
    incluir_solapamientos_profesor: bool = True
    incluir_solapamientos_aula: bool = True
    incluir_violaciones_restriccion: bool = True
    severidad_minima: SeveridadConflicto = SeveridadConflicto.BAJA
    rango_fechas: Optional[tuple[datetime, datetime]] = None

    model_config = {"frozen": True}


class ResultadoDeteccion(BaseModel):
    """
    Resultado canónico del motor de conflictos.
    Nota: hash_deteccion asegura idempotencia al persistir.
    """
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    sesion_id: int
    sesion_2_id: Optional[int] = None  # para conflictos binarios (e.g., solapes)
    profesor_id: Optional[int] = None  # si aplica
    aula_id: Optional[int] = None      # si aplica
    restriccion_id: Optional[int] = None  # si aplica
    descripcion: str
    hash_deteccion: str
    datos_contexto: dict = Field(default_factory=dict)  # Metadatos adicionales del contexto

    model_config = {"frozen": True}
