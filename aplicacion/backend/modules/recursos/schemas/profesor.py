"""
Schemas Pydantic para la entidad Profesor.

Estos modelos definen:
- Validación de entrada (tipos, rangos, formatos)
- Serialización de salida (respuestas API)
- Documentación automática (OpenAPI)
- Normalización de datos (strip, lowercase, etc.)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from typing import Optional
import re


# ============================================================
#  BASE: Campos comunes compartidos por Create/Update/Out
# ============================================================

class ProfesorBase(BaseModel):
    """
    Schema base con campos comunes de Profesor.
    
    Campos:
    - nombre: Nombre del profesor (1-120 chars)
    - apellidos: Apellidos del profesor (1-200 chars)
    - email: Correo electrónico único (opcional, max 200 chars)
    - telefono: Teléfono de contacto (opcional, max 20 chars)
    - departamento: Departamento al que pertenece (opcional, max 200 chars)
    - activo: Estado del profesor (soft delete)
    """
    
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Nombre del profesor",
        examples=["Juan", "María José", "Pedro"]
    )
    
    apellidos: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Apellidos del profesor",
        examples=["García López", "Martínez", "Fernández García"]
    )
    
    email: Optional[str] = Field(
        None,
        max_length=200,
        description="Correo electrónico único del profesor",
        examples=["juan.garcia@universidad.es", "maria.martinez@uam.es"]
    )
    
    telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono de contacto del profesor",
        examples=["+34 912 345 678", "912345678", "+1-555-1234"]
    )
    
    departamento: Optional[str] = Field(
        None,
        max_length=200,
        description="Departamento al que pertenece el profesor",
        examples=["Matemáticas", "Ingeniería Informática", "Física Aplicada"]
    )
    
    activo: bool = Field(
        default=True,
        description="Indica si el profesor está activo (soft delete)"
    )
    
    
    @field_validator('nombre', 'apellidos', 'departamento', mode='before')
    @classmethod
    def normalize_texto(cls, v: Optional[str]) -> Optional[str]:
        """
        Normalizar campos de texto:
        1. Quitar espacios al inicio/final (strip)
        2. Colapsar espacios múltiples en uno solo
        
        IMPORTANTE: mode='before' para normalizar ANTES de validar longitud.
        
        Ejemplos:
        - "  Juan  " → "Juan"
        - "García   López" → "García López"
        - "  Matemáticas  Aplicadas  " → "Matemáticas Aplicadas"
        """
        if v is None or not isinstance(v, str):
            return v
        
        # 1. Strip: quitar espacios al inicio/final
        v = v.strip()
        
        # 2. Colapsar espacios múltiples en uno solo
        v = re.sub(r'\s+', ' ', v)
        
        return v
    
    
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """
        Normalizar email:
        1. Quitar espacios al inicio/final (strip)
        2. Convertir a minúsculas para consistencia en búsquedas
        
        IMPORTANTE: mode='before' para normalizar ANTES de validar formato.
        
        Ejemplos:
        - "  Juan.Garcia@Universidad.ES  " → "juan.garcia@universidad.es"
        - "MARIA@UAM.ES" → "maria@uam.es"
        """
        if v is None or not isinstance(v, str):
            return v
        
        # 1. Strip: quitar espacios
        v = v.strip()
        
        # 2. Lowercase: para consistencia (emails case-insensitive)
        v = v.lower()
        
        return v
    
    
    @field_validator('telefono', mode='before')
    @classmethod
    def normalize_telefono(cls, v: Optional[str]) -> Optional[str]:
        """
        Normalizar teléfono:
        1. Quitar espacios al inicio/final (strip)
        
        NO se modifica el formato interno para preservar:
        - Prefijos internacionales (+34, +1, etc.)
        - Separadores (espacios, guiones) definidos por el usuario
        - Extensiones
        
        Ejemplos:
        - "  +34 912 345 678  " → "+34 912 345 678"
        - "  912345678  " → "912345678"
        """
        if v is None or not isinstance(v, str):
            return v
        
        # Solo strip: preservar formato interno
        return v.strip()


# ============================================================
#  CREATE: Schema para crear profesor (POST)
# ============================================================

class ProfesorCreate(ProfesorBase):
    """
    Schema para crear un nuevo profesor.
    
    Hereda todos los campos de ProfesorBase.
    Campos requeridos:
    - nombre
    - apellidos
    
    Campos opcionales:
    - email (único si se proporciona)
    - telefono
    - departamento
    - activo (default: True)
    
    Ejemplo:
    ```json
    {
        "nombre": "Juan",
        "apellidos": "García López",
        "email": "juan.garcia@universidad.es",
        "telefono": "+34 912 345 678",
        "departamento": "Matemáticas",
        "activo": true
    }
    ```
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Juan",
                "apellidos": "García López",
                "email": "juan.garcia@universidad.es",
                "telefono": "+34 912 345 678",
                "departamento": "Matemáticas",
                "activo": True
            }
        }
    )


