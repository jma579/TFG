"""
Esquemas Pydantic para la entidad GrupoDocente.

Define los contratos de datos para:
- Entrada: GrupoDocenteCreate, GrupoDocenteUpdate
- Salida: GrupoDocenteOut, GrupoDocenteList
- Validaciones: unicidad compuesta (asignatura_id, codigo), normalización

Responsabilidades:
- Validar tipos de datos (Pydantic automático)
- Normalizar texto (strip, colapsar espacios, uppercase código)
- Validar reglas de negocio (FK asignatura_id > 0)
- Convertir modelos SQLAlchemy a JSON (GrupoDocenteOut)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List

from constants.enums import TipoGrupoDocente


# ============================================================
#  HELPERS: Validadores reutilizables
# ============================================================

def normalize_texto(value: Optional[str]) -> Optional[str]:
    """
    Normalizar texto: trim + colapsar múltiples espacios.
    
    Ejemplos:
        "  Grupo   A  " → "Grupo A"
        None → None
    """
    if value is None:
        return None
    
    # Strip + reemplazar múltiples espacios por uno solo
    normalized = " ".join(value.strip().split())
    return normalized if normalized else None


# ============================================================
#  SCHEMAS: Base y derivados
# ============================================================

class GrupoDocenteBase(BaseModel):
    """
    Schema base para GrupoDocente con campos comunes.
    
    Campos:
        - asignatura_id: ID de la asignatura (FK obligatorio)
        - codigo: Código del grupo (único por asignatura)
        - tipo: Tipo de grupo (TEORIA, PRACTICA, LABORATORIO, etc.)
        - curso: Curso académico del grupo (1, 2, 3, 4, opcional)
        - turno: Turno del grupo (mañana, tarde, noche, opcional)
    """
    
    asignatura_id: int = Field(
        ...,
        gt=0,
        description="ID de la asignatura a la que pertenece el grupo",
        examples=[1, 42, 123]
    )
    
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código único del grupo dentro de la asignatura (ej: A, B, L1, T1)",
        examples=["A", "B", "T1", "L1", "P2", "TEORIA-M"]
    )
    
    tipo: TipoGrupoDocente = Field(
        ...,
        description="Tipo de grupo docente"
    )
    
    curso: Optional[int] = Field(
        None,
        ge=1,
        le=6,  # Máximo 6 años (doctorado)
        description="Curso académico del grupo (1=primero, 2=segundo, etc.)",
        examples=[1, 2, 3, 4]
    )
    
    turno: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Turno del grupo (mañana, tarde, noche, etc.)",
        examples=["mañana", "tarde", "noche", "M", "T"]
    )
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @field_validator("codigo", "turno", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        """Normalizar codigo y turno: trim + colapsar espacios."""
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: str) -> str:
        """
        Validar formato del código:
        - No permitir solo espacios
        - Normalizar a mayúsculas para consistencia
        """
        if not value or not value.strip():
            raise ValueError("El código no puede estar vacío")
        
        return value.upper()  # Normalizar a mayúsculas


class GrupoDocenteCreate(GrupoDocenteBase):
    """
    Schema para crear un grupo docente.
    
    Hereda todos los campos de GrupoDocenteBase.
    
    Validaciones adicionales en service layer:
    - asignatura_id debe existir (FK)
    - (asignatura_id, codigo) debe ser único
    """
    pass


class GrupoDocenteUpdate(BaseModel):
    """
    Schema para actualizar un grupo docente (actualización parcial).
    
    Todos los campos son opcionales.
    Solo se actualizan los campos proporcionados (exclude_unset=True).
    
    Comportamiento:
    - Campo no incluido → No se modifica
    - Campo con valor → Se actualiza
    - Campo con null → Se borra (pone a None) - solo curso y turno
    
    Nota: asignatura_id, codigo y tipo NO pueden ser null (obligatorios en DB)
    """
    
    asignatura_id: Optional[int] = Field(
        None,
        gt=0,
        description="Nuevo ID de asignatura"
    )
    
    codigo: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Nuevo código del grupo"
    )
    
    tipo: Optional[TipoGrupoDocente] = Field(
        None,
        description="Nuevo tipo de grupo"
    )
    
    curso: Optional[int] = Field(
        None,
        ge=1,
        le=6,
        description="Nuevo curso (null para borrar)"
    )
    
    turno: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Nuevo turno (null para borrar)"
    )
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @field_validator("codigo", "turno", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        """Normalizar codigo y turno."""
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: Optional[str]) -> Optional[str]:
        """Validar formato del código si se proporciona."""
        if value is None:
            return None
        
        if not value.strip():
            raise ValueError("El código no puede estar vacío")
        
        return value.upper()


class GrupoDocenteOut(GrupoDocenteBase):
    """
    Schema para respuestas de GrupoDocente (incluye ID).
    
    Usado en:
    - Respuestas de endpoints GET, POST, PUT
    - Elementos de listas
    
    Incluye configuración para convertir desde modelo SQLAlchemy.
    """
    
    id: int = Field(
        ...,
        description="ID único del grupo docente (autogenerado)"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "asignatura_id": 42,
                "codigo": "T1",
                "tipo": "teoria",
                "curso": 3,
                "turno": "mañana"
            }
        }
    )


class GrupoDocenteList(BaseModel):
    """
    Schema para respuestas de listado paginado.
    
    Usado en: GET /grupos-docentes (lista con paginación)
    
    Incluye metadatos de paginación:
    - total: Total de registros (sin paginar)
    - items: Lista de grupos en la página actual
    - page: Número de página actual
    - size: Tamaño de página (limit)
    """
    
    total: int = Field(
        ...,
        ge=0,
        description="Total de grupos docentes que cumplen los filtros (sin paginar)"
    )
    
    items: List[GrupoDocenteOut] = Field(
        ...,
        description="Grupos docentes en la página actual"
    )
    
    page: int = Field(
        ...,
        ge=1,
        description="Número de página actual (basado en skip/limit)"
    )
    
    size: int = Field(
        ...,
        ge=1,
        description="Tamaño de página (número de items por página)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 15,
                "items": [
                    {
                        "id": 1,
                        "asignatura_id": 42,
                        "codigo": "T1",
                        "tipo": "teoria",
                        "curso": 3,
                        "turno": "mañana"
                    },
                    {
                        "id": 2,
                        "asignatura_id": 42,
                        "codigo": "P1",
                        "tipo": "practica",
                        "curso": 3,
                        "turno": "tarde"
                    }
                ],
                "page": 1,
                "size": 20
            }
        }
    )