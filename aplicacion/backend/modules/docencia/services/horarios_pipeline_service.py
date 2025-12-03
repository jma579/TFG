from __future__ import annotations

from typing import Dict, List, Optional, Union
from pathlib import Path
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database.models import Asignatura, Aula
from backend.modules.docencia.schemas.horarios import (
    HorarioTemporalOut, HorarioTemporalConfirmIn, HorarioConfirmResponse
)
from backend.modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate,
    GrupoDocenteOut,
)
from backend.modules.docencia.schemas.sesion import SesionCreate, SesionOut
from backend.modules.docencia.services.grupo_docente_service import (
    grupo_docente_service,
)
from backend.modules.docencia.services.sesion_service import sesion_service
from backend.core.extraccion.horarios.extractor import HorarioExtractor
from backend.core.extraccion.horarios.parser import HorarioParser

from backend.core.extraccion.horarios.normalize import horario_data_normalizer
from backend.modules.docencia.services.horarios_normalization_models import (
    build_parsing_result_for_normalization,
)


class HorariosPipelineService:
    """Servicio de orquestación del flujo de horarios.

    Esta implementación de `confirmar_horario`:
    - Recibe el horario confirmado desde el frontend.
    - Reconstruye un resultado de parsing sintético.
    - Normaliza las tablas/sesiones a dominio.
    - Resuelve asignaturas, grupos y aulas contra la BD.
    - Crea sesiones usando la capa de servicio de docencia.
    - Devuelve los grupos/sesiones creados y métricas de apoyo.
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

    def confirmar_horario(
        self,
        db: Session,
        data: HorarioTemporalConfirmIn,
    ) -> HorarioConfirmResponse:
        """Confirmar un horario temporal y persistirlo en BD.

        Pasos principales:
        1. Métricas de entrada.
        2. Reconstrucción del resultado de parsing para el normalizador.
        3. Normalización de las tablas/sesiones.
        4. Resolución de asignaturas, grupos y aulas.
        5. Creación de sesiones vía capa de servicio.
        6. Construcción de la respuesta con métricas y advertencias.
        """

        # 1) Métricas de lo que llega del frontend
        num_tablas_recibidas = len(data.horarios)
        num_sesiones_recibidas = sum(len(t.sesiones or []) for t in data.horarios)

        # 2) Reconstruir ParsingResult sintético para el normalizador
        parsed_for_normalizer = build_parsing_result_for_normalization(data)

        # 3) Normalizar
        normalized_tablas = horario_data_normalizer.normalize_horarios(
            parsed_for_normalizer
        )

        num_tablas_normalizadas = len(normalized_tablas)
        num_sesiones_normalizadas = sum(
            len(t.sesiones or []) for t in normalized_tablas
        )

        warnings: List[str] = []
        errors: List[str] = []

        # Caches en memoria para evitar queries repetidas
        asignatura_cache: Dict[str, Optional[Asignatura]] = {}
        aula_cache: Dict[str, Optional[Aula]] = {}
        grupos_cache: Dict[tuple[int, str], GrupoDocenteOut] = {}

        # Resultados a devolver
        grupos_resultado: Dict[int, GrupoDocenteOut] = {}
        sesiones_resultado: List[SesionOut] = []

        grupos_creados = 0
        grupos_reutilizados = 0
        sesiones_creadas = 0

        # 4) Recorrer tablas y sesiones normalizadas
        for idx_tabla, tabla in enumerate(normalized_tablas):
            sesiones_tabla = tabla.sesiones or []

            for idx_sesion, sesion_norm in enumerate(sesiones_tabla):
                # -----------------------------
                # 4.1) Resolver asignatura por nombre
                # -----------------------------
                asignatura_nombre = sesion_norm.asignatura_nombre

                if not asignatura_nombre:
                    warnings.append(
                        f"Sesión en tabla {idx_tabla + 1}, índice {idx_sesion + 1}: "
                        "sin nombre de asignatura normalizado; no se persiste."
                    )
                    continue

                asignatura_key = asignatura_nombre.strip().lower()

                if asignatura_key in asignatura_cache:
                    asignatura = asignatura_cache[asignatura_key]
                else:
                    asignatura = (
                        db.query(Asignatura)
                        .filter(Asignatura.nombre.ilike(asignatura_nombre.strip()))
                        .one_or_none()
                    )
                    asignatura_cache[asignatura_key] = asignatura

                if asignatura is None:
                    warnings.append(
                        "No se encontró la asignatura "
                        f"'{asignatura_nombre}' en el catálogo; "
                        f"sesión en tabla {idx_tabla + 1}, índice {idx_sesion + 1} "
                        "no se ha persistido."
                    )
                    continue

                # -----------------------------
                # 4.2) Resolver / crear grupo docente
                # -----------------------------
                grupo_codigo_norm = sesion_norm.grupo_codigo.strip().upper()
                grupo_key = (asignatura.id, grupo_codigo_norm)

                grupo_out = grupos_cache.get(grupo_key)

                if grupo_out is None:
                    # Intentar recuperar un grupo existente para (asignatura, codigo)
                    try:
                        grupo_out = grupo_docente_service.get_by_asignatura_codigo(
                            db=db,
                            asignatura_id=asignatura.id,
                            codigo=grupo_codigo_norm,
                        )
                        grupos_reutilizados += 1
                    except HTTPException as exc:  # grupo no encontrado u otro error
                        if exc.status_code == status.HTTP_404_NOT_FOUND:
                            # Crear un grupo nuevo
                            grupo_in = GrupoDocenteCreate(
                                asignatura_id=asignatura.id,
                                codigo=grupo_codigo_norm,
                                tipo=sesion_norm.tipo_grupo,
                                curso=tabla.curso,
                                turno=None,
                            )
                            grupo_out = grupo_docente_service.create(db, grupo_in)
                            grupos_creados += 1
                        else:
                            # Para otros errores (409, etc.) dejamos propagar
                            raise

                    grupos_cache[grupo_key] = grupo_out
                    grupos_resultado[grupo_out.id] = grupo_out

                # -----------------------------
                # 4.3) Resolver aula
                # -----------------------------
                aula_nombre = sesion_norm.aula_nombre

                if not aula_nombre:
                    warnings.append(
                        "Sesión para asignatura "
                        f"'{asignatura_nombre}' sin aula normalizada; "
                        f"tabla {idx_tabla + 1}, índice {idx_sesion + 1} "
                        "no se ha persistido."
                    )
                    continue

                aula_key = aula_nombre.strip().lower()

                if aula_key in aula_cache:
                    aula = aula_cache[aula_key]
                else:
                    aula = (
                        db.query(Aula)
                        .filter(Aula.nombre.ilike(aula_nombre.strip()))
                        .one_or_none()
                    )
                    aula_cache[aula_key] = aula

                if aula is None:
                    warnings.append(
                        f"No se encontró el aula normalizada '{aula_nombre}'; "
                        f"sesión en tabla {idx_tabla + 1}, índice {idx_sesion + 1} "
                        "no se ha persistido."
                    )
                    continue

                # -----------------------------
                # 4.4) Construir SesionCreate a partir del modelo normalizado
                # -----------------------------
                sesion_in = SesionCreate(
                    grupo_docente_id=grupo_out.id,
                    aula_id=aula.id,
                    modalidad=sesion_norm.modalidad,
                    tipo_recurrencia=sesion_norm.tipo_recurrencia,
                    dia_semana=sesion_norm.dia_semana,
                    hora_inicio=sesion_norm.hora_inicio,
                    hora_fin=sesion_norm.hora_fin,
                    inicio=None,  # el normalizador actual no maneja sesiones puntuales
                    fin=None,
                    profesores=[],  # el flujo de horarios no asigna profesores todavía
                )

                sesion_out = sesion_service.create(db, sesion_in)
                sesiones_resultado.append(sesion_out)
                sesiones_creadas += 1

        # 5) Construir métricas de entidades creadas / procesadas
        created_entities = {
            "horarios_recibidos": num_tablas_recibidas,
            "sesiones_recibidas": num_sesiones_recibidas,
            "horarios_normalizados": num_tablas_normalizadas,
            "sesiones_normalizadas": num_sesiones_normalizadas,
            "grupos_creados": grupos_creados,
            "grupos_reutilizados": grupos_reutilizados,
            "sesiones_creadas": sesiones_creadas,
        }

        # 6) Construir respuesta
        return HorarioConfirmResponse(
            grupos=list(grupos_resultado.values()),
            sesiones=sesiones_resultado,
            created_entities=created_entities,
            warnings=warnings,
            errors=errors,
        )
