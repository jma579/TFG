from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import time
import re

# Entidades comunes y de horarios
from core.extraccion.common.entities import ExtractionMetadata, ParserError, ParsingMetadata
from core.extraccion.horarios.entities import (
    ExtractionResult, CleanTable, RawTable,
    Session, Schedule, Warning
)

# Constantes del parser (se declararán en horarios/constants.py)
from core.extraccion.horarios.constants import (  # nombres, no implementadas aún
    DEFAULT_PARSER_CONFIG, TIME_WINDOW_START, TIME_WINDOW_END,
    DAYS_CANONICAL, DAY_ALIASES, HEADER_DAYS_ORDER,
    TOKEN_SPLIT_REGEX, RE_WHITESPACE_NORM, RE_DASHES,
    RE_GRUPO_PL, RE_GRUPO_PA, RE_GRUPO_GENERIC,
    RE_AULA, RE_AULA_SEMINARIO, RE_AULA_ABBREV,
    RE_AULA_LAB, RE_AULA_LSC,
    RE_PUNCT_TRIM, RE_MULTI_SPACE,
    MODALIDAD_KEYWORDS, MODALIDAD_CANON_MAP, MODALIDAD_PRIORITY,
    AMBIGUOUS_TOKENS, UNKNOWN_TOKENS,
)

ParserRuns = List[Dict[str, Any]]  # cada run: {dia_idx, row_idx, asignatura, aula?, modalidad, grupo?}

