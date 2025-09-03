from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database.models import Base


class ImportRun(Base):
    __tablename__ = "import_runs"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String(20), nullable=False)
    inicio_en = Column(DateTime, default=func.now(), nullable=False)
    fin_en = Column(DateTime)
    resumen = Column(Text)

    documento = relationship("Documento", back_populates="import_runs", passive_deletes=True)
    extracciones = relationship("Extraccion", back_populates="import_run", cascade="all, delete-orphan", passive_deletes=True)
