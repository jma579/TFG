"""
Esquemas Pydantic para la entidad Sesion.
"""

from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, List
from datetime import time, datetime

from constants.enums import (
    ModalidadSesion, TipoRecurrencia, DiaSemana
)
from modules.conflictos.schemas.conflicto import ConflictoOut



class ProfesorSesionBase(BaseModel):
    profesor_id: int = Field(..., gt=0)
    rol_en_sesion: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Rol del profesor en la sesión (Docente, Ayudante, Apoyo, etc.)",
        examples=["Docente", "Ayudante", "Apoyo", "Tutor"]
    )


class ProfesorSesionCreate(ProfesorSesionBase):
    pass


class ProfesorSesionOut(ProfesorSesionBase):
    nombre: Optional[str] = Field(None)
    apellidos: Optional[str] = Field(None)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "profesor_id": 42,
                "rol_en_sesion": "Docente",
                "nombre": "Juan",
                "apellidos": "García López"
            }
        }
    )


class SesionBase(BaseModel):
    grupo_docente_id: int = Field(..., gt=0)
    aula_id: int = Field(..., gt=0)
    modalidad: ModalidadSesion = Field(...)
    tipo_recurrencia: TipoRecurrencia = Field(...)
    
    dia_semana: Optional[DiaSemana] = Field(
        None,
        description="Día de la semana (requerido si tipo_recurrencia != PUNTUAL)"
    )
    hora_inicio: Optional[time] = Field(
        None,
        description="Hora de inicio (requerido si tipo_recurrencia != PUNTUAL)",
        examples=["09:00:00", "14:30:00"]
    )
    hora_fin: Optional[time] = Field(
        None,
        description="Hora de fin (requerido si tipo_recurrencia != PUNTUAL)",
        examples=["11:00:00", "16:30:00"]
    )
    
    inicio: Optional[datetime] = Field(
        None,
        description="Fecha y hora de inicio (requerido si tipo_recurrencia == PUNTUAL)",
        examples=["2025-10-25T09:00:00", "2025-11-15T14:30:00"]
    )
    
    fin: Optional[datetime] = Field(
        None,
        description="Fecha y hora de fin (requerido si tipo_recurrencia == PUNTUAL)",
        examples=["2025-10-25T11:00:00", "2025-11-15T16:30:00"]
    )
    
    @model_validator(mode='after')
    def validate_horario_segun_tipo_recurrencia(self):
        if self.tipo_recurrencia == TipoRecurrencia.PUNTUAL:
            if not self.inicio or not self.fin:
                raise ValueError(
                    "Para sesiones puntuales, 'inicio' y 'fin' son obligatorios"
                )
            if self.dia_semana or self.hora_inicio or self.hora_fin:
                raise ValueError(
                    "Para sesiones puntuales, 'dia_semana', 'hora_inicio' y 'hora_fin' "
                    "deben estar vacíos"
                )
            if self.inicio >= self.fin:
                raise ValueError("'inicio' debe ser anterior a 'fin'")
        else:
            if not self.dia_semana or not self.hora_inicio or not self.hora_fin:
                raise ValueError(
                    f"Para sesiones {self.tipo_recurrencia.value}, 'dia_semana', "
                    "'hora_inicio' y 'hora_fin' son obligatorios"
                )
            if self.inicio or self.fin:
                raise ValueError(
                    f"Para sesiones {self.tipo_recurrencia.value}, 'inicio' y 'fin' "
                    "deben estar vacíos"
                )
            if self.hora_inicio >= self.hora_fin:
                raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        return self
    
    @model_validator(mode='after')
    def validate_horas(self) -> 'SesionBase':
        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValueError("La hora de inicio debe ser estrictamente anterior a la hora de fin")
        if self.inicio and self.fin:
            if self.inicio >= self.fin:
                raise ValueError("La fecha/hora de inicio debe ser anterior a la de fin")
        return self


class SesionCreate(SesionBase):
    profesores: List[ProfesorSesionCreate] = Field(
        default_factory=list,
        description="Lista de profesores asignados a la sesión",
    )
    temp_id: Optional[int] = Field(
        None, 
        description="ID temporal del frontend usado para mapear conflictos en simulaciones."
    )


