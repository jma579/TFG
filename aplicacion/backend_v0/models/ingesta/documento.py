from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database.models import Base


class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(250), nullable=False)
    tipo = Column(String(30), nullable=False)
    ruta = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=func.now(), nullable=False)

    programa = relationship("Programa", back_populates="documentos", passive_deletes=True)
    import_runs = relationship("ImportRun", back_populates="documento", cascade="all, delete-orphan", passive_deletes=True)
    extracciones = relationship("Extraccion", back_populates="documento", passive_deletes=True)
