"""Normalización de datos extraídos de horarios académicos.

Responsabilidades:
- Limpiar y normalizar nombres de asignaturas y menciones
- Mapear días de la semana a enums
- Mapear tipos de sesión del parser a TipoGrupoDocente / ModalidadSesion
- Inferir códigos de grupo cuando falten
- Inferir tipos de aula básicos a partir del nombre
- Mapear periodos a enums

Flujo:
    ParsingResult (datos crudos) → HorarioDataNormalizer.normalize_horarios()
    → List[NormalizedHorarioTablaData] (datos listos para la capa de BD)

IMPORTANTE:
- Esta capa NO interactúa con la base de datos
- No intenta detectar duplicados ni resolver IDs
- Se limita a dejar los datos en un formato coherente con los enums y modelos
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional

from backend.core.extraccion.horarios.entities import (
    ParsingResult,
    Horario as ParsedHorario,
    Sesion as ParsedSesion,
    NormalizedHorarioTablaData,
    NormalizedSesionHorarioData,
)
from backend.core.extraccion.horarios.constants import (
    DIA_SEMANA_MAP,
    PERIODO_MAP,
    AULA_KEYWORDS,
    CURSO_MAP,
    CURSO_MIN,
    CURSO_MAX,
    PATRON_NUMERO_ROMANO,
    GRUPO_DEFAULT_TEORIA,
    GRUPO_DEFAULT_PRACTICA,
)
from backend.constants.enums import (
    DiaSemana,
    Periodo,
    TipoGrupoDocente,
    TipoAula,
)


logger = logging.getLogger(__name__)


class HorarioDataNormalizer:
    """Normaliza datos extraídos de horarios académicos.

    Transforma el ParsingResult del parser de horarios en entidades
    NormalizedHorarioTablaData + NormalizedSesionHorarioData listas para
    ser consumidas por la capa de persistencia.
    """

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def normalize_horarios(self, parsed: ParsingResult) -> List[NormalizedHorarioTablaData]:
        """Normaliza un ParsingResult completo.

        Esta operación debe ser *fail-soft*: nunca debe tumbar el flujo completo
        por culpa de una tabla mal formada. Si una tabla no se puede
        normalizar, se descarta y se registra un warning.

        Args:
            parsed: Resultado del parser de horarios.

        Returns:
            Lista de horarios normalizados (uno por tabla/curso/página).
        """
        resultados: List[NormalizedHorarioTablaData] = []

        programa_nombre = self._normalize_nombre(parsed.titulo)

        for horario in parsed.horarios:
            try:
                normalizado = self._normalize_horario_tabla(
                    programa_nombre=programa_nombre,
                    horario=horario,
                )
            except Exception as exc:
                logger.warning(
                    "Horario descartado en normalización: %s (curso=%r, periodo=%r)",
                    exc,
                    getattr(horario, "curso", None),
                    getattr(horario, "periodo", None),
                )
                continue

            # Si una tabla no deja ninguna sesión válida, no tiene mucho sentido
            # mantenerla en la salida
            if not normalizado.sesiones:
                logger.warning(
                    "Horario sin sesiones válidas descartado (curso=%r, periodo=%r)",
                    getattr(horario, "curso", None),
                    getattr(horario, "periodo", None),
                )
                continue

            resultados.append(normalizado)

        return resultados

    # ------------------------------------------------------------------
    # Normalizadores específicos
    # ------------------------------------------------------------------

    def _normalize_horario_tabla(
        self,
        programa_nombre: str,
        horario: ParsedHorario,
    ) -> NormalizedHorarioTablaData:
        """Normaliza una tabla de horario concreta (un curso/mención/página).

        Esta operación también debe ser *fail-soft* a nivel de sesión: si una
        sesión individual no se puede normalizar, se descarta y se registra un
        warning, pero el resto de sesiones de la tabla continúan
        procesándose.
        """

        curso = self._parse_curso(horario.curso)
        periodo_enum = self._map_periodo(horario.periodo)
        mencion = self._normalize_mencion(horario.mencion)

        sesiones_norm: List[NormalizedSesionHorarioData] = []
        for sesion in horario.sesiones:
            try:
                sesiones_norm.append(
                    self._normalize_sesion(
                        sesion=sesion,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Sesión descartada en normalización: %s (asignatura=%r, dia=%r, hora_inicio=%r, hora_fin=%r)",
                    exc,
                    getattr(sesion, "asignatura", None),
                    getattr(sesion, "dia", None),
                    getattr(sesion, "hora_inicio", None),
                    getattr(sesion, "hora_fin", None),
                )
                continue

        return NormalizedHorarioTablaData(
            programa_nombre=programa_nombre,
            curso=curso,
            periodo=periodo_enum,
            mencion=mencion,
            sesiones=sesiones_norm,
        )

    def _normalize_sesion(self, sesion: ParsedSesion) -> NormalizedSesionHorarioData:
        """Normaliza una sesión individual del horario."""

        asignatura_nombre = self._normalize_nombre(sesion.asignatura)
        dia_semana = self._map_dia_semana(sesion.dia)

        grupo_codigo, tipo_grupo = self._infer_tipo_grupo_y_codigo(
            sesion.tipo,
            sesion.grupo,
        )

        aula_nombre_norm = self._normalize_aula_nombre(sesion.aula)
        aula_tipo = self._infer_aula_tipo(aula_nombre_norm)

        return NormalizedSesionHorarioData(
            asignatura_nombre=asignatura_nombre,
            grupo_codigo=grupo_codigo,
            tipo_grupo=tipo_grupo,
            dia_semana=dia_semana,
            hora_inicio=sesion.hora_inicio,
            hora_fin=sesion.hora_fin,
            aula_nombre=aula_nombre_norm,
            aula_tipo=aula_tipo,
        )

    # ------------------------------------------------------------------
    # Helpers de mapeo / normalización de campos simples
    # ------------------------------------------------------------------

    def _normalize_nombre(self, nombre: str) -> str:
        """Normalizar nombres (asignaturas, programas, etc.).

        - strip()
        - colapsar espacios múltiples
        - title case
        - pequeñas correcciones de números romanos
        """
        nombre = (nombre or "").strip()
        nombre = re.sub(r"\s+", " ", nombre)
        nombre = nombre.title()

        # Corregir números romanos comunes usando PATRON_NUMERO_ROMANO
        for patron, repl in PATRON_NUMERO_ROMANO.items():
            nombre = re.sub(patron, repl, nombre)

        return nombre

    def _normalize_mencion(self, mencion: Optional[str]) -> Optional[str]:
        """Normalizar texto de mención (si existe)."""
        if not mencion:
            return None
        mencion = mencion.strip()
        if not mencion:
            return None
        return self._normalize_nombre(mencion)

    def _map_periodo(self, periodo: str) -> Periodo:
        """Mapear texto de periodo a enum Periodo.

        En caso de no reconocer el periodo se lanza ValueError. Este error
        será capturado en niveles superiores para descartar la tabla.
        """
        if not periodo:
            raise ValueError("Periodo vacío en horario")

        # Normalizamos el texto de entrada
        p = periodo.strip().lower()

        # Quitar tildes y variantes típicas
        p = (
            p.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        # Intentar match directo después de normalizar
        # (también normalizamos las claves del PERIODO_MAP)
        def _norm(s: str) -> str:
            s = s.strip().lower()
            return (
                s.replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
            )

        # 1) Match exacto con alguna clave
        for key, value in PERIODO_MAP.items():
            if _norm(key) == p:
                return value

        # 2) Match parcial: alguna clave está contenida en el texto
        for key, value in PERIODO_MAP.items():
            if _norm(key) in p:
                return value

        # Si hemos llegado hasta aquí, no hemos sabido mapear el periodo
        raise ValueError(f"Periodo de horario desconocido: {periodo!r}")


    def _map_dia_semana(self, dia: str) -> DiaSemana:
        """Mapear texto de día de la semana a enum DiaSemana."""
        if not dia:
            raise ValueError("Día vacío en sesión de horario")

        d = dia.strip().lower()

        # Normalizar tildes comunes
        d = d.replace("miércoles", "miercoles").replace("sábado", "sabado")

        if d in DIA_SEMANA_MAP:
            return DIA_SEMANA_MAP[d]

        # Intentar match parcial (p.ej. "lun" → LUNES)
        for key, value in DIA_SEMANA_MAP.items():
            if d.startswith(key[:3]):
                return value

        raise ValueError(f"Día de la semana desconocido: {dia!r}")

    def _infer_tipo_grupo_y_codigo(
        self,
        tipo: Optional[str],
        grupo: Optional[str],
    ) -> tuple[str, TipoGrupoDocente]:
        """Inferir tipo de grupo (TEORIA vs PRACTICA) + código básico.

        Reglas (heurísticas):
        - Si el texto del tipo contiene "práctica"/"practica" → PRACTICA
        - Si el grupo empieza por "PA","PB","PC","PL" → PRACTICA
        - En otro caso se asume TEORIA
        - Si falta el grupo, se asigna un código por defecto distinto para
          teoría vs práctica.
        """
        tipo_valor = (tipo or "").strip().lower()
        grupo_valor = (grupo or "").strip().upper()

        # Inferir tipo de grupo
        if "práctica" in tipo_valor or "practica" in tipo_valor:
            tipo_enum = TipoGrupoDocente.PRACTICA
        else:
            tipo_enum = TipoGrupoDocente.TEORIA

        # Ajustar según prefijo de grupo
        if grupo_valor.startswith(("PA", "PB", "PC", "PL")):
            tipo_enum = TipoGrupoDocente.PRACTICA

        # Código de grupo
        if grupo_valor:
            codigo = grupo_valor
        else:
            codigo = GRUPO_DEFAULT_PRACTICA if tipo_enum is TipoGrupoDocente.PRACTICA else GRUPO_DEFAULT_TEORIA

        return codigo, tipo_enum

    def _normalize_aula_nombre(self, aula: Optional[str]) -> str:
        """Normalizar nombre de aula: strip, upper, colapsar espacios."""
        if not aula:
            return "DESCONOCIDA"

        nombre = aula.strip().upper()
        nombre = re.sub(r"\s+", " ", nombre)
        return nombre

    def _infer_aula_tipo(self, aula_nombre: str) -> TipoAula:
        """Inferir tipo de aula a partir del nombre textual.

        Usa heurísticas simples basadas en palabras clave definidas en
        AULA_KEYWORDS.
        """
        texto = aula_nombre.lower()

        # Laboratorio
        for keyword in AULA_KEYWORDS["laboratorio"]:
            if keyword in texto:
                return TipoAula.LABORATORIO

        # Informática
        for keyword in AULA_KEYWORDS["informatica"]:
            if keyword in texto:
                return TipoAula.INFORMATICA

        # Seminario
        for keyword in AULA_KEYWORDS["seminario"]:
            if keyword in texto:
                return TipoAula.SEMINARIO

        # Teórica (aula genérica)
        for keyword in AULA_KEYWORDS["teorica"]:
            if keyword in texto:
                return TipoAula.TEORICA

        # Por defecto, consideramos aula teórica genérica
        return TipoAula.TEORICA

    def _parse_curso(self, curso_str: str) -> int:
        """Parsear curso textual a entero (1-4).

        Se aceptan formatos como "1º", "1", "PRIMERO", etc., según CURSO_MAP.
        """
        if not curso_str:
            raise ValueError("Curso vacío en horario")

        s = curso_str.strip().lower()

        # Intentar usar el mapa de curso primero
        for key, value in CURSO_MAP.items():
            if key in s:
                return value

        # Si no se encuentra en el mapa, intentar parsear como entero directo
        try:
            valor = int(s)
        except ValueError as exc:
            raise ValueError(f"No se pudo parsear curso: {curso_str!r}") from exc

        # Validar rango usando constantes
        if not (CURSO_MIN <= valor <= CURSO_MAX):
            raise ValueError(f"Curso fuera de rango ({CURSO_MIN}-{CURSO_MAX}): {valor!r}")

        return valor


# ============================================================
# SINGLETON DE CONVENIENCIA
# ============================================================

horario_data_normalizer = HorarioDataNormalizer()
