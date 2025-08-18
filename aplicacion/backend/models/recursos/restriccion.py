from sqlalchemy import Column, Integer, Text, ForeignKey, Enum, Time, DateTime, CheckConstraint, Index
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import TipoRestriccion, DurezaRestriccion, DiaSemana


class Restriccion(Base):
    __tablename__ = "restricciones"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoRestriccion), nullable=False)
    dureza = Column(Enum(DurezaRestriccion), nullable=False)
    motivo = Column(Text)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="SET NULL"))
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"))
    # Modelos de ventana: semanal o fechada
    dia_semana = Column(Enum(DiaSemana))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    inicio = Column(DateTime)
    fin = Column(DateTime)

    __table_args__ = (
        # XOR exacto: o profesor o aula, pero no ambos y no ninguno
        CheckConstraint(
            "((profesor_id IS NULL AND aula_id IS NOT NULL) OR "
            "(profesor_id IS NOT NULL AND aula_id IS NULL))",
            name="ck_restriccion_exclusive_parent"
        ),
        # coherencia de horas (si ambas no son NULL, hora_inicio < hora_fin)
        CheckConstraint(
            "(hora_inicio IS NULL OR hora_fin IS NULL) OR (hora_inicio < hora_fin)",
            name="ck_restriccion_horas"
        ),
        # coherencia de fechas (si ambas no son NULL, inicio < fin)
        CheckConstraint(
            "(inicio IS NULL OR fin IS NULL) OR (inicio < fin)",
            name="ck_restriccion_fechas"
        ),
        Index("ix_restriccion_profesor", "profesor_id"),
        Index("ix_restriccion_aula", "aula_id"),
    )

    profesor = relationship("Profesor", back_populates="restricciones")
    aula = relationship("Aula", back_populates="restricciones")
    conflictos = relationship("Conflicto", back_populates="restriccion", passive_deletes=True)
