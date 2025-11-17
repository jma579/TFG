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
from typing import List, Optional

from core.extraccion.horarios.entities import (
    ParsingResult,
    Horario as ParsedHorario,
    Sesion as ParsedSesion,
    NormalizedHorarioTablaData,
    NormalizedSesionHorarioData,
)
from core.extraccion.horarios.constants import (
    PERIODO_MAP,
    DIA_SEMANA_MAP,
    AULA_KEYWORDS,
    PATRON_NUMERO_ROMANO,
    CURSO_MAP,
    GRUPO_DEFAULT_TEORIA,
    GRUPO_DEFAULT_PRACTICA,
    CURSO_MIN,
    CURSO_MAX,
)
from constants.enums import (
    DiaSemana,
    TipoGrupoDocente,
    TipoAula,
    Periodo,
)


# ==========================================================================
# NORMALIZADOR PRINCIPAL
# ==========================================================================


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

        Args:
            parsed: Resultado del parser de horarios.

        Returns:
            Lista de horarios normalizados (uno por tabla/curso/página).
        """
        resultados: List[NormalizedHorarioTablaData] = []

        programa_nombre = self._normalize_nombre(parsed.titulo)

        for horario in parsed.horarios:
            resultados.append(
                self._normalize_horario_tabla(
                    programa_nombre=programa_nombre,
                    horario=horario,
                )
            )

        return resultados

    # ------------------------------------------------------------------
    # Normalizadores específicos
    # ------------------------------------------------------------------

    def _normalize_horario_tabla(
        self,
        programa_nombre: str,
        horario: ParsedHorario,
    ) -> NormalizedHorarioTablaData:
        """Normaliza una tabla de horario concreta (un curso/mención/página)."""

        curso = self._parse_curso(horario.curso)
        periodo_enum = self._map_periodo(horario.periodo)
        mencion = self._normalize_mencion(horario.mencion)

        sesiones_norm: List[NormalizedSesionHorarioData] = []
        for sesion in horario.sesiones:
            sesiones_norm.append(
                self._normalize_sesion(
                    sesion=sesion,
                )
            )

        return NormalizedHorarioTablaData(
            programa_nombre=programa_nombre,
            curso=curso,
            periodo=periodo_enum,
            mencion=mencion,
            sesiones=sesiones_norm,
        )

    def _normalize_sesion(self, sesion: ParsedSesion) -> NormalizedSesionHorarioData:
        """Normalizar una sesión individual.

        - Limpia nombre de asignatura
        - Mapea día de la semana a enum
        - Infere tipo de grupo y código
        - Infere tipo de aula y la normaliza
        """
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
    # Helpers de normalización de strings
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
        """Normalizar el texto de mención (si existe)."""
        if not mencion:
            return None
        return self._normalize_nombre(mencion)

    def _normalize_aula_nombre(self, aula: str) -> str:
        """Normalizar nombre de aula.

        - strip
        - colapsar espacios
        - upper para facilitar matching posterior
        """
        aula = (aula or "").strip()
        aula = re.sub(r"\s+", " ", aula)
        return aula.upper()

    # ------------------------------------------------------------------
    # Mapeos a enums
    # ------------------------------------------------------------------

    def _map_periodo(self, periodo: str) -> Periodo:
        """Mapear string de periodo de horario a enum Periodo.

        Se espera valores tipo "PRIMER CUATRIMESTRE", "SEGUNDO CUATRIMESTRE",
        "ANUAL", etc.
        """
        if not periodo:
            raise ValueError("Periodo vacío en horario")

        p = periodo.strip().lower()
        
        # Buscar en el mapa de periodos
        if p in PERIODO_MAP:
            return PERIODO_MAP[p]
        
        # Búsqueda parcial si no hay coincidencia exacta
        for key, value in PERIODO_MAP.items():
            if key in p:
                return value

        raise ValueError(f"Periodo de horario desconocido: {periodo!r}")

    def _map_dia_semana(self, dia: str) -> DiaSemana:
        """Mapear el día en texto del parser a DiaSemana.

        Admite variantes con y sin acento y mayúsculas.
        """
        if not dia:
            raise ValueError("Día vacío en sesión de horario")

        d = dia.strip().lower()

        # Normalizar acentos básicos
        d = d.replace("miércoles", "miercoles").replace("sábado", "sabado")
        
        # Buscar en el mapa de días
        if d in DIA_SEMANA_MAP:
            return DIA_SEMANA_MAP[d]
        
        # Búsqueda por prefijo si no hay coincidencia exacta
        for key, value in DIA_SEMANA_MAP.items():
            if d.startswith(key[:3]):  # Primeras 3 letras
                return value

        raise ValueError(f"Día de la semana desconocido: {dia!r}")

    # ------------------------------------------------------------------
    # Inferencias varias
    # ------------------------------------------------------------------

    def _infer_tipo_grupo_y_codigo(
        self,
        tipo: Optional[str],
        grupo: Optional[str],
    ) -> tuple[str, TipoGrupoDocente]:
        """Inferir código de grupo y TipoGrupoDocente.

        Reglas sencillas:
        - Si el parser indica tipo "PRÁCTICA" → TipoGrupoDocente.PRACTICA
        - Si indica "TEORÍA" o None → TipoGrupoDocente.TEORIA
        - Si hay texto de grupo (PL2, PA1, Grupo 3...) se limpia y usa
        - Si no hay grupo, usa constantes por defecto
        """
        tipo_valor = (tipo or "").strip().lower()

        if "práctica" in tipo_valor or "practica" in tipo_valor:
            tipo_enum = TipoGrupoDocente.PRACTICA
        else:
            # Incluye TEORÍA, PRÁCTICA_AULA u otros como teoría por defecto
            tipo_enum = TipoGrupoDocente.TEORIA

        if grupo:
            codigo = grupo.strip().upper()
        else:
            codigo = GRUPO_DEFAULT_PRACTICA if tipo_enum is TipoGrupoDocente.PRACTICA else GRUPO_DEFAULT_TEORIA

        return codigo, tipo_enum

    def _infer_aula_tipo(self, aula_nombre: str) -> TipoAula:
        """Inferir TipoAula a partir del nombre de aula.

        Usa AULA_KEYWORDS de constants.py para clasificar.
        """
        nombre_lower = aula_nombre.lower()

        # Buscar en keywords de laboratorio
        for keyword in AULA_KEYWORDS['laboratorio']:
            if keyword in nombre_lower:
                return TipoAula.LABORATORIO
        
        # Buscar en keywords de informática
        for keyword in AULA_KEYWORDS['informatica']:
            if keyword in nombre_lower:
                return TipoAula.INFORMATICA
        
        # Buscar en keywords de seminario
        for keyword in AULA_KEYWORDS['seminario']:
            if keyword in nombre_lower:
                return TipoAula.SEMINARIO
        
        # Buscar en keywords de teórica
        for keyword in AULA_KEYWORDS['teorica']:
            if keyword in nombre_lower:
                return TipoAula.TEORICA

        return TipoAula.TEORICA

    # ------------------------------------------------------------------
    # Parseos auxiliares
    # ------------------------------------------------------------------

    def _parse_curso(self, curso_str: str) -> int:
        """Parsear curso ("1º", "Primero", "1", etc.) a int.

        Usa CURSO_MAP de constants.py.
        """
        if not curso_str:
            raise ValueError("Curso vacío en horario")

        s = curso_str.strip().lower()

        # Buscar en el mapa de cursos
        for key, value in CURSO_MAP.items():
            if key in s:
                return value

        # Intentar parsear directamente como número
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
