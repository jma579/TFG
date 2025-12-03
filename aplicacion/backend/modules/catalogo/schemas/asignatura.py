"""
Schemas Pydantic para la entidad Asignatura.

Estos modelos definen:
- Validación de entrada (tipos, rangos, formatos)
- Serialización de salida (respuestas API)
- Documentación automática (OpenAPI)
- Normalización de datos (strip, uppercase, etc.)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re

from constants.enums import Periodo, ModalidadAsignatura, Idioma, TipoAsignatura
from modules.catalogo.schemas.programa import ProgramaOut


# ============================================================
#  BASE: Campos comunes compartidos por Create/Update/Out
# ============================================================

class AsignaturaBase(BaseModel):
    """
    Schema base con campos comunes de Asignatura.
    
    Campos:
    - codigo_plan: Código único de la asignatura (1-6 chars, uppercase)
    - nombre: Nombre completo de la asignatura (1-250 chars)
    - periodo: Periodo de impartición (anual, cuatrimestral_1, cuatrimestral_2)
    - ects: Créditos ECTS (1-12, opcional)
    - modalidad: Modalidad de impartición (presencial, online, semipresencial)
    - idioma: Idioma de impartición (español, inglés, catalán)
    - english_friendly: Soporte para estudiantes extranjeros
    - activo: Estado de la asignatura (soft delete)
    """
    
    codigo_plan: str = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Código único de la asignatura en el plan de estudios",
        examples=["MAT1", "G123", "FIS101"]
    )
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="Nombre completo de la asignatura",
        examples=["Matemáticas I", "Inteligencia Artificial", "Física Cuántica"]
    )
    
    periodo: Periodo = Field(
        ...,
        description="Periodo en que se imparte la asignatura"
    )
    
    ects: Optional[int] = Field(
        None,
        ge=1,
        le=12,
        description="Créditos ECTS de la asignatura (1-12)",
        examples=[6, 3, 12]
    )
    
    modalidad: ModalidadAsignatura = Field(
        ...,
        description="Modalidad de impartición de la asignatura"
    )
    
    idioma: Idioma = Field(
        default=Idioma.ESPAÑOL,
        description="Idioma en que se imparte la asignatura"
    )
    
    english_friendly: bool = Field(
        default=False,
        description="Indica si la asignatura tiene soporte para estudiantes extranjeros"
    )
    
    activo: bool = Field(
        default=True,
        description="Indica si la asignatura está activa (soft delete)"
    )
    
    
    @field_validator('codigo_plan', mode='before')
    @classmethod
    def normalize_codigo_plan(cls, v: str) -> str:
        """
        Normalizar código de asignatura:
        1. Quitar espacios al inicio/final (strip)
        2. Convertir a mayúsculas (convención académica)
        
        IMPORTANTE: mode='before' para normalizar ANTES de validar longitud.
        
        Ejemplos:
        - "  mat1  " → "MAT1" (8 chars → 4 chars)
        - "fis101" → "FIS101"
        - "G-123" → "G-123" (preserva guiones)
        """
        if not v or not isinstance(v, str):
            return v
        
        # 1. Strip: quitar espacios al inicio/final
        v = v.strip()
        
        # 2. Uppercase: convención para códigos académicos
        v = v.upper()
        
        return v
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v: str) -> str:
        """
        Normalizar nombre de asignatura:
        1. Quitar espacios al inicio/final (strip)
        2. Colapsar espacios múltiples en uno solo
        
        IMPORTANTE: mode='before' para normalizar ANTES de validar longitud.
        
        NO se altera la capitalización para preservar:
        - Nombres propios
        - Acrónimos (IA, TIC, etc.)
        - Formato definido por el usuario
        """
        if not v or not isinstance(v, str):
            return v
        
        # 1. Strip: quitar espacios al inicio/final
        v = v.strip()
        
        # 2. Colapsar espacios múltiples: "Matemáticas   I" → "Matemáticas I"
        v = re.sub(r'\s+', ' ', v)
        
        return v


# ============================================================
#  CREATE: Schema para crear asignatura (POST)
# ============================================================

class AsignaturaCreate(AsignaturaBase):
    """
    Schema para crear una nueva asignatura.
    
    Hereda todos los campos de AsignaturaBase.
    Todos los campos son requeridos excepto:
    - ects (opcional)
    - idioma (default: español)
    - english_friendly (default: False)
    - activo (default: True)
    
    Ejemplo:
    ```json
    {
        "codigo_plan": "MAT101",
        "nombre": "Matemáticas I",
        "periodo": "cuatrimestral_1",
        "ects": 6,
        "modalidad": "presencial",
        "idioma": "español",
        "english_friendly": false,
        "activo": true
    }
    ```
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo_plan": "MAT101",
                "nombre": "Matemáticas I",
                "periodo": "cuatrimestral_1",
                "ects": 6,
                "modalidad": "presencial",
                "idioma": "español",
                "english_friendly": False,
                "activo": True
            }
        }
    )


