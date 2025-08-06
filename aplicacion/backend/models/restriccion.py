from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Restriccion(Base):
    __tablename__ = 'restricciones'
    id = Column(Integer, primary_key=True)
    tipo = Column(String)
    valor = Column(Text)  # JSON con los parámetros
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    aula_id = Column(Integer, ForeignKey('aulas.id'))

    # Relationships
    asignatura = relationship('Asignatura')
    profesor = relationship('Profesor')
    aula = relationship('Aula')
