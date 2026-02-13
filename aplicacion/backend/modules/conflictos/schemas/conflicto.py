"""
Schemas Pydantic para el módulo de conflictos.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime

from constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto

class SesionResumen(BaseModel):
    id: int
    asignatura: str = "Desconocida"
    grupo: str = "?"
    horario: str = "Sin horario"
    curso: str = "-"
    aula: Optional[str] = None
    titulacion: Optional[str] = None
    mencion: Optional[str] = None
    periodo: Optional[str] = None
    programa_id: Optional[int] = None
    curso_num: Optional[int] = None
    periodo_code: Optional[str] = None

class ConflictoBase(BaseModel):
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    estado: EstadoConflicto
    descripcion: str

class ConflictoEstadoUpdateIn(BaseModel):
    estado: EstadoConflicto

class ConflictoOut(ConflictoBase):
    id: int
    sesion_id: int = Field(...)
    sesion_2_id: Optional[int] = Field(None)
    
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    restriccion_id: Optional[int] = None
    
    sesion_1_detalle: Optional[SesionResumen] = Field(None, validation_alias="sesion")
    sesion_2_detalle: Optional[SesionResumen] = Field(None, validation_alias="sesion_2")
    
    hash_deteccion: str
    creado_en: datetime
    resuelto_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sesion_1_detalle", "sesion_2_detalle", mode="before")
    @classmethod
    def transform_sesion_orm(cls, v):
        if not v: return None
        
        asig = "Desconocida"
        grp = "?"
        curso_str = "-"
        horario = "Sin horario"
        aula_nombre = v.aula.nombre if v.aula else "Sin Aula"
        titulacion = None
        mencion = None
        
        periodo_str = None
        periodo_code = None
        programa_id = None
        curso_num = None

        if hasattr(v, "grupo_docente") and v.grupo_docente:
            tipo = v.grupo_docente.tipo.value if v.grupo_docente.tipo else "TEORIA"
            cod = v.grupo_docente.codigo or "UNICO"
            grp = f"{tipo} ({cod})"
            
            curso_val = v.grupo_docente.curso
            curso_num = curso_val
            curso_str = f"{curso_val}º" if curso_val else "Optativa"
            
            if v.grupo_docente.asignatura:
                asig_obj = v.grupo_docente.asignatura
                asig = asig_obj.nombre
                
                if asig_obj.periodo:
                    periodo_code = asig_obj.periodo.value 
                    periodo_str = asig_obj.periodo.value.replace("_", " ").title()
                
                target_pa = None
                if asig_obj.programa_asignaturas:
                    for pa in asig_obj.programa_asignaturas:
                        if pa.curso == curso_val:
                            target_pa = pa
                            break
                    if not target_pa and len(asig_obj.programa_asignaturas) > 0:
                        target_pa = asig_obj.programa_asignaturas[0]
                
                if target_pa:
                    if target_pa.programa:
                        titulacion = target_pa.programa.nombre
                        programa_id = target_pa.programa.id
                    if target_pa.mencion:
                        mencion = target_pa.mencion.nombre

        if hasattr(v, "dia_semana") and v.dia_semana:
            try:
                dia = v.dia_semana.value.capitalize()
            except:
                dia = str(v.dia_semana)
            ini = v.hora_inicio.strftime("%H:%M") if v.hora_inicio else "??"
            fin = v.hora_fin.strftime("%H:%M") if v.hora_fin else "??"
            horario = f"{dia} {ini}-{fin}"
            
        return SesionResumen(
            id=v.id,
            asignatura=asig,
            grupo=grp,
            horario=horario,
            curso=curso_str,
            aula=aula_nombre,
            titulacion=titulacion,
            mencion=mencion,
            periodo=periodo_str,
            
            programa_id=programa_id,
            curso_num=curso_num,
            periodo_code=periodo_code
        )

class ConflictoList(BaseModel):
    total: int
    items: List[ConflictoOut]
    page: int
    size: int