"""
Esquemas Pydantic para el flujo de horarios académicos.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from modules.docencia.schemas.grupo_docente import GrupoDocenteOut
from modules.docencia.schemas.sesion import SesionOut


class ExtractionMetadataOut(BaseModel):
    quality: str = Field(
        ...,
        description="Calidad global de la extracción (excellent, good, acceptable, etc.)",
        examples=["good", "acceptable"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confianza numérica global en la extracción (0-1)",
        examples=[0.82, 0.95],
    )
    status: str = Field(
        ...,
        description="Estado del procesamiento (completed, failed, low_quality)",
        examples=["completed"],
    )
    processing_time_seconds: float = Field(..., ge=0.0)
    page_count: int = Field(..., ge=1)
    file_size_mb: float = Field(..., ge=0.0)
    has_embedded_text: bool = Field(...)
    char_count: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)
    errors: List[str] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    pages_with_text: Optional[int] = Field(None, ge=0)


class ParsingMetadataOut(BaseModel):
    parser_name: str = Field(...)
    parser_version: Optional[str] = Field(None)
    parse_timestamp: Optional[str] = Field(None)
    parse_duration: float = Field(..., ge=0.0)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class HorarioSesionTemporal(BaseModel):
    asignatura: Optional[str] = Field(None, description="Nombre asignatura (PDF)")
    aula: Optional[str] = Field(None, description="Nombre aula (PDF)")
    dia: Optional[str] = Field(None, description="Día texto")
    hora_inicio: Optional[str] = Field(None, description="HH:MM")
    hora_fin: Optional[str] = Field(None, description="HH:MM")
    tipo: Optional[str] = Field(None, description="Tipo visual")
    grupo: Optional[str] = Field(None, description="Grupo texto")

    asignatura_id: Optional[int] = Field(None, description="ID sugerido por Matcher")
    asignatura_sugerida: Optional[str] = Field(None, description="Nombre oficial sugerido")
    match_confidence: Optional[float] = Field(0.0, description="Confianza del matching")
    match_status: Optional[str] = Field("NO_MATCH", description="Estado del matching")
    
    aula_id: Optional[int] = Field(None, description="ID aula encontrada")
    aula_nombre: Optional[str] = Field(None, description="Nombre oficial aula")

    grupo_codigo: Optional[str] = Field(None, description="Código de grupo normalizado")
    tipo_grupo: Optional[str] = Field(None, description="Tipo de grupo normalizado")
    
    texto_original: Optional[str] = Field(None, description="Para aprender alias futuros")

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "asignatura": "Fisica I",
                "asignatura_id": 15,
                "aula": "AULA 1",
                "match_confidence": 95.0
            }
        }
    )


class HorarioTablaTemporal(BaseModel):
    curso: Optional[str] = Field(None, description="Curso al que pertenece la tabla")
    periodo: Optional[str] = Field(None, description="Periodo textual asociado a la tabla")
    mencion: Optional[str] = Field(None, description="Texto de mención si aplica (p.ej. 'Mención en Física Teórica')")
    pagina: Optional[int] = Field(None, ge=0, description="Número de página del PDF donde se encuentra esta tabla")
    sesiones: List[HorarioSesionTemporal] = Field(
        default_factory=list,
        description="Sesiones extraídas de esta tabla de horario",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "curso": "1º",
                "periodo": "PRIMER CUATRIMESTRE",
                "mencion": None,
                "pagina": 2,
                "sesiones": [
                    {
                        "asignatura": "Física Básica I",
                        "aula": "AULA 4",
                        "dia": "LUNES",
                        "hora_inicio": "08:30",
                        "hora_fin": "10:30",
                        "tipo": "TEORÍA",
                        "grupo": "T1",
                    }
                ],
            }
        }
    )


class HorarioTemporalBase(BaseModel):
    titulo: Optional[str] = Field(
        None,
        description="Título original del documento de horario",
    )
    plan: Optional[str] = Field(
        None,
        description="Nombre del plan/titulación (normalmente coincide con titulo)",
    )
    periodo: Optional[str] = Field(
        None,
        description="Periodo global del horario (PRIMER CUATRIMESTRE, SEGUNDO, ANUAL, ...)",
    )
    horarios: List[HorarioTablaTemporal] = Field(
        default_factory=list,
        description="Listado de tablas de horario extraídas del PDF",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "titulo": "GRADO EN FÍSICA PRIMER CUATRIMESTRE",
                "plan": "GRADO EN FÍSICA",
                "periodo": "PRIMER CUATRIMESTRE",
                "horarios": [
                    {
                        "curso": "1º",
                        "periodo": "PRIMER CUATRIMESTRE",
                        "mencion": None,
                        "pagina": 2,
                        "sesiones": [],
                    }
                ],
            }
        }
    )


class HorarioTemporalOut(HorarioTemporalBase):
    extraction_metadata: Optional[Dict[str, Any]] = Field(None)
    parsing_metadata: Optional[Dict[str, Any]] = Field(None)


class HorarioTemporalConfirmIn(HorarioTemporalBase):
    pass


# ============================================================
#  DTO: RESPUESTA DE CONFIRMACIÓN
# ============================================================

class HorarioConfirmResponse(BaseModel):
    grupos: List[GrupoDocenteOut] = Field(
        default_factory=list,
        description="Grupos docentes creados o actualizados a partir del horario",
    )
    sesiones: List[SesionOut] = Field(
        default_factory=list,
        description="Sesiones creadas a partir del horario confirmado",
    )
    created_entities: Dict[str, int] = Field(
        default_factory=dict,
        description="Resumen de entidades creadas (p.ej. grupos, sesiones, aulas)",
        examples=[{"grupos_creados": 3, "sesiones_creadas": 24}],
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Avisos no críticos producidos durante la creación de entidades",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errores producidos durante la creación de entidades",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "grupos": [],
                "sesiones": [],
                "created_entities": {
                    "grupos_creados": 3,
                    "sesiones_creadas": 24,
                    "aulas_creadas": 1,
                },
                "warnings": [
                    "No se encontró la asignatura 'Prácticas Avanzadas' en el catálogo",
                ],
                "errors": [],
            }
        }
    )
