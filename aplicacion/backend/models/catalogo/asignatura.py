from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import Periodo, ModalidadAsignatura, Idioma


class Asignatura(Base):
    __tablename__ = "asignaturas"
    id = Column(Integer, primary_key=True)
    codigo_plan = Column(String(6), nullable=False, unique=True)
    nombre = Column(String(250), nullable=False, unique=True)
    periodo = Column(Enum(Periodo), nullable=False)
    ects = Column(Integer)
    modalidad = Column(Enum(ModalidadAsignatura), nullable=False)
    idioma = Column(Enum(Idioma), nullable=False, default=Idioma.ESPAÑOL)
    english_friendly = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, default=True, nullable=False)

    # Relaciones
    grupos_docentes = relationship("GrupoDocente", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)
    programa_asignaturas = relationship("ProgramaAsignatura", back_populates="asignatura", passive_deletes=True)
    asignatura_menciones = relationship("AsignaturaMencion", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)
    profesores_asignaturas = relationship("ProfesorAsignatura", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia (solo lectura)
    programas = relationship("Programa", secondary="programas_asignaturas", viewonly=True, overlaps="programa_asignaturas")
    menciones = relationship("Mencion", secondary="asignaturas_menciones", viewonly=True, overlaps="asignatura_menciones")
