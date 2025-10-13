from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database.models import Base


class ProfesorSesion(Base):
    __tablename__ = "profesores_sesiones"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False)
    rol_en_sesion = Column(String(30), nullable=True)

    __table_args__ = (
        UniqueConstraint("profesor_id", "sesion_id", name="uq_profesor_sesion"),
        Index("ix_prof_ses_profesor", "profesor_id"),
        Index("ix_prof_ses_sesion", "sesion_id"),
    )

    profesor = relationship("Profesor", back_populates="profesores_sesiones", passive_deletes=True)
    sesion = relationship("Sesion", back_populates="profesores_sesiones", passive_deletes=True)
