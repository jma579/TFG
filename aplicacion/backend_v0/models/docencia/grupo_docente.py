from sqlalchemy import Column, Integer, String, Enum, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import TipoGrupoDocente


class GrupoDocente(Base):
    __tablename__ = "grupos_docentes"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(50), nullable=False)
    tipo = Column(Enum(TipoGrupoDocente), nullable=False)
    curso = Column(Integer)
    turno = Column(String(30))

    __table_args__ = (
        UniqueConstraint("asignatura_id", "codigo", name="uq_grupo_asig_codigo"),
        Index("ix_grupo_asignatura", "asignatura_id"),
    )

    asignatura = relationship("Asignatura", back_populates="grupos_docentes", passive_deletes=True)
    sesiones = relationship("Sesion", back_populates="grupo_docente", cascade="all, delete-orphan", passive_deletes=True)
