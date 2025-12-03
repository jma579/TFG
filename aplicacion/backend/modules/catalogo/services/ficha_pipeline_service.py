"""Servicio de orquestación para el flujo de fichas académicas.

Este servicio coordina las distintas fases del pipeline de fichas:
- extracción de texto a partir de un PDF de ficha (FichaExtractor)
- parsing del texto en una ficha estructurada (FichaParser)
- normalización de los datos (DataNormalizer)
- persistencia en base de datos (asignatura + programas + relación programa-asignatura)

En esta primera versión **no** se persisten profesores ni menciones.
Los profesores se dejan como posible evolución futura del pipeline
cuando se acuerde la estrategia de modelado con la tutora del TFG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

from sqlalchemy.orm import Session

from backend.constants.enums import TipoPrograma

# Core de extracción de fichas
from backend.core.extraccion.fichas.extractor import FichaExtractor
from backend.core.extraccion.fichas.parser import FichaParser
from backend.core.extraccion.fichas.normalize import DataNormalizer
from backend.core.extraccion.fichas.entities import (
    NormalizedFichaData,
    PipelineResult,
)

# Servicios y repositorios de catálogo
from backend.modules.catalogo.schemas.asignatura import (
    AsignaturaCreate,
    AsignaturaUpdate,
)
from backend.modules.catalogo.schemas.programa import ProgramaCreate
from backend.modules.catalogo.services.asignatura_service import AsignaturaService
from backend.modules.catalogo.services.programa_service import ProgramaService
from backend.modules.catalogo.repositories.asignatura_repo import asignatura_repository
from backend.modules.catalogo.repositories.programa_repo import programa_repository
from backend.modules.catalogo.repositories.programa_asignatura_repo import (
    programa_asignatura_repository,
)
from backend.modules.recursos.schemas.profesor import ProfesorCreate
from backend.modules.recursos.services.profesor_service import ProfesorService
from backend.modules.recursos.repositories.profesor_repo import profesor_repository
from backend.modules.recursos.repositories.profesor_asignatura_repo import (
    profesor_asignatura_repository,
)


class FichaPipelineService:
    """Servicio de alto nivel para el flujo de fichas académicas.

    Responsable de exponer una API de Python sencilla para los routers FastAPI,
    escondiendo los detalles de extractor, parser, normalizador y persistencia.

    Uso típico desde un endpoint:

        service = FichaPipelineService()
        result = service.procesar_ficha(pdf_path, db)

    El output es un ``PipelineResult`` definido en
    ``core.extraccion.fichas.entities`` que resume el resultado global
    del procesamiento y las entidades creadas/actualizadas.
    """

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    def __init__(self) -> None:

        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        # Componentes del pipeline de extracción/parseo/normalización
        self._extractor = FichaExtractor()
        self._parser = FichaParser()
        self._normalizer = DataNormalizer()

        # Servicios de dominio
        self._asignatura_service = AsignaturaService()
        self._programa_service = ProgramaService()
        self._profesor_service = ProfesorService()

        # Repositorios auxiliares
        self._asignatura_repo = asignatura_repository
        self._programa_repo = programa_repository
        self._programa_asignatura_repo = programa_asignatura_repository
        self._profesor_repo = profesor_repository
        self._profesor_asignatura_repo = profesor_asignatura_repository

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def procesar_ficha(
        self,
        pdf_path: Union[str, Path],
        db: Session,
    ) -> PipelineResult:
        """Ejecuta el pipeline completo de fichas y persiste en BD.

        Flujo:
        1) Extraer texto y metadatos del PDF (FichaExtractor)
        2) Parsear el texto a ``SubjectSheet`` (FichaParser)
        3) Normalizar a ``NormalizedFichaData`` (DataNormalizer)
        4) Crear/actualizar Asignatura
        5) Crear/actualizar Programas
        6) Crear relaciones Programa-Asignatura

        En esta versión **no** se persisten profesores ni menciones.

        Args:
            pdf_path: Ruta al archivo PDF de la ficha a procesar.
            db: Sesión de base de datos activa.

        Returns:
            PipelineResult con información sobre la asignatura creada/actualizada,
            programas asociados y contadores de entidades creadas.
        """

        # Aseguramos que trabajamos siempre con una cadena de texto
        path_str = str(pdf_path)

        # ------------------------------------------------------------------
        # 1) Extracción de texto a partir del PDF
        # ------------------------------------------------------------------
        extraction_result = self._extractor.extract_from_pdf(path_str)

        if not extraction_result.success or not extraction_result.is_usable:
            # Error en extracción: devolvemos un PipelineResult fallido.
            # El router podrá decidir si mapearlo a un HTTP 4xx/5xx.
            return PipelineResult(
                success=False,
                asignatura_id=None,
                programas_asociados=[],
                profesores_asociados=[],
                created_entities={},
                errors=[
                    extraction_result.error_message
                    or "Error en la extracción de la ficha (PDF no usable)"
                ],
                metadata={
                    "extraction_metadata": extraction_result.metadata,
                },
            )

        # ------------------------------------------------------------------
        # 2) Parsing del texto a entidad semántica (SubjectSheet)
        # ------------------------------------------------------------------
        ficha = self._parser.parse_text(
            extraction_result.text,
            extraction_metadata=extraction_result.metadata,
        )

        # ------------------------------------------------------------------
        # 3) Normalización (tipos correctos, enums, limpieza de strings...)
        # ------------------------------------------------------------------
        normalized: NormalizedFichaData = self._normalizer.normalize_ficha(ficha)

        # ------------------------------------------------------------------
        # 4) Persistencia en BD
        # ------------------------------------------------------------------
        created_entities: Dict[str, int] = {
            "asignaturas_creadas": 0,
            "asignaturas_actualizadas": 0,
            "programas_creados": 0,
            "relaciones_programa_asignatura_creadas": 0,
            "profesores_creados": 0,
            "relaciones_profesor_asignatura_creadas": 0,
        }

        # 4.1) Crear o actualizar Asignatura
        asignatura_id = self._persist_asignatura(db, normalized, created_entities)

        # 4.2) Crear o actualizar Programas + relación Programa-Asignatura
        programas_asociados = self._persist_programas_y_relaciones(
            db, normalized, asignatura_id, created_entities
        )

        # 4.3) Crear o asociar Profesores + relación Profesor-Asignatura
        profesores_asociados = self._persist_profesores_y_relaciones(
            db, normalized, asignatura_id, created_entities
        )

        # ------------------------------------------------------------------
        # 5) Construir PipelineResult final
        # ------------------------------------------------------------------
        metadata = {
            "codigo_plan": normalized.asignatura.codigo_plan,
            "nombre_asignatura": normalized.asignatura.nombre,
            "programa_nombres": [
                t.programa_nombre for t in normalized.titulaciones
            ],
        }

        return PipelineResult(
            success=True,
            asignatura_id=asignatura_id,
            programas_asociados=programas_asociados,
            profesores_asociados=profesores_asociados,
            created_entities=created_entities,
            errors=[],
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Métodos internos de persistencia
    # ------------------------------------------------------------------

    def _persist_asignatura(
        self,
        db: Session,
        normalized: NormalizedFichaData,
        created_entities: Dict[str, int],
    ) -> int:
        """Crear o actualizar la Asignatura a partir de los datos normalizados.

        Estrategia:
        - Buscar por ``codigo_plan`` en el repositorio
        - Si existe → actualizar usando ``AsignaturaUpdate``
        - Si no existe → crear usando ``AsignaturaCreate``

        Devuelve el ``id`` de la asignatura en BD.
        """

        asig = normalized.asignatura

        # ¿Existe ya una asignatura con este código de plan?
        existing = self._asignatura_repo.get_by_codigo(db, asig.codigo_plan)

        if existing is None:
            # Crear nueva asignatura
            asig_create = AsignaturaCreate(
                codigo_plan=asig.codigo_plan,
                nombre=asig.nombre,
                periodo=asig.periodo,
                ects=asig.ects,
                modalidad=asig.modalidad,
                idioma=asig.idioma,
                english_friendly=asig.english_friendly,
                activo=True,
            )

            asig_out = self._asignatura_service.create_asignatura(db, asig_create)
            created_entities["asignaturas_creadas"] += 1
            return asig_out.id

        # Actualizar asignatura existente (idempotente)
        asig_update = AsignaturaUpdate(
            codigo_plan=asig.codigo_plan,
            nombre=asig.nombre,
            periodo=asig.periodo,
            ects=asig.ects,
            modalidad=asig.modalidad,
            idioma=asig.idioma,
            english_friendly=asig.english_friendly,
            activo=True,
        )

        asig_out = self._asignatura_service.update_asignatura(
            db,
            asignatura_id=existing.id,
            asignatura_in=asig_update,
        )
        created_entities["asignaturas_actualizadas"] += 1
        return asig_out.id

    def _persist_programas_y_relaciones(
        self,
        db: Session,
        normalized: NormalizedFichaData,
        asignatura_id: int,
        created_entities: Dict[str, int],
    ) -> List[int]:
        """Crear/actualizar Programas y relaciones Programa-Asignatura.

        Para cada titulación normalizada:
        - Determinar el tipo de programa a partir del nombre (heurística sencilla)
        - Buscar Programa por (nombre, tipo)
        - Crear si no existe
        - Crear relación Programa-Asignatura si no existe

        Devuelve la lista de IDs de programas asociados a la asignatura.
        """

        programas_ids: List[int] = []

        for tit in normalized.titulaciones:
            # 1) Inferir tipo de programa a partir del nombre
            programa_tipo = self._infer_program_type(tit.programa_nombre)

            # 2) Buscar programa existente por (nombre, tipo)
            programa = self._programa_repo.get_by_nombre_tipo(
                db,
                nombre=tit.programa_nombre,
                tipo=programa_tipo,
            )

            if programa is None:
                # Crear nuevo programa
                prog_create = ProgramaCreate(
                    nombre=tit.programa_nombre,
                    tipo=programa_tipo,
                    activo=True,
                )
                prog_out = self._programa_service.create_programa(db, prog_create)
                programa_id = prog_out.id
                created_entities["programas_creados"] += 1
            else:
                programa_id = programa.id

            if programa_id not in programas_ids:
                programas_ids.append(programa_id)

            # 3) Crear relación Programa-Asignatura si no existe
            if not self._programa_asignatura_repo.exists(db, programa_id, asignatura_id):
                self._programa_asignatura_repo.create(
                    db,
                    programa_id=programa_id,
                    asignatura_id=asignatura_id,
                    curso=tit.curso,
                    tipo_asignatura=tit.tipo_asignatura,
                )
                created_entities["relaciones_programa_asignatura_creadas"] += 1

        return programas_ids

    def _persist_profesores_y_relaciones(
        self,
        db: Session,
        normalized: NormalizedFichaData,
        asignatura_id: int,
        created_entities: Dict[str, int],
    ) -> List[int]:
        """Crear/actualizar Profesores y relaciones Profesor-Asignatura.

        Estrategia conservadora:
        - Para cada profesor normalizado (nombre + apellidos):
          - Buscar por nombre y apellidos (búsqueda normalizada en el repositorio)
          - Si existe: reutilizar
          - Si no existe: crear nuevo profesor con campos mínimos
        - Crear relación Profesor-Asignatura si no existe.

        Devuelve la lista de IDs de profesores asociados a la asignatura.
        """

        profesores_ids: List[int] = []

        for prof in normalized.profesores:
            # 1) Buscar profesor existente por nombre + apellidos
            existing = self._profesor_repo.get_by_nombre_apellidos(
                db,
                nombre=prof.nombre,
                apellidos=prof.apellidos,
            )

            if existing is None:
                # Crear profesor nuevo con datos mínimos
                prof_create = ProfesorCreate(
                    nombre=prof.nombre,
                    apellidos=prof.apellidos,
                    email=None,
                    telefono=None,
                    departamento=None,
                    activo=True,
                )
                prof_out = self._profesor_service.create(db, prof_create)
                profesor_id = prof_out.id
                created_entities["profesores_creados"] += 1
            else:
                profesor_id = existing.id

            if profesor_id not in profesores_ids:
                profesores_ids.append(profesor_id)

            # 2) Crear relación Profesor-Asignatura si no existe
            if not self._profesor_asignatura_repo.exists(db, profesor_id, asignatura_id):
                self._profesor_asignatura_repo.create(
                    db,
                    profesor_id=profesor_id,
                    asignatura_id=asignatura_id,
                )
                created_entities["relaciones_profesor_asignatura_creadas"] += 1

        return profesores_ids

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_program_type(nombre_programa: str) -> TipoPrograma:
        """Inferir TipoPrograma a partir del nombre del programa.

        Heurística sencilla basada en palabras clave típicas de la facultad:
        - Si contiene "doble" → DOBLE_GRADO
        - Si contiene "máster" o "master" → MASTER
        - En otro caso → GRADO

        Esta lógica se puede refinar más adelante si se incorporan
        nuevos tipos de programas o convenciones de nomenclatura.
        """

        nombre_lower = nombre_programa.lower()

        if "doble" in nombre_lower:
            return TipoPrograma.DOBLE_GRADO

        if "máster" in nombre_lower or "master" in nombre_lower:
            return TipoPrograma.MASTER

        return TipoPrograma.GRADO
