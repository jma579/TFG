from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Profesor(Base):
    __tablename__ = 'profesores'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    disponibilidad = Column(Text)  # formato JSON

    # Relationships
    asignaturas = relationship('ProfesorAsignatura', back_populates='profesor')
    sesiones = relationship('Sesion', back_populates='profesor')


class ProfesorAsignatura(Base):
    __tablename__ = 'profesor_asignatura'
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))

    # Relationships
    profesor = relationship('Profesor', back_populates='asignaturas')
    asignatura = relationship('Asignatura', back_populates='profesores')
