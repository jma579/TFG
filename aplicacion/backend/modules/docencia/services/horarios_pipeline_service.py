"""Servicio de orquestación para el flujo de horarios académicos.

Este servicio coordina las distintas fases del pipeline de horarios:
- extracción de tablas a partir de un PDF de horario (HorarioExtractor)
- parsing de las tablas en sesiones temporales (HorarioParser)

En esta primera versión **no** realiza persistencia en BD ni normalización;
únicamente devuelve un `HorarioTemporalOut` listo para que el frontend lo
muestre y permita su edición.

La normalización y creación de entidades en la base de datos se implementará
posteriormente en un método separado (`confirmar_horario`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from backend.core.extraccion.horarios.extractor import HorarioExtractor
from backend.core.extraccion.horarios.parser import HorarioParser
from backend.core.extraccion.horarios.normalize import horario_data_normalizer


from backend.modules.docencia.schemas.horarios import (
    HorarioTemporalOut, HorarioTemporalConfirmIn, HorarioConfirmResponse
)
from backend.modules.docencia.services.horarios_normalization_models import (
    build_parsing_result_for_normalization,
)


class HorariosPipelineService:
    """Servicio de alto nivel para el flujo de horarios.

    Responsable de exponer una API de Python sencilla para los routers FastAPI,
    escondiendo los detalles de extractor y parser.

    Uso típico desde un endpoint:

        service = HorariosPipelineService()
        horario_temporal = service.extraer_horario(pdf_path)

    Más adelante se añadirá un método `confirmar_horario(...)` que utilizará
    el normalizador y los servicios de dominio (grupos, sesiones, aulas...).
    """

    def __init__(self) -> None:
        # En esta versión inicial instanciamos extractor y parser directamente.
        # Si en el futuro necesitas inyección de dependencias, se puede adaptar
        # para recibirlos desde fuera.
        self._extractor = HorarioExtractor()
        self._parser = HorarioParser()

    # ---------------------------------------------------------------------
    # API pública
    # ---------------------------------------------------------------------
    def extraer_horario(self, pdf_path: Union[str, Path]) -> HorarioTemporalOut:
        """Ejecuta el pipeline de extracción+parsing y devuelve un horario temporal.

        Args:
            pdf_path: Ruta al archivo PDF de horario a procesar.

        Returns:
            HorarioTemporalOut: objeto Pydantic que representa el horario
            temporal editable, listo para ser enviado al frontend.
        """
        # Aseguramos que trabajamos siempre con una cadena de texto
        path_str = str(pdf_path)

        # 1) Extracción de tablas y metadatos a partir del PDF
        extraction_result = self._extractor.extract(path_str)

        # 2) Parsing de las tablas extraídas para construir sesiones temporales
        #    y serialización a un dict alineado con los DTOs de horarios.
        parsed_dict = self._parser.parse(extraction_result)

        # 3) Construcción del DTO Pydantic. Pydantic se encarga de mapear
        #    los dicts anidados de metadatos a ExtractionMetadataOut y
        #    ParsingMetadataOut automáticamente.
        return HorarioTemporalOut(**parsed_dict)
    

    def confirmar_horario(self, data: HorarioTemporalConfirmIn) -> HorarioConfirmResponse:
        """Confirmar un horario editado y normalizar sus sesiones.

        En esta fase el método NO persiste nada en la base de datos. Su
        responsabilidad es:

        - A partir del DTO HorarioTemporalConfirmIn reconstruir una estructura
          equivalente a ParsingResult (usando modelos de adaptación internos).
        - Pasar esa estructura al HorarioDataNormalizer para:
            - Filtrar tablas mal construidas
            - Filtrar sesiones mal formadas (sin horas, sin día, etc.)
        - Calcular métricas agregadas sobre el resultado:
            - nº de tablas/sesiones recibidas
            - nº de tablas/sesiones que sobreviven a la normalización

        Más adelante, este método será el punto donde se conecte la
        persistencia (creación de grupos, sesiones, etc.).
        """

        # 1) Métricas básicas de lo que llega del frontend
        num_tablas_recibidas = len(data.horarios)
        num_sesiones_recibidas = sum(
            len(tabla.sesiones or [])
            for tabla in data.horarios
        )

        # 2) Reconstruir una estructura tipo ParsingResult usando el adaptador
        parsed_for_normalizer = build_parsing_result_for_normalization(data)

        # 3) Normalizar usando HorarioDataNormalizer (fail-soft)
        normalized_tablas = horario_data_normalizer.normalize_horarios(
            parsed_for_normalizer
        )

        num_tablas_normalizadas = len(normalized_tablas)
        num_sesiones_normalizadas = sum(
            len(tabla.sesiones)
            for tabla in normalized_tablas
        )

        # 4) Construir respuesta (sin persistencia todavía)
        return HorarioConfirmResponse(
            grupos=[],   # se rellenará cuando creemos grupos en BD
            sesiones=[],  # se rellenará cuando creemos sesiones en BD
            created_entities={
                "horarios_recibidos": num_tablas_recibidas,
                "sesiones_recibidas": num_sesiones_recibidas,
                "horarios_normalizados": num_tablas_normalizadas,
                "sesiones_normalizadas": num_sesiones_normalizadas,
            },
            warnings=[],
            errors=[],
        )