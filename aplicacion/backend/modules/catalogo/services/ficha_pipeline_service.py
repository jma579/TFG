"""
Servicio de Pipeline para Ingesta de Fichas Académicas.

Este servicio actúa como ORQUESTADOR del proceso End-to-End.
Integra los componentes del Core (Extracción, Parsing, Normalización) con
la capa de Persistencia, garantizando la integridad transaccional (ACID).
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Union

from sqlalchemy.orm import Session

from core.extraccion.fichas.extractor import FichaExtractor
from core.extraccion.fichas.parser import FichaParser
from core.extraccion.fichas.normalize import DataNormalizer
from core.extraccion.fichas.entities import (
    NormalizedFichaData,
    PipelineResult,
)
from constants.enums import TipoPrograma

from modules.catalogo.repositories.asignatura_repo import asignatura_repository
from modules.catalogo.repositories.programa_repo import programa_repository
from modules.catalogo.repositories.programa_asignatura_repo import programa_asignatura_repository
from modules.recursos.repositories.profesor_repo import profesor_repository
from modules.recursos.repositories.profesor_asignatura_repo import profesor_asignatura_repository


class FichaPipelineService:
    """
    Coordinador del flujo de procesamiento de fichas académicas.
    Gestiona el ciclo de vida completo desde la lectura del archivo hasta la confirmación en BD.
    """

    def __init__(self) -> None:
        """Inicializa el servicio con los componentes necesarios."""
        self.logger = logging.getLogger(__name__)
        
        self._extractor = FichaExtractor()
        self._parser = FichaParser()
        self._normalizer = DataNormalizer()

        self._asignatura_repo = asignatura_repository
        self._programa_repo = programa_repository
        self._programa_asignatura_repo = programa_asignatura_repository
        self._profesor_repo = profesor_repository
        self._profesor_asignatura_repo = profesor_asignatura_repository

    def procesar_ficha(
        self,
        pdf_path: Union[str, Path],
        db: Session,
    ) -> PipelineResult:
        """
        Ejecuta el pipeline de procesamiento de manera atómica.

        Realiza las siguientes fases:
        1. Extracción: Obtención del texto crudo desde el PDF.
        2. Parsing: Estructuración del texto en objetos de dominio.
        3. Normalización: Limpieza y estandarización de datos.
        4. Persistencia: Sincronización con la base de datos bajo una única transacción.

        Si ocurre cualquier error durante el proceso, se realiza un ROLLBACK automático
        para asegurar que la base de datos no quede en un estado inconsistente.

        Args:
            pdf_path: Ruta al archivo PDF fuente.
            db: Sesión de base de datos activa.

        Returns:
            PipelineResult: Objeto con el estado final, estadísticas y posibles errores.
        """
        path_str = str(pdf_path)

        try:
            extraction_result = self._extractor.extract_from_pdf(path_str)
            if not extraction_result.success or not extraction_result.is_usable:
                return PipelineResult(
                    success=False,
                    errors=[extraction_result.error_message or "Calidad de PDF insuficiente para procesamiento"],
                    metadata={"extraction_metadata": extraction_result.metadata},
                )

            ficha_raw = self._parser.parse_text(
                extraction_result.text,
                extraction_metadata=extraction_result.metadata,
            )

            normalized_data = self._normalizer.normalize_ficha(ficha_raw)

        except Exception as e:
            self.logger.error(f"Error en fases de procesamiento (Extracción/Parsing): {e}", exc_info=True)
            return PipelineResult(
                success=False,
                errors=[f"Error procesando el archivo: {str(e)}"],
            )

        created_stats: Dict[str, int] = {
            "asignaturas_creadas": 0,
            "asignaturas_actualizadas": 0,
            "programas_creados": 0,
            "relaciones_creadas": 0,
            "profesores_creados": 0,
        }

        try:           
            asignatura_id = self._upsert_asignatura(db, normalized_data, created_stats)
            programas_ids = self._sync_programas(db, normalized_data, asignatura_id, created_stats)
            profesores_ids = self._sync_profesores(db, normalized_data, asignatura_id, created_stats)
            db.commit()
            
            metadata = {
                "codigo": normalized_data.asignatura.codigo_plan,
                "nombre": normalized_data.asignatura.nombre,
                "extraction_quality": extraction_result.metadata.quality,
            }

            return PipelineResult(
                success=True,
                asignatura_id=asignatura_id,
                programas_asociados=programas_ids,
                profesores_asociados=profesores_ids,
                created_entities=created_stats,
                metadata=metadata,
            )

        except Exception as e:
            db.rollback()
            self.logger.error(f"Error de base de datos durante persistencia. Rollback ejecutado: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                errors=[f"Error de integridad de datos: {str(e)}"],
                created_entities=created_stats,
            )


    def _upsert_asignatura(
        self, db: Session, data: NormalizedFichaData, stats: Dict[str, int]
    ) -> int:
        """
        Crea o actualiza la asignatura basándose en su código único.
        Prioriza la información del PDF sobre la existente en BD.
        """
        asig_data = data.asignatura.model_dump()
        codigo = asig_data["codigo_plan"]

        existing = self._asignatura_repo.get_by_codigo(db, codigo)

        if existing:
            self._asignatura_repo.update(db, existing.id, asig_data)
            stats["asignaturas_actualizadas"] += 1
            return existing.id
        else:
            new_asig = self._asignatura_repo.create(db, asig_data)
            stats["asignaturas_creadas"] += 1
            return new_asig.id

    def _sync_programas(
        self, db: Session, data: NormalizedFichaData, asignatura_id: int, stats: Dict[str, int]
    ) -> List[int]:
        """
        Asegura que la asignatura esté vinculada a los programas detectados.
        Si un programa no existe, se crea automáticamente bajo demanda.
        """
        programas_ids = []

        for tit in data.titulaciones:
            tipo_inferido = self._infer_program_type(tit.programa_nombre)
            programa = self._programa_repo.get_by_nombre_tipo(
                db, tit.programa_nombre, tipo_inferido
            )

            if not programa:
                prog_data = {
                    "nombre": tit.programa_nombre,
                    "tipo": tipo_inferido,
                    "activo": True
                }
                programa = self._programa_repo.create(db, prog_data)
                stats["programas_creados"] += 1
            
            programas_ids.append(programa.id)

            rel = self._programa_asignatura_repo.get_by_programa_and_asignatura(
                db, programa.id, asignatura_id
            )

            if not rel:
                self._programa_asignatura_repo.create(
                    db,
                    programa_id=programa.id,
                    asignatura_id=asignatura_id,
                    curso=tit.curso,
                    tipo_asignatura=tit.tipo_asignatura
                )
                stats["relaciones_creadas"] += 1
            else:
                if rel.curso != tit.curso or rel.tipo_asignatura != tit.tipo_asignatura:
                    self._programa_asignatura_repo.update_tipo_curso_mencion(
                        db, programa_id=programa.id, asignatura_id=asignatura_id, 
                        curso=tit.curso, tipo_asignatura=tit.tipo_asignatura
                    )

        return programas_ids

    def _sync_profesores(
        self, db: Session, data: NormalizedFichaData, asignatura_id: int, stats: Dict[str, int]
    ) -> List[int]:
        """
        Sincroniza la asignación docente.
        Aplica una estrategia diferencial: añade los nuevos y elimina los que ya no figuran en el PDF.
        """
        profesores_pdf_ids = []

        for prof_data in data.profesores:
            profesor = self._profesor_repo.get_by_nombre_apellidos(
                db, prof_data.nombre, prof_data.apellidos
            )

            if not profesor:
                new_prof_data = {
                    "nombre": prof_data.nombre,
                    "apellidos": prof_data.apellidos,
                    "activo": True,
                }
                profesor = self._profesor_repo.create(db, new_prof_data)
                stats["profesores_creados"] += 1
            elif not profesor.activo:
                self._profesor_repo.update(db, profesor.id, {"activo": True})

            profesores_pdf_ids.append(profesor.id)

            if not self._profesor_asignatura_repo.exists(db, profesor.id, asignatura_id):
                self._profesor_asignatura_repo.create(db, profesor.id, asignatura_id)
                stats["relaciones_creadas"] += 1

        relaciones_db = self._profesor_asignatura_repo.get_by_asignatura(db, asignatura_id)
        
        for rel in relaciones_db:
            if rel.profesor_id not in profesores_pdf_ids:
                self._profesor_asignatura_repo.delete(db, rel.profesor_id, asignatura_id)

        return profesores_pdf_ids

    @staticmethod
    def _infer_program_type(nombre_programa: str) -> TipoPrograma:
        """Determina el tipo de programa basándose en convenciones de nomenclatura."""
        nombre_lower = nombre_programa.lower()
        if "doble" in nombre_lower:
            return TipoPrograma.DOBLE_GRADO
        if "máster" in nombre_lower or "master" in nombre_lower:
            return TipoPrograma.MASTER
        return TipoPrograma.GRADO