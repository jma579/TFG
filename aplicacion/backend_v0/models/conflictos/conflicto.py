from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime, CheckConstraint, Index, func
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import TipoConflicto, SeveridadConflicto, EstadoConflicto


class Conflicto(Base):
    __tablename__ = "conflictos"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoConflicto), nullable=False)
    severidad = Column(Enum(SeveridadConflicto), nullable=False)
    estado = Column(Enum(EstadoConflicto), nullable=False, default=EstadoConflicto.ABIERTO)

    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False)
    sesion_2_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="SET NULL"))
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"))
    restriccion_id = Column(Integer, ForeignKey("restricciones.id", ondelete="SET NULL"))

    descripcion = Column(Text)
    hash_deteccion = Column(String(64), nullable=False, unique=True)
    creado_en = Column(DateTime, default=func.now(), nullable=False)
    resuelto_en = Column(DateTime)

    __table_args__ = (
        CheckConstraint(
            "sesion_2_id IS NULL OR sesion_id <> sesion_2_id",
            name="ck_conflicto_sesiones_distintas"
        ),
        Index("ix_conflicto_sesion", "sesion_id"),
        Index("ix_conflicto_sesion_2", "sesion_2_id"),
        Index("ix_conflicto_profesor", "profesor_id"),
        Index("ix_conflicto_aula", "aula_id"),
        Index("ix_conflicto_restriccion", "restriccion_id"),
    )

    sesion = relationship("Sesion", foreign_keys=[sesion_id], back_populates="conflictos_sesion_1", passive_deletes=True)
    sesion_2 = relationship("Sesion", foreign_keys=[sesion_2_id], back_populates="conflictos_sesion_2", passive_deletes=True)
    profesor = relationship("Profesor", back_populates="conflictos", passive_deletes=True)
    aula = relationship("Aula", back_populates="conflictos", passive_deletes=True)
    restriccion = relationship("Restriccion", back_populates="conflictos", passive_deletes=True)
