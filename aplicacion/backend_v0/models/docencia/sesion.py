from sqlalchemy import Column, Integer, ForeignKey, Enum, Time, DateTime, Index
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana


class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True)
    grupo_docente_id = Column(Integer, ForeignKey("grupos_docentes.id", ondelete="CASCADE"), nullable=False)
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"), nullable=False)
    modalidad = Column(Enum(ModalidadSesion), nullable=False)
    tipo_recurrencia = Column(Enum(TipoRecurrencia), nullable=False)

    # Si semanal:
    dia_semana = Column(Enum(DiaSemana))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)

    # Si fechada:
    inicio = Column(DateTime)
    fin = Column(DateTime)

    __table_args__ = (
        Index("ix_sesion_grupo", "grupo_docente_id"),
    )

    grupo_docente = relationship("GrupoDocente", back_populates="sesiones", passive_deletes=True)
    aula = relationship("Aula", back_populates="sesiones", passive_deletes=True)

    profesores_sesiones = relationship("ProfesorSesion", back_populates="sesion", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia
    profesores = relationship("Profesor", secondary="profesores_sesiones", viewonly=True, overlaps="profesores_sesiones,profesores")

    conflictos_sesion_1 = relationship("Conflicto", back_populates="sesion", foreign_keys="Conflicto.sesion_id", passive_deletes=True)
    conflictos_sesion_2 = relationship("Conflicto", back_populates="sesion_2", foreign_keys="Conflicto.sesion_2_id", passive_deletes=True)
