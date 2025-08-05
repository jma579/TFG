from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Mencion(Base):
    __tablename__ = 'menciones'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    grado_id = Column(Integer, ForeignKey('grados.id'))

    grado = relationship('Grado', back_populates='menciones')