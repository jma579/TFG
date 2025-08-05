from sqlalchemy import Column, Integer, String
from database import Base

class Aula(Base):
    __tablename__ = 'aulas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    capacidad = Column(Integer)
    tipo = Column(String)