# ============================================================
#  UPDATE: Schema para actualizar asignatura (PUT/PATCH)
# ============================================================

class AsignaturaUpdate(BaseModel):
    """
    Schema para actualizar una asignatura existente.
    
    Todos los campos son opcionales (update parcial).
    Solo se actualizan los campos proporcionados.
    
    Ejemplo (actualizar solo nombre y ECTS):
    ```json
    {
        "nombre": "Matemáticas Avanzadas I",
        "ects": 9
    }
    ```
    """
    
    codigo_plan: Optional[str] = Field(
        None,
        min_length=1,
        max_length=6,
        description="Código único de la asignatura"
    )
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        description="Nombre de la asignatura"
    )
    
    periodo: Optional[Periodo] = Field(
        None,
        description="Periodo de impartición"
    )
    
    ects: Optional[int] = Field(
        None,
        ge=1,
        le=12,
        description="Créditos ECTS (1-12)"
    )
    
    modalidad: Optional[ModalidadAsignatura] = Field(
        None,
        description="Modalidad de impartición"
    )
    
    idioma: Optional[Idioma] = Field(
        None,
        description="Idioma de impartición"
    )
    
    english_friendly: Optional[bool] = Field(
        None,
        description="Soporte para estudiantes extranjeros"
    )
    
    activo: Optional[bool] = Field(
        None,
        description="Estado activo/inactivo"
    )
    
    
    @field_validator('codigo_plan', mode='before')
    @classmethod
    def normalize_codigo_plan(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar código: strip + uppercase ANTES de validar longitud."""
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = v.upper()
        return v
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar nombre: strip + colapsar espacios ANTES de validar longitud."""
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v
    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Matemáticas Avanzadas I",
                "ects": 9
            }
        }
    )


# ============================================================
#  OUT: Schema de respuesta (GET)
# ============================================================

class AsignaturaOut(AsignaturaBase):
    """
    Schema de salida para asignatura.
    
    Incluye el ID autogenerado por la base de datos.
    Se usa en respuestas de GET, POST y PUT.
    
    Hereda todos los campos de AsignaturaBase + ID.
    """
    
    id: int = Field(
        ...,
        description="ID único autogenerado de la asignatura",
        examples=[1, 42, 123]
    )
    
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde ORM models
        json_schema_extra={
            "example": {
                "id": 1,
                "codigo_plan": "MAT101",
                "nombre": "Matemáticas I",
                "periodo": "cuatrimestral_1",
                "ects": 6,
                "modalidad": "presencial",
                "idioma": "español",
                "english_friendly": False,
                "activo": True
            }
        }
    )

class AsignaturaProgramaOut(BaseModel):
    """
    Relación entre una asignatura y un programa concreto.

    Incluye la información del programa y los metadatos de la relación
    (curso y tipo de asignatura dentro del programa).
    """

    programa: ProgramaOut = Field(
        ...,
        description="Programa / titulación al que pertenece la asignatura"
    )

    curso: Optional[int] = Field(
        None,
        description="Curso dentro del programa (1..4, o None si no aplica)",
        examples=[1, 2, None],
    )

    tipo_asignatura: Optional[TipoAsignatura] = Field(
        None,
        description="Tipo de asignatura dentro del programa (OBLIGATORIA, OPTATIVA, ...)",
    )

    model_config = ConfigDict(
        from_attributes=True,
    )



# ============================================================
#  LIST: Schema para listado paginado
# ============================================================

class AsignaturaList(BaseModel):
    """
    Schema para respuesta de listado paginado de asignaturas.
    
    Campos:
    - total: Número total de asignaturas (sin paginación)
    - items: Lista de asignaturas en la página actual
    - page: Número de página actual (basado en skip/limit)
    - size: Tamaño de página (limit)
    
    Ejemplo:
    ```json
    {
        "total": 45,
        "items": [...],
        "page": 2,
        "size": 10
    }
    ```
    """
    
    total: int = Field(
        ...,
        ge=0,
        description="Número total de asignaturas (sin aplicar paginación)"
    )
    
    items: list[AsignaturaOut] = Field(
        ...,
        description="Lista de asignaturas en la página actual"
    )
    
    page: int = Field(
        ...,
        ge=1,
        description="Número de página actual"
    )
    
    size: int = Field(
        ...,
        ge=1,
        description="Tamaño de página (número de items por página)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 45,
                "items": [
                    {
                        "id": 1,
                        "codigo_plan": "MAT101",
                        "nombre": "Matemáticas I",
                        "periodo": "cuatrimestral_1",
                        "ects": 6,
                        "modalidad": "presencial",
                        "idioma": "español",
                        "english_friendly": False,
                        "activo": True
                    }
                ],
                "page": 1,
                "size": 10
            }
        }
    )