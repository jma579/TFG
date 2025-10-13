from sqlalchemy import Column, Integer, String, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import TipoPrograma


class Programa(Base):
    __tablename__ = "programas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoPrograma), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("nombre", "tipo", name="uq_programa_nombre_tipo"),
    )

    # Relaciones
    menciones = relationship("Mencion", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)
    programa_asignaturas = relationship("ProgramaAsignatura", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)
    documentos = relationship("Documento", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="programas_asignaturas", viewonly=True, overlaps="programa_asignaturas")
