from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

# Entidades del extractor (entrada)
from core.extraccion.entities.extractor import ExtractionResult, ExtractionMetadata

from core.extraccion.entities.common import ParseReport, ParserError

from core.extraccion.constants.base import (
    BASE_PARSER_CONFIG 
)


TParsed = TypeVar("TParsed")  # Tipo de salida que devolverán las subclases


# =========================
# Parser base (contrato)
# =========================
class BaseParser(ABC, Generic[TParsed]):
    """
    Base para parsers académicos.

    Diseño:
      - Las subclases implementan `parse_text` (y opcionalmente `validate`, `to_normalized`).
      - `parse` recibe un `ExtractionResult` completo para facilitar la integración.
      - Este base solo define **firmas y docstrings**; no implementa lógica.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Args:
            config: Diccionario opcional para ajustes del parser (umbrales, proximidades, etc.)
        """
        self.name = self.__class__.__name__
        self.config = BASE_PARSER_CONFIG.copy()
        if config:
            self.config.update(config)
        self.cache = {}  # TODO: Revisar esto

    # ---------- Punto de entrada recomendado ----------
    def parse(self, extraction_result: ExtractionResult) -> TParsed:
        """
        Punto de entrada que usan los clientes.

        Args:
            extraction_result: Resultado de extracción (texto + metadatos) emitido por el extractor.

        Returns:
            Instancia tipada de la salida del parser (p. ej., SubjectSheet o List[ScheduleEntry]).

        Raises:
            ParserError: si el texto es insuficiente o si el parsing falla de forma no recuperable.
        """
        text = extraction_result.text or ""
        metadata = extraction_result.metadata

        # Comprobacion de calidad y estado
        if not text or len(text.strip()) < self.config.get("min_text_length", 20):
            raise ParserError("El texto de entrada está vacío o es insuficiente.")
        if not extraction_result.success:
            raise ParserError(f"Extracción fallida: {extraction_result.error_message}")
        if not extraction_result.is_usable:
            raise ParserError("Calidad de extracción insuficiente para parsing.")
        if extraction_result.confidence < self.config.get("min_confidence", 0.5):
            raise ParserError("Confianza de extracción insuficiente para parsing.")
        
        try:
            return self.parse_text(text, metadata)
        except ParserError:
            raise
        except Exception as e:
            raise ParserError(f"Error durante el parsing en {self.name}: {e}") from e

    # ---------- Implementación obligatoria por subclase ----------
    @abstractmethod
    def parse_text(self, text: str, metadata: Optional[ExtractionMetadata] = None) -> TParsed:
        """
        Implementar en la subclase:
          - Preprocesado (si procede)
          - Extracción de señales mínimas (si procede)
          - Parsing estructurado
          - Validación de la salida
          - Cálculo de confianza (si usas report)
          - Construcción del ParseReport (y asignar self.last_report)
        Debe lanzar ParserError con mensajes claros cuando falle.
        """
        raise NotImplementedError

    # ---------- Validación (opcional) ----------
    def validate(self, parsed: TParsed) -> Tuple[bool, List[str]]:
        """
        Valida mínimos de la salida (p. ej., ficha: code+name; horario: ≥1 entrada con day+start).

        Returns:
            (is_valid, errores)
        """
        return True, []

    # ---------- Normalización (opcional) ----------
    def to_normalized(self, parsed: TParsed) -> Dict[str, Any]:
        """
        Convierte la salida tipada a un `dict` estable (contrato común para el motor de conflictos).

        Ejemplos:
          - Ficha → {"subject": {...}, "workload": {...}, "teaching_staff": [...]}
          - Horario → {"timetable": [ ... ]}

        Returns:
            dict serializable.
        """
        return {}

    # ---------- Reporte (opcional) ----------
    def build_report(
        self,
        parsed: Optional[TParsed] = None,
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ParseReport:
        """
        Construye un reporte homogéneo para trazas/logs.

        Nota: las subclases pueden enriquecer `confidence` con métricas propias.
        """
        return ParseReport(
            parser_name=self.name,
            confidence=confidence,
            warnings=warnings or [],
            errors=errors or [],
            extra=extra or {},
        )

    # =========================
    # Utilidades comunes (firmas)
    # =========================
    def preprocess(self, text: str) -> str:
        """
        Normalización leve previa al parsing. Ejemplos:
          - colapsar espacios múltiples
          - estandarizar separadores alrededor de ':'
          - conservar saltos si el parser los necesita para heurísticas

        Returns:
            texto normalizado (no destructivo).
        """
        # Colapsar espacios múltiples
        text = re.sub(r'\s+', ' ', text)

        # Estandarizar separadores comunes
        text = re.sub(r'\s*:\s*', ': ', text)      # "Profesor : Dr." → "Profesor: Dr."
        text = re.sub(r'\s*-\s*', ' - ', text)     # "9:00-11:00" → "9:00 - 11:00"
        text = re.sub(r'\s*,\s*', ', ', text)      # "L,M,X" → "L, M, X"

        # Espacios alrededor de paréntesis
        text = re.sub(r'\s*\(\s*', ' (', text)
        text = re.sub(r'\s*\)\s*', ') ', text)

        # Eliminar espacios al inicio y final
        return text.strip()

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenización simple (si la subclase lo necesita).
        """
        return text.split()

    def nearby_context(self, text: str, start: int, end: int, radius: int) -> str:
        """
        Devuelve una ventana de contexto alrededor de un match (para buscar entidades relacionadas).

        Args:
            text: Texto completo.
            start: Índice de inicio del match.
            end: Índice de fin del match.
            radius: Número de caracteres a ambos lados del match.

        Returns:
            Subcadena de contexto.
        """
        left = max(0, start - self.config.get("radius", 80))
        right = min(len(text), end + self.config.get("radius", 80))
        return text[left:right]
