from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Grado(Base):
    __tablename__ = 'grados'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)

    menciones = relationship('Mencion', back_populates='grado')
    asignaturas = relationship('AsignaturaGrado', back_populates='grado')