from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base

class Profesor(Base):
    __tablename__ = 'profesores'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    disponibilidad = Column(Text)  # formato JSON

class ProfesorAsignatura(Base):
    __tablename__ = 'profesor_asignatura'
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