class SesionUpdate(BaseModel):
    grupo_docente_id: Optional[int] = Field(None, gt=0)
    aula_id: Optional[int] = Field(None, gt=0)
    modalidad: Optional[ModalidadSesion] = None
    tipo_recurrencia: Optional[TipoRecurrencia] = None
    
    dia_semana: Optional[DiaSemana] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    
    inicio: Optional[datetime] = None
    fin: Optional[datetime] = None
    
    profesores: Optional[List[ProfesorSesionCreate]] = None
    
    @model_validator(mode='after')
    def validate_horario_si_se_proporciona(self):
        if self.tipo_recurrencia is not None:
            if self.tipo_recurrencia == TipoRecurrencia.PUNTUAL:
                if self.inicio is None or self.fin is None:
                    raise ValueError(
                        "Al cambiar a tipo_recurrencia=PUNTUAL, 'inicio' y 'fin' son obligatorios"
                    )
                if self.inicio >= self.fin:
                    raise ValueError("'inicio' debe ser anterior a 'fin'")
            else:
                if (self.dia_semana is None or self.hora_inicio is None or 
                    self.hora_fin is None):
                    raise ValueError(
                        f"Al cambiar a tipo_recurrencia={self.tipo_recurrencia.value}, "
                        "'dia_semana', 'hora_inicio' y 'hora_fin' son obligatorios"
                    )
                if self.hora_inicio >= self.hora_fin:
                    raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        if self.inicio and self.fin:
            if self.inicio >= self.fin:
                raise ValueError("'inicio' debe ser anterior a 'fin'")
        
        return self


class SesionOut(SesionBase):
    id: int = Field(...)
    profesores: List[ProfesorSesionOut] = Field(default_factory=list)
    conflictos: List[ConflictoOut] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "grupo_docente_id": 42,
                "aula_id": 15,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": [],
                "conflictos": []
            }
        }
    )


class SesionList(BaseModel):
    total: int = Field(
        ...,
        ge=0,
        description="Total de sesiones que cumplen los filtros (sin paginar)"
    )
    items: List[SesionOut] = Field(
        ...,
        description="Sesiones en la página actual"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Número de página actual"
    )
    size: int = Field(
        ...,
        ge=1,
        description="Tamaño de página"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 25,
                "items": [
                    {
                        "id": 1,
                        "grupo_docente_id": 42,
                        "aula_id": 15,
                        "modalidad": "presencial",
                        "tipo_recurrencia": "semanal",
                        "dia_semana": "lunes",
                        "hora_inicio": "09:00:00",
                        "hora_fin": "11:00:00",
                        "inicio": None,
                        "fin": None,
                        "profesores": []
                    }
                ],
                "page": 1,
                "size": 20
            }
        }
    )

class SesionWithConflictosOut(BaseModel):
    sesion: SesionOut
    conflictos: List[ConflictoOut]


class SesionUpdateWithId(SesionUpdate):
    id: int = Field(..., gt=0, description="ID de la sesión a actualizar")

class SesionBatchRequest(BaseModel):
    created: List[SesionCreate] = Field(default_factory=list, description="Sesiones nuevas a crear")
    updated: List[SesionUpdateWithId] = Field(default_factory=list, description="Sesiones existentes a modificar")
    deleted: List[int] = Field(default_factory=list, description="IDs de sesiones a eliminar")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "created": [{"grupo_docente_id": 1, "aula_id": 1, "modalidad": "presencial", "tipo_recurrencia": "semanal", "dia_semana": "lunes", "hora_inicio": "09:00", "hora_fin": "10:00"}],
                "updated": [{"id": 55, "aula_id": 2}],
                "deleted": [10, 11]
            }
        }
    )

class SesionBatchResponse(BaseModel):
    status: str = "success"
    created: List[SesionWithConflictosOut] = Field(default_factory=list)
    updated: List[SesionWithConflictosOut] = Field(default_factory=list)
    deleted_ids: List[int] = Field(default_factory=list)

class SesionValidationResult(BaseModel):
    valid: bool
    conflictos: List[ConflictoOut] = []