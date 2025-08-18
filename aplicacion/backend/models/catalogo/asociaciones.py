from sqlalchemy import Column, Integer, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database.models import Base


class ProgramaAsignatura(Base):
    __tablename__ = "programas_asignaturas"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    curso = Column(Integer)
    obligatoria = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("programa_id", "asignatura_id", name="uq_programa_asignatura"),
        Index("ix_prog_asig_programa", "programa_id"),
        Index("ix_prog_asig_asignatura", "asignatura_id"),
    )

    programa = relationship("Programa", back_populates="programa_asignaturas", passive_deletes=True)
    asignatura = relationship("Asignatura", back_populates="programa_asignaturas", passive_deletes=True)


class AsignaturaMencion(Base):
    __tablename__ = "asignaturas_menciones"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    mencion_id = Column(Integer, ForeignKey("menciones.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("asignatura_id", "mencion_id", name="uq_asignatura_mencion"),
        Index("ix_asig_men_asignatura", "asignatura_id"),
        Index("ix_asig_men_mencion", "mencion_id"),
    )

    asignatura = relationship("Asignatura", back_populates="asignatura_menciones", passive_deletes=True)
    mencion = relationship("Mencion", back_populates="asignatura_menciones", passive_deletes=True)
