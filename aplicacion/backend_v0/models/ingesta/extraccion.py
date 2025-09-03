from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database.models import Base


class Extraccion(Base):
    __tablename__ = "extracciones"
    id = Column(Integer, primary_key=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)
    bloque = Column(String(80), nullable=False)
    contenido = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=func.now(), nullable=False)

    import_run = relationship("ImportRun", back_populates="extracciones", passive_deletes=True)
    documento = relationship("Documento", back_populates="extracciones", passive_deletes=True)
