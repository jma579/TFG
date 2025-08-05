from sqlalchemy import Column, Integer, String, Text, Time, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Grado(Base):
    __tablename__ = 'grados'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)

    menciones = relationship('Mencion', back_populates='grado')
    asignaturas = relationship('AsignaturaGrado', back_populates='grado')


class Mencion(Base):
    __tablename__ = 'menciones'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    grado_id = Column(Integer, ForeignKey('grados.id'))

    grado = relationship('Grado', back_populates='menciones')
    
    # Modificado por copilot
    asignaturas = relationship('AsignaturaMencion', back_populates='mencion')


class Asignatura(Base):
    __tablename__ = 'asignaturas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    creditos = Column(Integer)
    horas_semanales = Column(Integer)
    curso = Column(Integer)
    cuatrimestre = Column(Integer)

    # Modificado por copilot
    grados = relationship('AsignaturaGrado', back_populates='asignatura')
    menciones = relationship('AsignaturaMencion', back_populates='asignatura')
    profesores = relationship('ProfesorAsignatura', back_populates='asignatura')
    sesiones = relationship('Sesion', back_populates='asignatura')


class AsignaturaGrado(Base):
    __tablename__ = 'asignatura_grado'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    grado_id = Column(Integer, ForeignKey('grados.id'))

    grado = relationship('Grado', back_populates='asignaturas')
    
    # Modificado por copilot
    asignatura = relationship('Asignatura', back_populates='grados')


class AsignaturaMencion(Base):
    __tablename__ = 'asignatura_mencion'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    mencion_id = Column(Integer, ForeignKey('menciones.id'))

    # Modificado por copilot
    asignatura = relationship('Asignatura', back_populates='menciones')
    mencion = relationship('Mencion', back_populates='asignaturas')


class Profesor(Base):
    __tablename__ = 'profesores'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    disponibilidad = Column(Text)  # formato JSON

    # Modificado por copilot
    asignaturas = relationship('ProfesorAsignatura', back_populates='profesor')
    sesiones = relationship('Sesion', back_populates='profesor')


class ProfesorAsignatura(Base):
    __tablename__ = 'profesor_asignatura'
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))

    # Modificado por copilot
    profesor = relationship('Profesor', back_populates='asignaturas')
    asignatura = relationship('Asignatura', back_populates='profesores')


class Aula(Base):
    __tablename__ = 'aulas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    capacidad = Column(Integer)
    tipo = Column(String)

    # Modificado por copilot
    sesiones = relationship('Sesion', back_populates='aula')


class Sesion(Base):
    __tablename__ = 'sesiones'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    aula_id = Column(Integer, ForeignKey('aulas.id'))
    dia = Column(String)  # lunes, martes, etc.
    hora_inicio = Column(Time)
    hora_fin = Column(Time)

    # Modificado por copilot
    asignatura = relationship('Asignatura', back_populates='sesiones')
    profesor = relationship('Profesor', back_populates='sesiones')
    aula = relationship('Aula', back_populates='sesiones')


class Restriccion(Base):
    __tablename__ = 'restricciones'
    id = Column(Integer, primary_key=True)
    tipo = Column(String)
    valor = Column(Text)  # JSON con los parámetros
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    aula_id = Column(Integer, ForeignKey('aulas.id'))

    # Modificado por copilot
    asignatura = relationship('Asignatura')
    profesor = relationship('Profesor')
    aula = relationship('Aula')
