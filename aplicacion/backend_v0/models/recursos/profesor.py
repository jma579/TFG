from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database.models import Base


class Profesor(Base):
    __tablename__ = "profesores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    activo = Column(Boolean, default=True, nullable=False)

    profesores_asignaturas = relationship("ProfesorAsignatura", back_populates="profesor", passive_deletes=True)
    profesores_sesiones = relationship("ProfesorSesion", back_populates="profesor", passive_deletes=True)
    restricciones = relationship("Restriccion", back_populates="profesor", passive_deletes=True)
    conflictos = relationship("Conflicto", back_populates="profesor", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="profesores_asignaturas", viewonly=True, overlaps="profesores_asignaturas")
    sesiones = relationship("Sesion", secondary="profesores_sesiones", viewonly=True, overlaps="profesores_sesiones")
