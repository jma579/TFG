from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database.models import Base


class ProfesorAsignatura(Base):
    __tablename__ = "profesores_asignaturas"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("profesor_id", "asignatura_id", name="uq_profesor_asignatura"),
        Index("ix_prof_asig_profesor", "profesor_id"),
        Index("ix_prof_asig_asignatura", "asignatura_id"),
    )

    profesor = relationship("Profesor", back_populates="profesores_asignaturas", passive_deletes=True)
    asignatura = relationship("Asignatura", back_populates="profesores_asignaturas", passive_deletes=True)
