"""
Schemas Pydantic para la entidad Programa.

Estos modelos definen:
- Validación de entrada (tipos, rangos, formatos)
- Serialización de salida (respuestas API)
- Documentación automática (OpenAPI)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re

from backend.constants.enums import TipoPrograma


# ============================================================
#  BASE: Campos comunes compartidos por Create/Update/Out
# ============================================================

class ProgramaBase(BaseModel):
    """
    Schema base con campos comunes de Programa.
    
    Se usa como clase padre para evitar duplicación de código.
    """
    nombre: str = Field(
        ...,  # Campo requerido
        min_length=1,
        max_length=200,
        description="Nombre del programa académico",
        examples=["Grado en Matemáticas", "Máster en Inteligencia Artificial"]
    )
    tipo: TipoPrograma = Field(
        ...,
        description="Tipo de programa (GRADO, MASTER, DOCTORADO, DOBLE_GRADO)"
    )
    activo: bool = Field(
        default=True,
        description="Indica si el programa está activo"
    )

    @field_validator('nombre')
    @classmethod
    def normalize_nombre(cls, v: str) -> str:
        """
        Normalizar nombre:
        1. Quitar espacios al inicio/final (strip)
        2. Colapsar espacios múltiples a uno solo
        3. Convertir a Title Case para consistencia
        """
        if not v:
            return v
        
        # 1. Strip
        v = v.strip()
        
        # 2. Colapsar espacios: "Grado  en   Física" → "Grado en Física"
        v = re.sub(r'\s+', ' ', v)
        
        return v


# ============================================================
#  CREATE: Schema para POST (sin ID)
# ============================================================

class ProgramaCreate(ProgramaBase):
    """
    Schema para crear un nuevo programa.
    
    Hereda todos los campos de ProgramaBase.
    No incluye 'id' porque lo genera la base de datos.
    
    Ejemplo request:
    {
        "nombre": "Grado en Física",
        "tipo": "GRADO",
        "activo": true
    }
    """
    pass


# ============================================================
#  UPDATE: Schema para PUT (campos opcionales)
# ============================================================

class ProgramaUpdate(BaseModel):
    """
    Schema para actualizar un programa existente.
    
    TODOS los campos son opcionales para permitir actualizaciones parciales.
    Si un campo no se envía, mantiene su valor actual.
    
    Ejemplo request (solo actualizar nombre):
    {
        "nombre": "Grado en Física Aplicada"
    }
    """
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nuevo nombre del programa"
    )
    tipo: Optional[TipoPrograma] = Field(
        None,
        description="Nuevo tipo de programa"
    )
    activo: Optional[bool] = Field(
        None,
        description="Nuevo estado del programa"
    )


# ============================================================
#  OUT: Schema para respuestas GET/POST/PUT
# ============================================================

class ProgramaOut(ProgramaBase):
    """
    Schema de salida para programas.
    
    Incluye el ID generado por la base de datos.
    Se usa en respuestas de:
    - GET /programas/{id}
    - POST /programas
    - PUT /programas/{id}
    
    Ejemplo response:
    {
        "id": 1,
        "nombre": "Grado en Matemáticas",
        "tipo": "GRADO",
        "activo": true
    }
    """
    id: int = Field(
        ...,
        description="Identificador único del programa"
    )
    
    # Configuración para trabajar con objetos SQLAlchemy
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde objetos ORM
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Grado en Matemáticas",
                "tipo": "GRADO",
                "activo": True
            }
        }
    )


# ============================================================
#  LIST: Schema para listados paginados
# ============================================================

class ProgramaList(BaseModel):
    """
    Schema para respuestas de listados con paginación.
    
    Incluye:
    - total: número total de registros (sin paginar)
    - items: lista de programas de la página actual
    - page: número de página actual
    - size: tamaño de página
    
    Ejemplo response:
    {
        "total": 25,
        "items": [
            {"id": 1, "nombre": "Grado Mat", "tipo": "GRADO", "activo": true},
            {"id": 2, "nombre": "Máster IA", "tipo": "MASTER", "activo": true}
        ],
        "page": 1,
        "size": 10
    }
    """
    total: int = Field(
        ...,
        ge=0,
        description="Número total de registros (sin paginar)"
    )
    items: list[ProgramaOut] = Field(
        ...,
        description="Lista de programas de la página actual"
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