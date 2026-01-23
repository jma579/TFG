"""
Definiciones de tipos para el sistema de detección de conflictos.
Actualizado para incluir contexto de asignatura y grupos.
"""
from __future__ import annotations
from typing import Optional, List, Literal
from datetime import datetime, time
from pydantic import BaseModel, field_validator, model_validator, Field
from constants.enums import TipoConflicto, SeveridadConflicto

# -----------------------------------------------------------------------------
# Value Objects (tiempo)
# -----------------------------------------------------------------------------

class Intervalo(BaseModel):
    inicio: datetime
    fin: datetime
    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _check_order(self):
        if not self.inicio < self.fin:
            raise ValueError("Intervalo: fin debe ser posterior a inicio")
        return self

class SlotSemanal(BaseModel):
    # 0=Lunes, 6=Domingo
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
        if not self.hora_inicio < self.hora_fin:
            raise ValueError("SlotSemanal: hora_fin debe ser posterior a hora_inicio")
        return self

# -----------------------------------------------------------------------------
# Entidades de entrada al motor (DTOs)
# -----------------------------------------------------------------------------

class SesionRef(BaseModel):
    """
    DTO de sesión enriquecido.
    Incluye asignatura y grupo para detectar colisiones de plan de estudios.
    """
    id: int
    aula_id: Optional[int] = None # Puede ser null si aún no se asignó aula
    profesor_ids: List[int] = Field(default_factory=list)
    
    # Nuevos campos para reglas de negocio
    asignatura_id: int 
    grupo_id: int
    
    curso: int = 0                  # Ej: 1, 2, 3...
    tipo_grupo: str = "TEORIA"      # TEORIA, PRACTICA, LABORATORIO...
    grupo_codigo: str = "UNICO"     # "A", "B", "1", "UNICO"
    mencion_ids: List[int] = Field(default_factory=list) # IDs de menciones asociadas
    
    tipo_recurrencia: Literal["SEMANAL", "FECHADA"]
    slot: Optional[SlotSemanal] = None
    intervalo: Optional[Intervalo] = None

    model_config = {"frozen": True}

class RestriccionRef(BaseModel):
    id: int
    ambito: Literal["PROFESOR", "AULA"]
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    slot: Optional[SlotSemanal] = None
    intervalo: Optional[Intervalo] = None
    es_blanda: bool = False

    model_config = {"frozen": True}

# -----------------------------------------------------------------------------
# Resultados
# -----------------------------------------------------------------------------

class ParametrosDeteccion(BaseModel):
    incluir_solapamientos_profesor: bool = True
    incluir_solapamientos_aula: bool = True
    incluir_violaciones_restriccion: bool = True
    incluir_solapamientos_grupo: bool = True # Nueva regla
    severidad_minima: SeveridadConflicto = SeveridadConflicto.LEVE
    rango_fechas: Optional[tuple[datetime, datetime]] = None
    model_config = {"frozen": True}

class ResultadoDeteccion(BaseModel):
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
    datos_contexto: dict = Field(default_factory=dict)
    model_config = {"frozen": False}