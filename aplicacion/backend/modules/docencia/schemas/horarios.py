"""
Esquemas Pydantic para el flujo de horarios académicos.

Define los contratos de datos para:
- HorarioTemporalOut: horario extraído y listo para editar en el frontend
- HorarioTemporalConfirmIn: horario corregido que envía el frontend para confirmar
- HorarioConfirmResponse: resumen de los grupos y sesiones creados en BD
- Metadatos de extracción/parsing: diagnóstico de calidad del proceso

IMPORTANTE:
- Estos DTOs representan el estado *temporal* del horario (salida del parser).
- La validación fuerte (enums, horas, recurrencias) se realiza después, en:
  - HorarioDataNormalizer (normalización a dominio)
  - Schemas de Sesion (SesionBase, SesionCreate, etc.)

Por tanto, aquí usamos validaciones ligeras y tipos sencillos (str) para:
- Facilitar la edición desde el frontend
- No duplicar la lógica compleja que ya existe en el normalizador y en Sesion.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from modules.docencia.schemas.grupo_docente import GrupoDocenteOut
from modules.docencia.schemas.sesion import SesionOut


# ============================================================
#  METADATOS DE EXTRACCIÓN Y PARSING
# ============================================================

class ExtractionMetadataOut(BaseModel):
    """Metadatos sobre la extracción del PDF de horario.

    Refleja el resultado del extractor (calidad del texto, tamaño, páginas, etc.).
    Es útil para mostrar información de diagnóstico en el frontend.
    """

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
    processing_time_seconds: float = Field(
        ...,
        ge=0.0,
        description="Tiempo total de procesamiento del PDF en segundos",
        examples=[1.23, 3.5],
    )
    page_count: int = Field(
        ...,
        ge=1,
        description="Número de páginas del PDF",
        examples=[2, 5],
    )
    file_size_mb: float = Field(
        ...,
        ge=0.0,
        description="Tamaño del archivo en MB",
        examples=[0.4, 2.1],
    )
    has_embedded_text: bool = Field(
        ...,
        description="Indica si el PDF contenía texto embebido (no solo imagen)",
    )
    char_count: int = Field(
        ...,
        ge=0,
        description="Número total aproximado de caracteres extraídos",
    )
    word_count: int = Field(
        ...,
        ge=0,
        description="Número total aproximado de palabras extraídas",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Lista de mensajes de error producidos durante la extracción",
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de avisos con información adicional (mensaje, severidad, contexto)",
    )
    pages_with_text: Optional[int] = Field(
        None,
        ge=0,
        description="Número de páginas con texto útil detectado (si está disponible)",
    )


class ParsingMetadataOut(BaseModel):
    """Metadatos sobre el proceso de parsing de las tablas de horario.

    Incluye información de diagnóstico como duración, versión del parser,
    avisos y errores detectados durante el análisis.
    """

    parser_name: str = Field(
        ...,
        description="Nombre del parser que ha procesado el documento",
        examples=["HorarioParser"],
    )
    parser_version: Optional[str] = Field(
        None,
        description="Versión del parser usada para el análisis",
        examples=["0.1.0"],
    )
    parse_timestamp: Optional[str] = Field(
        None,
        description="Marca de tiempo del parseo en formato ISO 8601",
        examples=["2025-11-18T10:15:30Z"],
    )
    parse_duration: float = Field(
        ...,
        ge=0.0,
        description="Duración del proceso de parsing en segundos",
        examples=[0.45, 1.2],
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Avisos generados durante el parsing (mensaje, severidad, contexto)",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errores detectados durante el parsing (si los hay)",
    )


# ============================================================
#  DTO: SESIONES Y TABLAS TEMPORALES (EDITABLES)
# ============================================================

class HorarioSesionTemporal(BaseModel):
    """Sesión tal como se representa en el horario temporal editable.

    Corresponde a la salida del parser para una celda de horario ya interpretada.
    Estos campos se editan directamente en el frontend antes de la confirmación.

    Campos:
        - asignatura: Nombre de la asignatura tal y como aparece en el horario
        - aula: Nombre del aula (p.ej. "AULA 4", "LAB 2", "LSC 1")
        - dia: Día de la semana en texto ("LUNES", "MARTES", ...)
        - hora_inicio: Hora de inicio en formato "HH:MM"
        - hora_fin: Hora de fin en formato "HH:MM"
        - tipo: Tipo de sesión textual ("TEORÍA", "PRÁCTICA", ...)
        - grupo: Código de grupo textual ("PL1", "PA2", "T1", ...)
    """

    # --- Datos Crudos (Tal cual vienen del PDF) ---
    asignatura: Optional[str] = Field(None, description="Nombre asignatura (PDF)")
    aula: Optional[str] = Field(None, description="Nombre aula (PDF)")
    dia: Optional[str] = Field(None, description="Día texto")
    hora_inicio: Optional[str] = Field(None, description="HH:MM")
    hora_fin: Optional[str] = Field(None, description="HH:MM")
    tipo: Optional[str] = Field(None, description="Tipo visual")
    grupo: Optional[str] = Field(None, description="Grupo texto")

    # --- Campos Técnicos de Matching (NECESARIOS PARA EL NUEVO MOTOR) ---
    # Asignatura
    asignatura_id: Optional[int] = Field(None, description="ID sugerido por Matcher")
    asignatura_sugerida: Optional[str] = Field(None, description="Nombre oficial sugerido")
    match_confidence: Optional[float] = Field(0.0, description="Confianza del matching")
    match_status: Optional[str] = Field("NO_MATCH", description="Estado del matching")
    
    # Aula
    aula_id: Optional[int] = Field(None, description="ID aula encontrada")
    aula_nombre: Optional[str] = Field(None, description="Nombre oficial aula")

    # Normalización (Para no perder el trabajo del normalizador)
    grupo_codigo: Optional[str] = Field(None, description="Código de grupo normalizado")
    tipo_grupo: Optional[str] = Field(None, description="Tipo de grupo normalizado")
    
    # Aprendizaje
    texto_original: Optional[str] = Field(None, description="Para aprender alias futuros")

    model_config = ConfigDict(
        extra="ignore", # Ignora campos extra si el parser antiguo enviara basura
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
    """Tabla de horario tal como se extrae de una página/curso del PDF.

    Representa un bloque de horario (normalmente una combinación de curso,
    mención y página) con todas sus sesiones asociadas.
    """

    curso: Optional[str] = Field(
        None,
        description="Curso al que pertenece la tabla (p.ej. '1º', '2º', '3º')",
        examples=["1º", "2º"],
    )
    periodo: Optional[str] = Field(
        None,
        description="Periodo textual asociado a la tabla (si difiere del global)",
        examples=["PRIMER CUATRIMESTRE", "ANUAL"],
    )
    mencion: Optional[str] = Field(
        None,
        description="Texto de mención si aplica (p.ej. 'Mención en Física Teórica')",
    )
    pagina: Optional[int] = Field(
        None,
        ge=0,
        description="Número de página del PDF donde se encuentra esta tabla",
        examples=[2, 3],
    )
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


# ============================================================
#  DTO: HORARIO COMPLETO (TEMPORAL)
# ============================================================

class HorarioTemporalBase(BaseModel):
    """Estructura base de un horario temporal.

    Agrupa toda la información extraída del PDF en un único objeto:
    - título/plan del documento
    - periodo global
    - lista de tablas de horario con sus sesiones.

    Este modelo se usa tanto para la respuesta de extracción como para la
    petición de confirmación (tras edición en el frontend).
    """

    titulo: Optional[str] = Field(
        None,
        description="Título original del documento de horario",
        examples=["GRADO EN FÍSICA PRIMER CUATRIMESTRE"],
    )
    plan: Optional[str] = Field(
        None,
        description="Nombre del plan/titulación (normalmente coincide con titulo)",
        examples=["GRADO EN FÍSICA"],
    )
    periodo: Optional[str] = Field(
        None,
        description="Periodo global del horario (PRIMER CUATRIMESTRE, SEGUNDO, ANUAL, ...)",
        examples=["PRIMER CUATRIMESTRE"],
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
    """Respuesta completa del endpoint de extracción de horarios.

    Por ahora, los metadatos se exponen como dicts genéricos para no acoplar
    demasiado el contrato de la API a la implementación interna del parser.
    """

    extraction_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos crudos de la extracción del PDF de horario",
    )
    parsing_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos crudos del proceso de parsing de tablas",
    )


class HorarioTemporalConfirmIn(HorarioTemporalBase):
    """Payload de entrada para confirmar un horario editado.

    El frontend envía este objeto tras permitir al usuario revisar y modificar
    las sesiones extraídas. A partir de estos datos se reconstruirá una
    estructura equivalente a ParsingResult para alimentar al normalizador.
    """

    # Por ahora no añadimos campos extra; si en el futuro quieres flags
    # (p.ej. "crear_asignaturas_si_no_existen"), este es el lugar.
    pass


# ============================================================
#  DTO: RESPUESTA DE CONFIRMACIÓN
# ============================================================

class HorarioConfirmResponse(BaseModel):
    """Respuesta del endpoint de confirmación de horario.

    Resume el resultado de la normalización y persistencia en BD:
    - grupos: grupos docentes creados o afectados
    - sesiones: sesiones creadas
    - created_entities: contadores auxiliares (grupos, sesiones, aulas, ...)
    - warnings/errors: mensajes relevantes del proceso
    """

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
