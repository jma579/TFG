"""
Schemas Pydantic para la entidad Mencion.

Estos modelos definen:
- Validación de entrada (tipos, rangos, formatos)
- Serialización de salida (respuestas API)
- Documentación automática (OpenAPI)
- Normalización de datos (strip, collapse spaces)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
import re


# ============================================================
#  BASE: Campos comunes compartidos por Create/Update/Out
# ============================================================

class MencionBase(BaseModel):
    """
    Schema base con campos comunes de Mencion.
    
    Campos:
    - programa_id: ID del programa al que pertenece la mención
    - nombre: Nombre de la mención (1-200 chars)
    - activo: Estado de la mención (soft delete)
    
    Constraint de unicidad:
    - (programa_id, nombre): Una mención con el mismo nombre puede existir
      en diferentes programas, pero no puede repetirse dentro del mismo programa
    """
    
    programa_id: int = Field(
        ...,
        gt=0,
        description="ID del programa al que pertenece la mención",
        examples=[1, 5, 10]
    )
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre de la mención",
        examples=[
            "Ingeniería del Software",
            "Inteligencia Artificial",
            "Computación y Sistemas Inteligentes"
        ]
    )
    
    activo: bool = Field(
        default=True,
        description="Indica si la mención está activa (soft delete)"
    )
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v):
        """
        Normalizar nombre de mención:
        1. Quitar espacios al inicio/final (strip)
        2. Colapsar espacios múltiples en uno solo
        
        NO se altera la capitalización para preservar:
        - Nombres propios
        - Formato definido por el usuario
        
        Ejemplos:
        - "  Ingeniería del Software  " → "Ingeniería del Software"
        - "IA   y   Robótica" → "IA y Robótica"
        """
        if not v or not isinstance(v, str):
            return v
        
        # 1. Strip: quitar espacios al inicio/final
        v = v.strip()
        
        # 2. Colapsar espacios múltiples: "IA   y   Robótica" → "IA y Robótica"
        v = re.sub(r'\s+', ' ', v)
        
        return v


# ============================================================
#  CREATE: Schema para crear mención (POST)
# ============================================================

class MencionCreate(MencionBase):
    """
    Schema para crear una nueva mención.
    
    Hereda todos los campos de MencionBase.
    Campos requeridos:
    - programa_id (required, > 0)
    - nombre (required, 1-200 chars)
    
    Campos con default:
    - activo (default: True)
    
    Validaciones:
    - El programa debe existir (validado en Service)
    - La combinación (programa_id, nombre) debe ser única (validado en Service)
    
    Ejemplo:
    ```json
    {
        "programa_id": 1,
        "nombre": "Ingeniería del Software",
        "activo": true
    }
    ```
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "programa_id": 1,
                "nombre": "Ingeniería del Software",
                "activo": True
            }
        }
    )


# ============================================================
#  UPDATE: Schema para actualizar mención (PUT/PATCH)
# ============================================================

class MencionUpdate(BaseModel):
    """
    Schema para actualizar una mención existente.
    
    Todos los campos son opcionales (update parcial).
    Solo se actualizan los campos proporcionados.
    
    Validaciones:
    - Si se cambia programa_id: el programa debe existir
    - Si se cambia nombre: la combinación (programa_id, nombre) debe ser única
    
    Ejemplo (actualizar solo nombre):
    ```json
    {
        "nombre": "Ingeniería del Software Avanzada"
    }
    ```
    
    Ejemplo (cambiar de programa):
    ```json
    {
        "programa_id": 2,
        "nombre": "Computación"
    }
    ```
    """
    
    programa_id: Optional[int] = Field(
        None,
        gt=0,
        description="ID del programa al que pertenece la mención"
    )
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre de la mención"
    )
    
    activo: Optional[bool] = Field(
        None,
        description="Estado activo/inactivo"
    )
    
    
    @field_validator('nombre', mode='before')
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar nombre: strip + colapsar espacios."""
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v
    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Ingeniería del Software Avanzada"
            }
        }
    )


# ============================================================
#  OUT: Schema de respuesta (GET)
# ============================================================

class MencionOut(MencionBase):
    """
    Schema de salida para mención.
    
    Incluye el ID autogenerado por la base de datos.
    Se usa en respuestas de GET, POST y PUT.
    
    Hereda todos los campos de MencionBase + ID.
    
    Ejemplo:
    ```json
    {
        "id": 1,
        "programa_id": 1,
        "nombre": "Ingeniería del Software",
        "activo": true
    }
    ```
    """
    
    id: int = Field(
        ...,
        description="ID único autogenerado de la mención",
        examples=[1, 42, 123]
    )
    
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde ORM models
        json_schema_extra={
            "example": {
                "id": 1,
                "programa_id": 1,
                "nombre": "Ingeniería del Software",
                "activo": True
            }
        }
    )


# ============================================================
#  LIST: Schema para listado paginado
# ============================================================

class MencionList(BaseModel):
    """
    Schema para respuesta de listado paginado de menciones.
    
    Campos:
    - total: Número total de menciones (sin paginación)
    - items: Lista de menciones en la página actual
    - page: Número de página actual (basado en skip/limit)
    - size: Tamaño de página (limit)
    
    Ejemplo:
    ```json
    {
        "total": 25,
        "items": [
            {
                "id": 1,
                "programa_id": 1,
                "nombre": "Ingeniería del Software",
                "activo": true
            }
        ],
        "page": 1,
        "size": 10
    }
    ```
    """
    
    total: int = Field(
        ...,
        ge=0,
        description="Número total de menciones (sin aplicar paginación)"
    )
    
    items: list[MencionOut] = Field(
        ...,
        description="Lista de menciones en la página actual"
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
                "total": 25,
                "items": [
                    {
                        "id": 1,
                        "programa_id": 1,
                        "nombre": "Ingeniería del Software",
                        "activo": True
                    },
                    {
                        "id": 2,
                        "programa_id": 1,
                        "nombre": "Inteligencia Artificial",
                        "activo": True
                    }
                ],
                "page": 1,
                "size": 10
            }
        }
    )


class MencionResumen(BaseModel):
    """
    Schema de solo lectura (ligero) para anidar la mención 
    dentro de relaciones (ej. AsignaturaProgramaOut).
    """
    id: int = Field(..., description="ID de la mención")
    nombre: str = Field(..., description="Nombre de la mención")

    model_config = ConfigDict(from_attributes=True)