class ScheduleParser:
    """
    Parser de horarios académicos basado en salida 'clean_tables' del extractor (Camelot).
    Responsabilidades:
      - Tokenización de celdas y normalización.
      - Inferencia de {asignatura, aula, modalidad, grupo}.
      - Generación de runs por franja y merge de bloques contiguos por día.
      - Validación y metadatos de parseo.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = DEFAULT_PARSER_CONFIG.copy()
        if config:
            self.config.update(config)
        self.name = self.__class__.__name__

    # -------- API pública
    def parse(self, extraction_result: ExtractionResult) -> Schedule:
        """
        Punto de entrada del parser.
        Args:
            extraction_result: Objeto con titulacion, tablas limpias/crudas y metadatos de extracción.
        Returns:
            Schedule: sesiones consolidadas + trazabilidad + metadatos.
        Raises:
            ParserError: ante fallos no recuperables de parsing.
        """
        t0 = time.time()
        self.warnings: List[Warning] = []
        self.errors: List[str] = []

        # --- Comprobación entrada mínima
        if extraction_result is None:
            raise ParserError("ExtractionResult es None.")
        titulacion = getattr(extraction_result, "titulacion", None)
        clean_tables = getattr(extraction_result, "clean_tables", None)
        raw_tables = getattr(extraction_result, "raw_tables", None)
        extraccion_md = getattr(extraction_result, "extraccion_metadata", None)

        if not titulacion or not isinstance(titulacion, str):
            self.errors.append("Campo 'titulacion' ausente o inválido.")
        if not isinstance(clean_tables, list) or not clean_tables:
            raise ParserError("Campo 'clean_tables' ausente o inválido.")
        if not isinstance(raw_tables, list) or not raw_tables:
            self._warn("Campo 'raw_tables' ausente o vacío.", "moderate")
            raw_tables = []
        if extraccion_md is None:
            self.errors.append("Campo 'extraccion_metadata' ausente o inválido.")


        # --- Parse por páginas (robusto: continúa aunque una página falle)
        all_sessions: List[Session] = []
        pages_ok = 0
        for idx, clean_table in enumerate(clean_tables):
            try:
                page_sessions = self._parse_page(clean_table)
                if not isinstance(page_sessions, list):
                    raise ParserError("La página no devolvió una lista de sesiones.")
                all_sessions.extend(page_sessions)
                pages_ok += 1
            except ParserError as e:
                self.errors.append(f"Página {idx+1}: {e}")
            except Exception as e:
                self.errors.append(f"Página {idx+1}: error inesperado: {type(e).__name__}: {e}")

        # --- Validación de coherencias básicas en sesiones (solo warnings)
        try:
            self.warnings.extend(self._validate_sesiones(all_sessions))
        except Exception as e:
            self.errors.append(f"Fallo al validar sesiones: {type(e).__name__}: {e}")

        # --- Regla de validación mínima del resultado (similar a fichas: abortar si falta lo esencial)
        valid_result = True
        validation_errs: List[str] = []
        if pages_ok == 0:
            validation_errs.append("No se pudo parsear ninguna página del horario.")
            valid_result = False
        if len(all_sessions) == 0:
            validation_errs.append("No se generó ninguna sesión a partir de las tablas.")
            valid_result = False

        # --- Si la validación mínima falla, comportarse como en fichas: lanzar ParserError
        if not valid_result:
            raise ParserError(f"Errores de validación: {validation_errs}")

        # --- Metadatos de parseo (alineados con parser de fichas)
        parse_ts = datetime.now().isoformat(timespec="seconds") + "Z"
        parse_duration = max(0.0, time.time() - t0)
        parse_metadata = ParsingMetadata(
            parser_name=self.name,
            parser_version=getattr(self, "version", "Unknown version"),
            parse_timestamp=parse_ts,
            parse_duration=parse_duration,
            warnings=self.warnings,
            errors=self.errors,
        )

        # --- Construcción del resultado
        schedule = Schedule(
            titulacion=titulacion,
            sesiones=all_sessions,
            raw_tables=raw_tables,
            clean_tables=clean_tables,
            extraccion_metadata=extraccion_md,
            parse_metadata=parse_metadata,
        )

        return schedule

    # -------- Parsing por página
    def _parse_page(self, clean_table: CleanTable) -> List[Session]:
        """
        Convierte una CleanTable en sesiones (lista de Session), aplicando:
         - propagación de valores por columna (día),
         - tokenización de celdas,
         - inferencia de campos por token,
         - creación de sesiones por franja horaria.
        """
        header_days = getattr(clean_table, "header_days", None)
        time_axis = getattr(clean_table, "time_axis", None)
        cells = getattr(clean_table, "cells", None)

        if not isinstance(header_days, list) or len(header_days) != len(DAYS_CANONICAL):
            raise ParserError("header_days ausente o no tiene los 5 días esperados (L->V).")

        if not isinstance(time_axis, list) or len(time_axis) < 2:
            raise ParserError("time_axis ausente o con menos de 2 marcas (no se pueden formar intervalos).")

        if not isinstance(cells, list) or len(cells) != len(time_axis):
            raise ParserError("cells ausente o su número de filas no coincide con time_axis.")

        n_cols = len(header_days)
        n_rows = len(time_axis)

        # Inicializar estado por columna (día)
        last_values = [
            {"asignatura": None, "aula": None, "grupo": None, "modalidad": None}
            for _ in range(n_cols)
        ]

        sesiones: List[Session] = []

        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                cell_text = cells[row_idx][col_idx]
                tokens = self._tokenize_cell(cell_text)
                entries = self._infer_fields(tokens) if tokens else []

                # Si hay entrada, actualiza el estado; si no, hereda el anterior
                if entries:
                    # Tomamos solo la primera entrada (en horarios académicos raramente hay más de una por celda)
                    entry = entries[0]
                    for key in ["asignatura", "aula", "grupo", "modalidad"]:
                        if entry.get(key):
                            last_values[col_idx][key] = entry[key]
                # Si no hay entrada, se hereda el valor anterior (ya está en last_values)

                # Solo creamos sesión si hay asignatura o aula (evita sesiones vacías)
                asignatura = last_values[col_idx]["asignatura"]
                aula = last_values[col_idx]["aula"]
                grupo = last_values[col_idx]["grupo"]
                modalidad = last_values[col_idx]["modalidad"] or "teoria"

                if asignatura or aula:
                    hora_inicio = time_axis[row_idx]
                    # hora_fin: siguiente marca, o None si es la última (no debería ocurrir)
                    if row_idx + 1 < n_rows:
                        hora_fin = time_axis[row_idx + 1]
                    else:
                        continue  # no se puede formar sesión sin hora_fin

                    dia_str = header_days[col_idx]

                    sesiones.append(
                        Session(
                            asignatura=asignatura,
                            aula=aula,
                            hora_inicio=hora_inicio,
                            hora_fin=hora_fin,
                            dia=dia_str,
                            modalidad=modalidad,
                            grupo=grupo,
                        )
                    )

        # Deduplicar sesiones exactas
        keyset = set()
        uniq: List[Session] = []
        for s in sesiones:
            k = (
                s.dia,
                s.hora_inicio,
                s.hora_fin,
                (s.asignatura or "").strip().lower(),
                (s.aula or "").strip().lower(),
                (s.grupo or "").strip().lower(),
                s.modalidad or "teoria",
            )
            if k in keyset:
                continue
            keyset.add(k)
            uniq.append(s)

        return uniq

    # -------- Tokenización e inferencia
    def _tokenize_cell(self, text: str) -> List[str]:
        """
        Separa una celda en tokens significativos, normaliza espacios/acentos y filtra tokens vacíos.
        """
        if not isinstance(text, str):
            return []

        s = text.strip()
        if not s:
            return []

        # Normalizaciones suaves (no removemos acentos)
        s = re.sub(RE_DASHES, "-", s)                          # unificar guiones
        s = re.sub(RE_WHITESPACE_NORM, " ", s)                 # espacios en blanco homogéneos

        # Split primario en separadores fuertes
        parts = re.split(TOKEN_SPLIT_REGEX, s)

        tokens: List[str] = []
        for p in parts:
            if not p:
                continue
            # Limpieza de bordes y espacios internos
            t = re.sub(RE_PUNCT_TRIM, "", p).strip()
            t = re.sub(RE_MULTI_SPACE, " ", t)
            if not t:
                continue
            # Filtrado de tokens desconocidos
            if t in UNKNOWN_TOKENS:
                continue
            tokens.append(t)

        return tokens

    def _infer_fields(self, tokens: List[str]) -> List[Dict[str, Optional[str]]]:
        """
        Dada una lista de tokens, infiere los campos: asignatura, aula, grupo, modalidad.
        Devuelve una lista de dicts (uno por posible entrada, normalmente solo uno).
        """
        import re

        # Unir tokens para análisis global
        text = " ".join(tokens).strip()
        result = {
            "asignatura": None,
            "aula": None,
            "grupo": None,
            "modalidad": None,
        }

        # Buscar grupo
        grupo_match = re.search(RE_GRUPO_PL, text)
        if not grupo_match:
            grupo_match = re.search(RE_GRUPO_PA, text)
        if not grupo_match:
            grupo_match = re.search(RE_GRUPO_GENERIC, text)
        if grupo_match:
            result["grupo"] = grupo_match.group(0)
            text = text.replace(result["grupo"], "").strip()

        # Buscar aula
        aula_match = re.search(RE_AULA, text)
        if not aula_match:
            aula_match = re.search(RE_AULA_LSC, text)
        if not aula_match:
            aula_match = re.search(RE_AULA_SEMINARIO, text)
        if not aula_match:
            aula_match = re.search(RE_AULA_ABBREV, text)
        if aula_match:
            result["aula"] = aula_match.group(0)
            text = text.replace(result["aula"], "").strip()
        else:
            # Si no hay patrón claro, buscar última palabra tipo "AULA X"
            m = re.search(r"(AULA\s*\d+)$", text)
            if m:
                result["aula"] = m.group(1)
                text = text.replace(result["aula"], "").strip()

        # Inferir modalidad por keywords
        modalidad = None
        for key, keywords in MODALIDAD_KEYWORDS.items():
            for kw in keywords:
                if kw in text.upper():
                    modalidad = key
                    break
            if modalidad:
                break
        if not modalidad and result["grupo"]:
            if "PL" in result["grupo"]:
                modalidad = "practicas_laboratorio"
            elif "PA" in result["grupo"]:
                modalidad = "practicas_aula"
        result["modalidad"] = modalidad

        # El resto es la asignatura (si queda algo)
        asignatura = text.strip(" -–—;:,")
        if asignatura:
            result["asignatura"] = asignatura
        else:
            result["asignatura"] = None

        return [result]

    # -------- Merge de runs por día
    def _merge_runs_por_dia(self, runs: ParserRuns, time_axis: List[str]) -> List[Session]:
        """
        Une bloques contiguos (misma asignatura/aula/modalidad/grupo y mismo día)
        para formar sesiones con hora_inicio y hora_fin correctas.
        - Etiqueta cada sesión con el día canónico (str, p.ej. "LUNES").
        - Descarta bloques fuera de ventana.
        - Deduplica sesiones idénticas al final.
        """
        if not runs:
            return []

        # Utilidades de tiempo
        def _to_minutes(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        lo = _to_minutes(TIME_WINDOW_START)
        hi = _to_minutes(TIME_WINDOW_END)

        def _in_window(hhmm: str) -> bool:
            t = _to_minutes(hhmm)
            return lo <= t <= hi

        def _same_payload(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
            return (
                (a.get("asignatura") or "").strip() == (b.get("asignatura") or "").strip()
                and (a.get("aula") or "").strip() == (b.get("aula") or "").strip()
                and (a.get("grupo") or "").strip() == (b.get("grupo") or "").strip()
                and (a.get("modalidad") or "teoria") == (b.get("modalidad") or "teoria")
                and a.get("dia_idx") == b.get("dia_idx")
            )

        # 1) Agrupar runs por día (usamos dia_idx interno solo para mapear a string canónico)
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for r in runs:
            by_day.setdefault(r["dia_idx"], []).append(r)

        sesiones: List[Session] = []

        # 2) Consolidar por día
        for dia_idx, day_runs in by_day.items():
            if not day_runs:
                continue

            day_runs.sort(key=lambda x: x["row_idx"])
            dia_str = DAYS_CANONICAL[dia_idx] if 0 <= dia_idx < len(DAYS_CANONICAL) else "DESCONOCIDO"

            current: Optional[Dict[str, Any]] = None
            start_r: Optional[int] = None
            end_r: Optional[int] = None

            def _flush():
                nonlocal current, start_r, end_r
                if current is None or start_r is None or end_r is None:
                    return

                if end_r + 1 >= len(time_axis):
                    self._warn(f"Sin marca de fin para bloque (día {dia_str}, filas {start_r}-{end_r}).", "minor")
                    current = None; start_r = None; end_r = None
                    return

                hora_inicio = time_axis[start_r]
                hora_fin = time_axis[end_r + 1]

                if hora_fin <= hora_inicio:
                    self._warn(f"Duración no positiva (día {dia_str} {hora_inicio}-{hora_fin}).", "minor")
                    current = None; start_r = None; end_r = None
                    return

                if not (_in_window(hora_inicio) and _in_window(hora_fin)):
                    # fuera de ventana objetivo → no añadimos
                    current = None; start_r = None; end_r = None
                    return

                sesiones.append(
                    Session(
                        asignatura=(current.get("asignatura") or "").strip() or None,
                        aula=(current.get("aula") or "").strip() or None,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        dia=dia_str,  # <- obligatorio
                        modalidad=current.get("modalidad") or "teoria",
                        grupo=(current.get("grupo") or "").strip() or None,
                    )
                )

                current = None; start_r = None; end_r = None

            for r in day_runs:
                if current is None:
                    current = r; start_r = r["row_idx"]; end_r = r["row_idx"]
                    continue

                if r["row_idx"] == end_r + 1 and _same_payload(r, current):
                    end_r = r["row_idx"]
                else:
                    _flush()
                    current = r; start_r = r["row_idx"]; end_r = r["row_idx"]

            _flush()

        # 3) Deduplicar sesiones exactas (incluyendo el día como string)
        keyset = set()
        uniq: List[Session] = []
        for s in sesiones:
            k = (
                s.dia,
                s.hora_inicio,
                s.hora_fin,
                (s.asignatura or "").strip().lower(),
                (s.aula or "").strip().lower(),
                (s.grupo or "").strip().lower(),
                s.modalidad or "teoria",
            )
            if k in keyset:
                continue
            keyset.add(k)
            uniq.append(s)

        return uniq


    # -------- Metadatos y validación
    def _validate_sesiones(self, sesiones: List[Session]) -> List[str]:
        """
        Reglas de coherencia (solo warnings):
        - HH:MM válidas; fin > inicio
        - ventana horaria respetada
        - sin solapes por día (string) para misma (asignatura, grupo, aula, modalidad)
        - modalidades en el canon
        """
        warnings: List[str] = []
        canon_modalidades = {"teoria", "practicas_laboratorio", "practicas_aula"}

        def _to_minutes(hhmm: str) -> int:
            h, m = map(int, hhmm.split(":"))
            return h * 60 + m

        lo = _to_minutes(TIME_WINDOW_START)
        hi = _to_minutes(TIME_WINDOW_END)

        # 1) Horas y ventana
        for idx, s in enumerate(sesiones):
            if not isinstance(s.hora_inicio, str) or not re.fullmatch(r"\d{2}:\d{2}", s.hora_inicio):
                warnings.append(f"Sesión {idx}: hora_inicio inválida: {s.hora_inicio!r}")
                continue
            if not isinstance(s.hora_fin, str) or not re.fullmatch(r"\d{2}:\d{2}", s.hora_fin):
                warnings.append(f"Sesión {idx}: hora_fin inválida: {s.hora_fin!r}")
                continue

            a, b = _to_minutes(s.hora_inicio), _to_minutes(s.hora_fin)
            if b <= a:
                warnings.append(f"Sesión {idx} ({s.dia}): hora_fin <= hora_inicio ({s.hora_inicio}-{s.hora_fin})")
            if not (lo <= a <= hi and lo <= b <= hi):
                warnings.append(f"Sesión {idx} ({s.dia}): fuera de ventana [{TIME_WINDOW_START}-{TIME_WINDOW_END}]")

        # 2) Solapes por día (string) y payload (intersección real)
        # Clave: (dia, asignatura, grupo, aula, modalidad)
        by_key: Dict[tuple, List[tuple]] = {}
        for idx, s in enumerate(sesiones):
            key = (
                s.dia,
                (s.asignatura or "").strip().lower(),
                (s.grupo or "").strip().lower(),
                (s.aula or "").strip().lower(),
                (s.modalidad or "teoria"),
            )
            interval = (_to_minutes(s.hora_inicio), _to_minutes(s.hora_fin))
            by_key.setdefault(key, []).append((idx, interval))

        for key, items in by_key.items():
            items.sort(key=lambda x: x[1][0])  # orden por inicio
            for i in range(1, len(items)):
                idx_i, (ai, bi) = items[i]
                idx_p, (ap, bp) = items[i-1]
                if ai < bp:  # solape real
                    warnings.append(
                        f"Solape en {key[0]} entre sesiones {idx_p} y {idx_i} para payload={key[1:]}"
                    )

        # 3) Modalidades
        for idx, s in enumerate(sesiones):
            if (s.modalidad or "teoria") not in canon_modalidades:
                warnings.append(f"Sesión {idx} ({s.dia}): modalidad fuera de canon: {s.modalidad!r}")

        return warnings

    
    # ------- Helpers de warnings
    def _warn(self, msg: str, severity: str) -> None:
        # Warning es tu dataclass; ajusta el import si procede
        try:
            self.warnings.append(Warning(msg, severity))
        except AttributeError:
            self.warnings = [Warning(msg, severity)]


# -----------------------------------------------------------------------------
schedule_parser = None

def get_schedule_parser(config: Optional[Dict[str, Any]] = None) -> ScheduleParser:
    """
    Factory singleton para ScheduleParser.
    """
    global schedule_parser
    if schedule_parser is None:
        schedule_parser = ScheduleParser(config)
    return schedule_parser