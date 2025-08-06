from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Asignatura(Base):
    __tablename__ = 'asignaturas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    creditos = Column(Integer)
    horas_semanales = Column(Integer)
    curso = Column(Integer)
    cuatrimestre = Column(Integer)

    # Relationships
    grados = relationship('AsignaturaGrado', back_populates='asignatura')
    menciones = relationship('AsignaturaMencion', back_populates='asignatura')
    profesores = relationship('ProfesorAsignatura', back_populates='asignatura')
    sesiones = relationship('Sesion', back_populates='asignatura')


class AsignaturaGrado(Base):
    __tablename__ = 'asignatura_grado'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    grado_id = Column(Integer, ForeignKey('grados.id'))

    # Relationships
    grado = relationship('Grado', back_populates='asignaturas')
    asignatura = relationship('Asignatura', back_populates='grados')


class AsignaturaMencion(Base):
    __tablename__ = 'asignatura_mencion'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    mencion_id = Column(Integer, ForeignKey('menciones.id'))

    # Relationships
    asignatura = relationship('Asignatura', back_populates='menciones')
    mencion = relationship('Mencion', back_populates='asignaturas')
