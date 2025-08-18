from sqlalchemy import Column, Integer, String, Enum, CheckConstraint
from sqlalchemy.orm import relationship
from database.models import Base
from backend.constants.enums import TipoAula


class Aula(Base):
    __tablename__ = "aulas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False, unique=True)
    codigo = Column(String(50), nullable=False, unique=True)
    tipo = Column(Enum(TipoAula), nullable=False)
    capacidad = Column(Integer)

    __table_args__ = (
        CheckConstraint(
            "capacidad IS NULL OR capacidad >= 0",
            name="ck_aula_capacidad_no_neg"
        ),
    )

    sesiones = relationship("Sesion", back_populates="aula", passive_deletes=True)
    restricciones = relationship("Restriccion", back_populates="aula", passive_deletes=True)
    conflictos = relationship("Conflicto", back_populates="aula", passive_deletes=True)
