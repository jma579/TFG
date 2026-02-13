"""
Schemas Pydantic para AsignaturaAlias.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator


class AsignaturaAliasBase(BaseModel):
    alias: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="Texto alternativo detectado para la asignatura",
        examples=["Fisica I", "Calc. Dif."]
    )
    
    origen: str = Field(
        default="MANUAL",
        max_length=50,
        description="Origen del alias (HORARIO_FEEDBACK, MANUAL)"
    )

    @field_validator("alias", mode="before")
    @classmethod
    def normalize_alias(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El alias no puede estar vacío")
        return " ".join(v.strip().split())


class AsignaturaAliasCreate(AsignaturaAliasBase):
    asignatura_id: int = Field(..., gt=0)


class AsignaturaAliasOut(AsignaturaAliasBase):
    id: int
    asignatura_id: int
    veces_usado: int = Field(..., ge=0)
    
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