# ============================================================
#  UPDATE: Schema para actualizar profesor (PUT/PATCH)
# ============================================================

class ProfesorUpdate(BaseModel):
    """
    Schema para actualizar un profesor existente.
    
    Todos los campos son opcionales (update parcial).
    Solo se actualizan los campos proporcionados.
    
    Ejemplo (actualizar solo email y departamento):
    ```json
    {
        "email": "nuevo.email@universidad.es",
        "departamento": "Ingeniería Informática"
    }
    ```
    """
    
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=120,
        description="Nombre del profesor"
    )
    
    apellidos: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Apellidos del profesor"
    )
    
    email: Optional[str] = Field(
        None,
        max_length=200,
        description="Correo electrónico único"
    )
    
    telefono: Optional[str] = Field(
        None,
        max_length=20,
        description="Teléfono de contacto"
    )
    
    departamento: Optional[str] = Field(
        None,
        max_length=200,
        description="Departamento del profesor"
    )
    
    activo: Optional[bool] = Field(
        None,
        description="Estado activo/inactivo"
    )
    
    
    @field_validator('nombre', 'apellidos', 'departamento', mode='before')
    @classmethod
    def normalize_texto(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar texto: strip + colapsar espacios ANTES de validar longitud."""
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = re.sub(r'\s+', ' ', v)
        return v
    
    
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar email: strip + lowercase ANTES de validar formato."""
        if v is None or not isinstance(v, str):
            return v
        v = v.strip()
        v = v.lower()
        return v
    
    
    @field_validator('telefono', mode='before')
    @classmethod
    def normalize_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Normalizar teléfono: solo strip ANTES de validar longitud."""
        if v is None or not isinstance(v, str):
            return v
        return v.strip()
    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "nuevo.email@universidad.es",
                "departamento": "Ingeniería Informática"
            }
        }
    )


# ============================================================
#  OUT: Schema de respuesta (GET)
# ============================================================

class ProfesorOut(ProfesorBase):
    """
    Schema de salida para profesor.
    
    Incluye el ID autogenerado por la base de datos.
    Se usa en respuestas de GET, POST y PUT.
    
    Hereda todos los campos de ProfesorBase + ID.
    """
    
    id: int = Field(
        ...,
        description="ID único autogenerado del profesor",
        examples=[1, 42, 123]
    )
    
    model_config = ConfigDict(
        from_attributes=True,  # Permite crear desde ORM models
        json_schema_extra={
            "example": {
                "id": 1,
                "nombre": "Juan",
                "apellidos": "García López",
                "email": "juan.garcia@universidad.es",
                "telefono": "+34 912 345 678",
                "departamento": "Matemáticas",
                "activo": True
            }
        }
    )


# ============================================================
#  LIST: Schema para listado paginado
# ============================================================

class ProfesorList(BaseModel):
    """
    Schema para respuesta de listado paginado de profesores.
    
    Campos:
    - total: Número total de profesores (sin paginación)
    - items: Lista de profesores en la página actual
    - page: Número de página actual (basado en skip/limit)
    - size: Tamaño de página (limit)
    
    Ejemplo:
    ```json
    {
        "total": 85,
        "items": [...],
        "page": 2,
        "size": 20
    }
    ```
    """
    
    total: int = Field(
        ...,
        ge=0,
        description="Número total de profesores (sin aplicar paginación)"
    )
    
    items: list[ProfesorOut] = Field(
        ...,
        description="Lista de profesores en la página actual"
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
                "total": 85,
                "items": [
                    {
                        "id": 1,
                        "nombre": "Juan",
                        "apellidos": "García López",
                        "email": "juan.garcia@universidad.es",
                        "telefono": "+34 912 345 678",
                        "departamento": "Matemáticas",
                        "activo": True
                    }
                ],
                "page": 1,
                "size": 20
            }
        }
    )