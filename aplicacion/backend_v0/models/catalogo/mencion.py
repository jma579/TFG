from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.models import Base


class Mencion(Base):
    __tablename__ = "menciones"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(200), nullable=False, unique=True)

    programa = relationship("Programa", back_populates="menciones", passive_deletes=True)
    asignatura_menciones = relationship("AsignaturaMencion", back_populates="mencion", passive_deletes=True)
    asignaturas = relationship("Asignatura", secondary="asignaturas_menciones", viewonly=True)