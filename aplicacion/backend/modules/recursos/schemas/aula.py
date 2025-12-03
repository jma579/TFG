"""
Esquemas Pydantic para la entidad Aula.

Define los contratos de datos para:
- Entrada: AulaCreate, AulaUpdate
- Salida: AulaOut, AulaList
- Validaciones: unicidad de nombre/código, normalización de texto, capacidad > 0

Responsabilidades:
- Validar tipos de datos (Pydantic automático)
- Normalizar texto (strip, colapsar espacios)
- Validar reglas de negocio (capacidad positiva)
- Convertir modelos SQLAlchemy a JSON (AulaOut)
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List

from constants.enums import TipoAula


# ============================================================
#  HELPERS: Validadores reutilizables
# ============================================================

def normalize_texto(value: Optional[str]) -> Optional[str]:
    """
    Normalizar texto: trim + colapsar múltiples espacios.
    
    Ejemplos:
        "  Aula   A101  " → "Aula A101"
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

class AulaBase(BaseModel):
    """
    Schema base para Aula con campos comunes.
    
    Campos:
        - nombre: Nombre descriptivo del aula (ej: "Aula Magna")
        - codigo: Código único alfanumérico (ej: "A101", "LAB-2")
        - tipo: Tipo de aula según enum TipoAula
        - capacidad: Aforo máximo (opcional, pero si existe debe ser > 0)
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo del aula",
        examples=["Aula Magna", "Laboratorio de Física", "Sala de Seminarios 1"]
    )
    
    codigo: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código único del aula (alfanumérico)",
        examples=["A101", "LAB-2", "SEM-3A", "MAGNA"]
    )
    
    tipo: TipoAula = Field(
        ...,
        description="Tipo de aula según clasificación"
    )
    
    capacidad: Optional[int] = Field(
        None,
        gt=0,  # Si tiene valor, debe ser > 0 (validación DB: CHECK capacidad > 0)
        description="Aforo máximo del aula (número de plazas)",
        examples=[30, 50, 100, 200]
    )
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @field_validator("nombre", "codigo", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        """Normalizar nombre y código: trim + colapsar espacios."""
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: str) -> str:
        """
        Validar formato del código:
        - Solo alfanuméricos, guiones y guiones bajos
        - No permitir solo espacios/guiones
        """
        if not value:
            raise ValueError("El código no puede estar vacío")
        
        # Verificar que contenga al menos un carácter alfanumérico
        if not any(c.isalnum() for c in value):
            raise ValueError("El código debe contener al menos un carácter alfanumérico")
        
        return value.upper()  # Normalizar a mayúsculas


class AulaCreate(AulaBase):
    """
    Schema para crear un aula.
    
    Hereda todos los campos de AulaBase.
    Todos los campos obligatorios excepto capacidad.
    
    Validaciones adicionales:
    - nombre único (validado en service layer)
    - codigo único (validado en service layer)
    """
    pass


class AulaUpdate(BaseModel):
    """
    Schema para actualizar un aula (actualización parcial).
    
    Todos los campos son opcionales.
    Solo se actualizan los campos proporcionados (exclude_unset=True).
    
    Comportamiento:
    - Campo no incluido → No se modifica
    - Campo con valor → Se actualiza
    - Campo con null → Se borra (pone a None) - solo capacidad
    
    Nota: nombre y codigo no pueden ser null (nullable=False en DB)
    """
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nuevo nombre del aula"
    )
    
    codigo: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Nuevo código del aula"
    )
    
    tipo: Optional[TipoAula] = Field(
        None,
        description="Nuevo tipo de aula"
    )
    
    capacidad: Optional[int] = Field(
        None,
        gt=0,
        description="Nueva capacidad (null para borrar)"
    )
    
    # ============================================================
    #  VALIDADORES
    # ============================================================
    
    @field_validator("nombre", "codigo", mode="before")
    @classmethod
    def normalize_strings(cls, value: Optional[str]) -> Optional[str]:
        """Normalizar nombre y código."""
        return normalize_texto(value)
    
    @field_validator("codigo")
    @classmethod
    def validate_codigo_format(cls, value: Optional[str]) -> Optional[str]:
        """Validar formato del código si se proporciona."""
        if value is None:
            return None
        
        if not any(c.isalnum() for c in value):
            raise ValueError("El código debe contener al menos un carácter alfanumérico")
        
        return value.upper()


class AulaOut(AulaBase):
    """
    Schema para respuestas de Aula (incluye ID).
    
    Usado en:
    - Respuestas de endpoints GET, POST, PUT
    - Elementos de listas
    
    Incluye configuración para convertir desde modelo SQLAlchemy.
    """
    
    id: int = Field(
        ...,
        description="ID único del aula (autogenerado)"
    )
    
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde modelo SQLAlchemy
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Aula Magna",
                "codigo": "MAGNA",
                "tipo": "TEORIA",
                "capacidad": 200
            }
        }
    )


class AulaList(BaseModel):
    """
    Schema para respuestas de listado paginado.
    
    Usado en: GET /aulas (lista con paginación)
    
    Incluye metadatos de paginación:
    - total: Total de registros (sin paginar)
    - items: Lista de aulas en la página actual
    - page: Número de página actual
    - size: Tamaño de página (limit)
    """
    
    total: int = Field(
        ...,
        ge=0,
        description="Total de aulas que cumplen los filtros (sin paginar)"
    )
    
    items: List[AulaOut] = Field(
        ...,
        description="Aulas en la página actual"
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
                "total": 42,
                "items": [
                    {
                        "id": 1,
                        "nombre": "Aula Magna",
                        "codigo": "MAGNA",
                        "tipo": "TEORIA",
                        "capacidad": 200
                    },
                    {
                        "id": 2,
                        "nombre": "Laboratorio de Física",
                        "codigo": "LAB-FIS-1",
                        "tipo": "LABORATORIO",
                        "capacidad": 30
                    }
                ],
                "page": 1,
                "size": 20
            }
        }
    )