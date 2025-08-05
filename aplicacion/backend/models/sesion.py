from sqlalchemy import Column, Integer, String, Time, ForeignKey
from database import Base

class Sesion(Base):
    __tablename__ = 'sesiones'
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id'))
    profesor_id = Column(Integer, ForeignKey('profesores.id'))
    aula_id = Column(Integer, ForeignKey('aulas.id'))
    dia = Column(String)  # lunes, martes, etc.
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
