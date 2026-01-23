from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime

from constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto

# 1. Definimos el sub-schema para los detalles
class SesionResumen(BaseModel):
    id: int
    asignatura: str = "Desconocida"
    grupo: str = "?"
    horario: str = "Sin horario"
    curso: str = "-"

class ConflictoBase(BaseModel):
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    estado: EstadoConflicto
    descripcion: str

class ConflictoEstadoUpdateIn(BaseModel):
    estado: EstadoConflicto

class ConflictoOut(ConflictoBase):
    id: int
    sesion_id: int = Field(..., description="ID de la sesión principal afectada")
    sesion_2_id: Optional[int] = Field(None, description="ID de la segunda sesión en conflicto (si existe)")
    
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    restriccion_id: Optional[int] = None
    
    # --- 2. CAMPOS NUEVOS NECESARIOS ---
    # Usamos validation_alias para mapear la relación ORM "sesion" al campo JSON "sesion_1_detalle"
    sesion_1_detalle: Optional[SesionResumen] = Field(None, validation_alias="sesion")
    sesion_2_detalle: Optional[SesionResumen] = Field(None, validation_alias="sesion_2")
    
    hash_deteccion: str
    creado_en: datetime
    resuelto_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    # --- 3. VALIDADOR PARA APLANAR EL OBJETO ORM ---
    @field_validator("sesion_1_detalle", "sesion_2_detalle", mode="before")
    @classmethod
    def transform_sesion_orm(cls, v):
        """
        Convierte el objeto ORM Sesion (cargado con joinedload) en SesionResumen.
        """
        if not v: return None
        
        # Extracción segura de datos relacionales
        asig = "Desconocida"
        grp = "?"
        curso = "-"
        horario = "Sin horario"

        # Navegamos por las relaciones ya cargadas en memoria
        if hasattr(v, "grupo_docente") and v.grupo_docente:
            if v.grupo_docente.asignatura:
                asig = v.grupo_docente.asignatura.nombre
            
            tipo = v.grupo_docente.tipo.value if v.grupo_docente.tipo else "TEORIA"
            cod = v.grupo_docente.codigo or "UNICO"
            grp = f"{tipo} ({cod})"
            curso = f"{v.grupo_docente.curso}º" if v.grupo_docente.curso else "Optativa"
            
        if hasattr(v, "dia_semana") and v.dia_semana:
            dia = v.dia_semana.value.capitalize()
            ini = v.hora_inicio.strftime("%H:%M") if v.hora_inicio else "??"
            fin = v.hora_fin.strftime("%H:%M") if v.hora_fin else "??"
            horario = f"{dia} {ini}-{fin}"
            
        return SesionResumen(
            id=v.id,
            asignatura=asig,
            grupo=grp,
            horario=horario,
            curso=curso
        )

class ConflictoList(BaseModel):
    total: int
    items: List[ConflictoOut]
    page: int
    size: int