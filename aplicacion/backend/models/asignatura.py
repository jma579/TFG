from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.session import Base

class Asignatura(Base):
    __tablename__ = 'asignaturas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    creditos = Column(Integer)
    horas_semanales = Column(Integer)
    curso = Column(Integer)
    cuatrimestre = Column(Integer)

class AsignaturaGrado(Base):
    __tablename__ = 'asignatura_grado'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    grado_id = Column(Integer, ForeignKey('grados.id'))

    grado = relationship('Grado', back_populates='asignaturas')

class AsignaturaMencion(Base):
    __tablename__ = 'asignatura_mencion'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    mencion_id = Column(Integer, ForeignKey('menciones.id'))
