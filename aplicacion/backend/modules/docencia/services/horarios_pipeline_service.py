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
from sqlalchemy.orm import Session

from backend.core.extraccion.horarios.extractor import HorarioExtractor
from backend.core.extraccion.horarios.parser import HorarioParser
from backend.core.extraccion.horarios.normalize import horario_data_normalizer


from backend.modules.docencia.schemas.horarios import (
    HorarioTemporalOut, HorarioTemporalConfirmIn, HorarioConfirmResponse
)
from backend.modules.docencia.services.horarios_normalization_models import (
    build_parsing_result_for_normalization,
)
# from backend.modules.catalogo.repositories.asignatura_repo import asignatura_repository  # TODO futuro


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
    

    def confirmar_horario(self, db: Session, data: HorarioTemporalConfirmIn,) -> HorarioConfirmResponse:
        # 1) Métricas de lo que llega del frontend
        num_tablas_recibidas = len(data.horarios)
        num_sesiones_recibidas = sum(len(t.sesiones or []) for t in data.horarios)

        # 2) Reconstruir ParsingResult sintético
        parsed_for_normalizer = build_parsing_result_for_normalization(data)

        # 3) Normalizar
        normalized_tablas = horario_data_normalizer.normalize_horarios(parsed_for_normalizer)

        num_tablas_normalizadas = len(normalized_tablas)
        num_sesiones_normalizadas = sum(len(t.sesiones) for t in normalized_tablas)

        # 4) Estructuras auxiliares (para futuro)
        grupos_creados = []
        sesiones_creadas = []
        warnings = []

        # Caches en memoria (para no machacar la BD a queries)
        # TODO FUTURO: cuando haya catálogo de asignaturas y aulas consolidadas,
        # descomentar y usar caches de búsqueda por nombre normalizado.
        #
        # asignaturas_cache = asignatura_repository.get_all_indexed_by_nombre(db)
        # aulas_cache = aula_repository.get_all_indexed_by_nombre(db)

        # 5) Recorrer tablas normalizadas y (en el futuro) persistir
        for tabla in normalized_tablas:
            for ses in tabla.sesiones:
                # AQUÍ iría la lógica de:
                # - Resolver asignatura por nombre → asignatura_id
                # - Resolver aula por nombre → aula_id
                # - Resolver/crear grupo docente por (asignatura_id, tipo, codigo)
                # - Crear sesión

                # -----------------------------
                # BLOQUE DE COMPROBACIÓN POR NOMBRE (COMENTADO)
                # -----------------------------
                #
                # # 5.1. Resolver asignatura por nombre
                # asignatura = asignaturas_cache.get(ses.asignatura_nombre_normalizado)
                # if not asignatura:
                #     warnings.append(
                #         f"Asig. no encontrada en catálogo: {ses.asignatura_nombre_normalizado}"
                #     )
                #     continue  # ← ESTA PARTE ES LA QUE QUERÍAS EVITAR AHORA
                #
                # # 5.2. Resolver aula por nombre
                # aula = aulas_cache.get(ses.aula_nombre_normalizado)
                # if not aula:
                #     warnings.append(
                #         f"Aula no encontrada en recursos: {ses.aula_nombre_normalizado}"
                #     )
                #     continue  # ← Y ESTA TAMBIÉN

                # -----------------------------
                # A PARTIR DE AQUÍ, PERSISTENCIA REAL
                # -----------------------------
                # ⚠️ Aquí necesitaríamos disponer de:
                # - asignatura_id (de algún sitio: DTO, mapeo manual, etc.)
                # - aula_id (igual)
                #
                # Ejemplo ideal (cuando tengamos IDs):
                #
                # grupo_in = GrupoDocenteCreate(
                #     asignatura_id=asignatura.id,
                #     codigo=ses.grupo_codigo or "T1",
                #     tipo=ses.tipo_grupo,
                #     curso=tabla.curso,
                #     turno=None,
                # )
                # grupo = grupo_docente_repository.create(db, grupo_in)
                # grupos_creados.append(grupo)
                #
                # sesion_in = SesionCreate(
                #     grupo_docente_id=grupo.id,
                #     aula_id=aula.id,
                #     modalidad=ses.modalidad,          # p.ej. PRESENCIAL
                #     tipo_recurrencia=ses.tipo_recurrencia,  # SEMANAL
                #     dia_semana=ses.dia_semana,
                #     hora_inicio=ses.hora_inicio,
                #     hora_fin=ses.hora_fin,
                #     profesores=[],  # por ahora vacío
                # )
                # sesion = sesion_repository.create(db, sesion_in)
                # sesiones_creadas.append(sesion)
                ...

        # 6) Construir respuesta (por ahora, sin grupos/sesiones reales si no tienes IDs)
        return HorarioConfirmResponse(

            grupos=[],   # o mapear grupos_creados → GrupoDocenteOut cuando lo actives
            sesiones=[],  # idem sesiones_creadas → SesionOut
            created_entities={
                "horarios_recibidos": num_tablas_recibidas,
                "sesiones_recibidas": num_sesiones_recibidas,
                "horarios_normalizados": num_tablas_normalizadas,
                "sesiones_normalizadas": num_sesiones_normalizadas,
                # "grupos_creados": len(grupos_creados),
                # "sesiones_creadas": len(sesiones_creadas),
            },
            warnings=warnings,
            errors=[],
        )