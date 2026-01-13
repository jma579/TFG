"""
Esquemas Pydantic para la entidad AsignaturaAlias.

Define los contratos de datos para:
- Entrada: Creación de nuevos alias (AsignaturaAliasCreate).
- Salida: Representación de alias existentes (AsignaturaAliasOut).
- Validaciones: Normalización de texto (trim y espacios simples).

Uso:
Principalmente utilizado por el Pipeline de Horarios para el aprendizaje automático
y potencialmente por un panel de administración para gestión manual.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================
#  SCHEMAS: Base y derivados
# ============================================================

class AsignaturaAliasBase(BaseModel):
    """
    Campos comunes para AsignaturaAlias.
    """
    
    alias: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="Texto alternativo detectado para la asignatura (ej: 'Mat. 1')",
        examples=["Fisica I", "Calc. Dif."]
    )
    
    origen: str = Field(
        default="MANUAL",
        max_length=50,
        description="Origen del alias (ej: HORARIO_FEEDBACK, MANUAL)"
    )

    # --- Validadores ---

    @field_validator("alias", mode="before")
    @classmethod
    def normalize_alias(cls, v: str) -> str:
        """
        Normaliza el alias: elimina espacios extremos y colapsa espacios internos.
        Ej: "  Fisica   1  " -> "Fisica 1"
        """
        if not v or not v.strip():
            raise ValueError("El alias no puede estar vacío")
        return " ".join(v.strip().split())


class AsignaturaAliasCreate(AsignaturaAliasBase):
    """
    Schema para registrar un nuevo alias.
    Requiere vincularlo a una asignatura existente.
    """
    asignatura_id: int = Field(
        ..., 
        gt=0, 
        description="ID de la asignatura oficial a la que apunta este alias"
    )


class AsignaturaAliasOut(AsignaturaAliasBase):
    """
    Schema de salida (API Response).
    Incluye datos de auditoría como el contador de usos.
    """
    id: int = Field(..., description="ID único del alias")
    asignatura_id: int = Field(..., description="ID de la asignatura vinculada")
    veces_usado: int = Field(..., ge=0, description="Número de veces que este alias ha sido detectado/usado")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "asignatura_id": 42,
                "alias": "Física 1",
                "origen": "HORARIO_FEEDBACK",
                "veces_usado": 5
            }
        }
    )