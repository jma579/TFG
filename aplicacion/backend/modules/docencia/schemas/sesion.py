"""
Esquemas Pydantic para la entidad Sesion.

Define los contratos de datos para:
- Entrada: SesionCreate, SesionUpdate
- Salida: SesionOut, SesionList
- Relación M:N: ProfesorSesionCreate, ProfesorSesionOut
- Validaciones: horarios duales (semanal vs puntual), FK constraints

Responsabilidades:
- Validar tipos de datos (Pydantic automático)
- Validar horarios según tipo_recurrencia (campos mutuamente excluyentes)
- Validar rangos horarios (hora_inicio < hora_fin, inicio < fin)
- Convertir modelos SQLAlchemy a JSON (SesionOut)
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import time, datetime

from constants.enums import (
    ModalidadSesion, TipoRecurrencia, DiaSemana
)
from modules.conflictos.schemas.conflicto import ConflictoOut



# ============================================================
#  SCHEMAS: Relación M:N con Profesor (ProfesorSesion)
# ============================================================

class ProfesorSesionBase(BaseModel):
    """
    Schema base para la relación Profesor-Sesion.
    
    Representa la asignación de un profesor a una sesión con un rol opcional.
    """
    
    profesor_id: int = Field(
        ...,
        gt=0,
        description="ID del profesor asignado a la sesión",
        examples=[1, 42, 123]
    )
    
    rol_en_sesion: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Rol del profesor en la sesión (Docente, Ayudante, Apoyo, etc.)",
        examples=["Docente", "Ayudante", "Apoyo", "Tutor"]
    )


class ProfesorSesionCreate(ProfesorSesionBase):
    """
    Schema para asignar un profesor a una sesión (creación).
    
    Usado en SesionCreate.profesores para asignar múltiples profesores.
    """
    pass


class ProfesorSesionOut(ProfesorSesionBase):
    """
    Schema de respuesta para la relación Profesor-Sesion.
    
    Incluye datos básicos del profesor para evitar consultas adicionales.
    """
    
    # Datos del profesor (populated desde la relación)
    nombre: Optional[str] = Field(None, description="Nombre del profesor")
    apellidos: Optional[str] = Field(None, description="Apellidos del profesor")
    
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


# ============================================================
#  SCHEMAS: Sesion (horarios duales)
# ============================================================

class SesionBase(BaseModel):
    """
    Schema base para Sesion con campos comunes.
    
    IMPORTANTE: Los campos de horario son mutuamente excluyentes según tipo_recurrencia:
    
    - SEMANAL/QUINCENAL/MENSUAL: Requiere dia_semana + hora_inicio + hora_fin
    - PUNTUAL: Requiere inicio + fin (DateTime)
    
    Campos:
        - grupo_docente_id: ID del grupo docente (FK obligatorio)
        - aula_id: ID del aula (FK obligatorio)
        - modalidad: Modalidad de la sesión (PRESENCIAL, ONLINE, HIBRIDA)
        - tipo_recurrencia: Tipo de recurrencia (SEMANAL, QUINCENAL, MENSUAL, PUNTUAL)
        - dia_semana: Día de la semana (solo si recurrente)
        - hora_inicio: Hora de inicio (solo si recurrente)
        - hora_fin: Hora de fin (solo si recurrente)
        - inicio: Fecha y hora de inicio (solo si puntual)
        - fin: Fecha y hora de fin (solo si puntual)
    """
    
    grupo_docente_id: int = Field(
        ...,
        gt=0,
        description="ID del grupo docente al que pertenece la sesión",
        examples=[1, 42, 123]
    )
    
    aula_id: int = Field(
        ...,
        gt=0,
        description="ID del aula donde se imparte la sesión",
        examples=[1, 15, 200]
    )
    
    modalidad: ModalidadSesion = Field(
        ...,
        description="Modalidad de la sesión"
    )
    
    tipo_recurrencia: TipoRecurrencia = Field(
        ...,
        description="Tipo de recurrencia de la sesión"
    )
    
    # ============================================================
    #  CAMPOS HORARIO SEMANAL (recurrente)
    # ============================================================
    
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
    
    # ============================================================
    #  CAMPOS HORARIO PUNTUAL (fecha específica)
    # ============================================================
    
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
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @model_validator(mode='after')
    def validate_horario_segun_tipo_recurrencia(self):
        """
        Validar que los campos de horario correctos estén presentes según tipo_recurrencia.
        
        Reglas:
        - SEMANAL/QUINCENAL/MENSUAL: Requiere dia_semana + hora_inicio + hora_fin
        - PUNTUAL: Requiere inicio + fin
        - Los campos del tipo NO usado deben estar vacíos
        """
        if self.tipo_recurrencia == TipoRecurrencia.PUNTUAL:
            # Validar horario puntual
            if not self.inicio or not self.fin:
                raise ValueError(
                    "Para sesiones puntuales, 'inicio' y 'fin' son obligatorios"
                )
            
            # Validar que campos de recurrente estén vacíos
            if self.dia_semana or self.hora_inicio or self.hora_fin:
                raise ValueError(
                    "Para sesiones puntuales, 'dia_semana', 'hora_inicio' y 'hora_fin' "
                    "deben estar vacíos"
                )
            
            # Validar rango de fechas
            if self.inicio >= self.fin:
                raise ValueError("'inicio' debe ser anterior a 'fin'")
        
        else:
            # Validar horario recurrente (SEMANAL, QUINCENAL, MENSUAL)
            if not self.dia_semana or not self.hora_inicio or not self.hora_fin:
                raise ValueError(
                    f"Para sesiones {self.tipo_recurrencia.value}, 'dia_semana', "
                    "'hora_inicio' y 'hora_fin' son obligatorios"
                )
            
            # Validar que campos de puntual estén vacíos
            if self.inicio or self.fin:
                raise ValueError(
                    f"Para sesiones {self.tipo_recurrencia.value}, 'inicio' y 'fin' "
                    "deben estar vacíos"
                )
            
            # Validar rango horario
            if self.hora_inicio >= self.hora_fin:
                raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        return self


class SesionCreate(SesionBase):
    """
    Schema para crear una sesión.
    
    Incluye lista de profesores a asignar.
    
    Validaciones adicionales en service layer:
    - grupo_docente_id debe existir (FK)
    - aula_id debe existir (FK)
    - Todos los profesor_id en profesores deben existir
    - TODO: Detectar conflictos de horarios
    
    Ejemplo (sesión semanal):
    {
        "grupo_docente_id": 42,
        "aula_id": 15,
        "modalidad": "presencial",
        "tipo_recurrencia": "semanal",
        "dia_semana": "lunes",
        "hora_inicio": "09:00:00",
        "hora_fin": "11:00:00",
        "profesores": [
            {"profesor_id": 10, "rol_en_sesion": "Docente"},
            {"profesor_id": 20, "rol_en_sesion": "Ayudante"}
        ]
    }
    
    Ejemplo (sesión puntual):
    {
        "grupo_docente_id": 42,
        "aula_id": 15,
        "modalidad": "online",
        "tipo_recurrencia": "puntual",
        "inicio": "2025-10-25T09:00:00",
        "fin": "2025-10-25T11:00:00",
        "profesores": [
            {"profesor_id": 10, "rol_en_sesion": "Docente"}
        ]
    }
    """
    
    profesores: List[ProfesorSesionCreate] = Field(
        default_factory=list,
        description="Lista de profesores asignados a la sesión",
        examples=[
            [
                {"profesor_id": 10, "rol_en_sesion": "Docente"},
                {"profesor_id": 20, "rol_en_sesion": "Ayudante"}
            ]
        ]
    )

    # Campo opcional para rastrear sesiones temporales en simulaciones
    temp_id: Optional[int] = Field(
        None, 
        description="ID temporal del frontend (ej: -123) usado para mapear conflictos en simulaciones."
    )


class SesionUpdate(BaseModel):
    """
    Schema para actualizar una sesión (actualización parcial).
    
    Todos los campos son opcionales.
    Solo se actualizan los campos proporcionados (exclude_unset=True).
    
    IMPORTANTE: Si se cambia tipo_recurrencia, los campos de horario deben actualizarse
    en conjunto (no se puede tener tipo_recurrencia=PUNTUAL con dia_semana presente).
    
    Validación de horarios se hará en el @model_validator si se proporcionan campos.
    """
    
    grupo_docente_id: Optional[int] = Field(None, gt=0)
    aula_id: Optional[int] = Field(None, gt=0)
    modalidad: Optional[ModalidadSesion] = None
    tipo_recurrencia: Optional[TipoRecurrencia] = None
    
    # Horario recurrente
    dia_semana: Optional[DiaSemana] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    
    # Horario puntual
    inicio: Optional[datetime] = None
    fin: Optional[datetime] = None
    
    # Profesores (reemplaza la lista completa)
    profesores: Optional[List[ProfesorSesionCreate]] = None
    
    @model_validator(mode='after')
    def validate_horario_si_se_proporciona(self):
        """
        Validar horarios solo si se proporcionan campos relacionados.
        
        Si se actualiza tipo_recurrencia, validar que los campos correctos estén presentes.
        """
        # Solo validar si tipo_recurrencia se proporciona
        if self.tipo_recurrencia is not None:
            if self.tipo_recurrencia == TipoRecurrencia.PUNTUAL:
                # Si cambia a PUNTUAL, inicio y fin son requeridos
                if self.inicio is None or self.fin is None:
                    raise ValueError(
                        "Al cambiar a tipo_recurrencia=PUNTUAL, 'inicio' y 'fin' son obligatorios"
                    )
                if self.inicio >= self.fin:
                    raise ValueError("'inicio' debe ser anterior a 'fin'")
            else:
                # Si cambia a recurrente, campos recurrentes son requeridos
                if (self.dia_semana is None or self.hora_inicio is None or 
                    self.hora_fin is None):
                    raise ValueError(
                        f"Al cambiar a tipo_recurrencia={self.tipo_recurrencia.value}, "
                        "'dia_semana', 'hora_inicio' y 'hora_fin' son obligatorios"
                    )
                if self.hora_inicio >= self.hora_fin:
                    raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        # Validar rangos si se proporcionan (sin cambiar tipo_recurrencia)
        if self.hora_inicio and self.hora_fin:
            if self.hora_inicio >= self.hora_fin:
                raise ValueError("'hora_inicio' debe ser anterior a 'hora_fin'")
        
        if self.inicio and self.fin:
            if self.inicio >= self.fin:
                raise ValueError("'inicio' debe ser anterior a 'fin'")
        
        return self


class SesionOut(SesionBase):
    """
    Schema para respuestas de Sesion (incluye ID, profesores y CONFLICTOS).
    """
    
    id: int = Field(
        ...,
        description="ID único de la sesión (autogenerado)"
    )
    
    profesores: List[ProfesorSesionOut] = Field(
        default_factory=list,
        description="Lista de profesores asignados a la sesión"
    )

    conflictos: List[ConflictoOut] = Field(
        default_factory=list,
        description="Lista de conflictos activos asociados a esta sesión"
    )
    
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
    """
    Schema para respuestas de listado paginado.
    
    Usado en: GET /sesiones (lista con paginación)
    """
    
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


# === NUEVO: Schemas para Batch Update ===

class SesionUpdateWithId(SesionUpdate):
    """
    SesionUpdate que incluye el ID obligatorio.
    Necesario para identificar qué sesión actualizar en una lista.
    """
    id: int = Field(..., gt=0, description="ID de la sesión a actualizar")

class SesionBatchRequest(BaseModel):
    """
    Payload para procesar cambios masivos en una sola transacción.
    """
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
    """
    Respuesta estructurada para operaciones en lote.
    Devuelve las entidades completas (con sus conflictos) para que el frontend
    pueda actualizar el estado visual (ej: pintar de rojo) sin recargar.
    """
    status: str = "success"
    created: List[SesionWithConflictosOut] = Field(default_factory=list)
    updated: List[SesionWithConflictosOut] = Field(default_factory=list)
    deleted_ids: List[int] = Field(default_factory=list)

class SesionValidationResult(BaseModel):
    """
    Respuesta de la simulación de cambios.
    Devuelve si el cambio es válido y la lista de conflictos que generaría.
    """
    valid: bool
    conflictos: List[ConflictoOut] = []