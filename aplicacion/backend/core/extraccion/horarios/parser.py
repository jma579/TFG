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
         - tokenización de celdas,
         - inferencia de campos por token,
         - creación de runs por franja,
         - merge de contiguos por día,
         - normalización de horas y modalidades.
        """
        # --- Validaciones mínimas de la tabla
        header_days = getattr(clean_table, "header_days", None)
        time_axis = getattr(clean_table, "time_axis", None)
        cells = getattr(clean_table, "cells", None)

        if not isinstance(header_days, list) or len(header_days) != len(DAYS_CANONICAL):
            raise ParserError("header_days ausente o no tiene los 5 días esperados (L->V).")

        if not isinstance(time_axis, list) or len(time_axis) < 2:
            raise ParserError("time_axis ausente o con menos de 2 marcas (no se pueden formar intervalos).")

        if not isinstance(cells, list) or len(cells) != len(time_axis):
            raise ParserError("cells ausente o su número de filas no coincide con time_axis.")

        # Normalización canónica de días (aplicar alias si aparece)
        unknown_days = []
        normalized_days: List[str] = []
        for d in header_days:
            d_up = (d or "").strip().upper()
            d_up = DAY_ALIASES.get(d_up, d_up)
            if d_up not in DAYS_CANONICAL:
                # día desconocido: lo anotamos pero seguimos (el índice sigue siendo 0..4)
                # No lanzamos error aquí; delegamos en validaciones posteriores si hiciera falta.
                unknown_days.append(d)
            normalized_days.append(d_up)
        if unknown_days:
            self._warn(f"Días desconocidos en header: {unknown_days}", "low")

        # Verificación rápida de HH:MM y orden
        def _valid_time(s: str) -> bool:
            return bool(re.fullmatch(r"\d{2}:\d{2}", s))

        for i, t in enumerate(time_axis):
            if not isinstance(t, str) or not _valid_time(t):
                raise ParserError(f"time_axis contiene una marca inválida en pos {i}: {t!r}")
            if i > 0 and time_axis[i] <= time_axis[i - 1]:
                raise ParserError("time_axis no está estrictamente ordenado de menor a mayor.")

        # Matriz columnas (días) consistente
        n_cols = len(normalized_days)
        for r, row in enumerate(cells):
            if not isinstance(row, list):
                raise ParserError(f"Fila {r} de cells no es una lista.")
            if len(row) < n_cols:
                raise ParserError(f"Fila {r} de cells tiene {len(row)} columnas, se esperaban {n_cols}.")
            if len(row) > n_cols:
                self._warn(f"Fila {r} tiene columnas extra ({len(row)}>{n_cols}); se ignorarán las sobrantes.", "low")

        # --- Generación de runs
        runs: List[Dict[str, Any]] = []
        for r, row in enumerate(cells):
            for c in range(n_cols):
                cell_text = row[c]
                if not isinstance(cell_text, str) or not cell_text.strip():
                    continue
                # Heurística OCR sospechoso: solo dígitos/espacios/puntuación
                if re.fullmatch(r"[0-9\s\.\,\-\–\—\/\\:;]+", cell_text.strip()):
                    self._warn(f"Contenido sospechoso en celda r{r}c{c!s}: {cell_text!r}", "moderate")
                tokens = self._tokenize_cell(cell_text)
                entries = self._infer_fields(tokens)
                if not entries:
                    # no se generan entradas a partir de un texto no vacío
                    self._warn(f"Celda no parseada r{r}c{c!s}: {cell_text!r}", "moderate")
                    continue
                for e in entries:
                    runs.append({
                        "dia_idx": c,
                        "row_idx": r,
                        "asignatura": e.get("asignatura"),
                        "aula": e.get("aula"),
                        "grupo": e.get("grupo"),
                        "modalidad": e.get("modalidad") or "teoria",
                    })

        # --- Merge y construcción de sesiones
        sesiones = self._merge_runs_por_dia(runs, time_axis)
        return sesiones


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
        A partir de tokens, devuelve una o varias entradas con campos inferidos:
            [{asignatura, aula?, grupo?, modalidad}, ...]
        Puede generar múltiples entradas si la celda contiene varios 'bloques' separados.
        """
        if not tokens:
            return []

        grupos: List[str] = []
        aulas: List[str] = []
        modo_votes = {
            "practicas_laboratorio": 0,
            "practicas_aula": 0,
            "teoria": 0,
        }
        subj_fragments: List[str] = []

        # Helpers de matching case-insensitive
        def m(pattern: str, t: str) -> bool:
            return re.search(pattern, t, flags=re.IGNORECASE) is not None

        def is_aula_token(t: str) -> bool:
            return (
                m(RE_AULA_LSC, t) or
                m(RE_AULA_LAB, t) or
                m(RE_AULA, t) or
                m(RE_AULA_SEMINARIO, t) or
                (re.fullmatch(RE_AULA_ABBREV, t, flags=re.IGNORECASE) is not None)
            )

        # 1) Clasificación de tokens
        for t in tokens:
            # Grupos
            if m(RE_GRUPO_PL, t) or m(RE_GRUPO_PA, t) or m(RE_GRUPO_GENERIC, t):
                if t not in grupos:
                    grupos.append(t)
                # Modalidad por inferencia rápida según el prefijo del grupo
                if m(RE_GRUPO_PL, t):
                    modo_votes["practicas_laboratorio"] += 1
                elif m(RE_GRUPO_PA, t):
                    modo_votes["practicas_aula"] += 1
                continue

            # Aulas
            if is_aula_token(t):
                if t not in aulas:
                    aulas.append(t)
                # Modalidad por heurística de aula
                if m(RE_AULA_LSC, t) or m(RE_AULA_LAB, t):
                    modo_votes["practicas_laboratorio"] += 1
                elif m(RE_AULA, t) or m(RE_AULA_SEMINARIO, t):
                    modo_votes["practicas_aula"] += 1
                continue

            # Modalidad explícita por keywords
            t_upper = t.upper()
            for key, words in MODALIDAD_KEYWORDS.items():
                # si cualquiera de las keywords aparece como palabra o prefijo razonable
                if any(re.search(rf"\b{re.escape(w)}\b", t_upper, flags=re.IGNORECASE) for w in words):
                    modo_votes[key] += 1

            # Ambiguos sueltos no se añaden a asignatura
            if t_upper in AMBIGUOUS_TOKENS:
                continue

            # El resto contribuye a la asignatura (incluye "ODS")
            subj_fragments.append(t)

        # 2) Asignatura: junta fragmentos conservando acentos y espacios
        asignatura = " ".join(subj_fragments).strip()
        asignatura = re.sub(RE_MULTI_SPACE, " ", asignatura)

        # Si quedó vacía pero había “ODS” explícito entre tokens, la usamos
        if not asignatura and any(tok.strip().upper() == "ODS" for tok in tokens):
            asignatura = "ODS"

        # 3) Modalidad: por prioridad (si no hay votos, cae en 'teoria')
        modalidad = "teoria"
        # si hay algún voto, ganan por ranking
        if any(v > 0 for v in modo_votes.values()):
            for key in MODALIDAD_PRIORITY:
                if modo_votes.get(key, 0) > 0:
                    modalidad = key
                    break

        # 4) Composición de entradas (cartesiano mínimo entre grupos y aulas)
        # Casos:
        #   - sin grupos y sin aulas -> una entrada base
        #   - n grupos, 0 aulas -> n entradas
        #   - 0 grupos, n aulas -> n entradas
        #   - n grupos, m aulas -> n*m entradas
        entries: List[Dict[str, Optional[str]]] = []

        base = {
            "asignatura": asignatura if asignatura else None,
            "aula": None,
            "grupo": None,
            "modalidad": modalidad,
        }

        gs = grupos if grupos else [None]
        as_ = aulas if aulas else [None]

        for g in gs:
            for a in as_:
                e = dict(base)
                e["grupo"] = g
                e["aula"] = a
                entries.append(e)

        # 5) Limpieza final: si asignatura quedó None y no hay grupo ni aula, devolvemos lista vacía
        # (celda irrelevante o solo compuesta de abreviaturas ambiguas)
        cleaned = []
        for e in entries:
            if e["asignatura"] or e["grupo"] or e["aula"]:
                # Normalización de modalidad al canon garantizado por constantes
                if e["modalidad"] not in ("teoria", "practicas_laboratorio", "practicas_aula"):
                    e["modalidad"] = "teoria"
                cleaned.append(e)

        return cleaned

    # -------- Merge de runs por día
    def _merge_runs_por_dia(self, runs: ParserRuns, time_axis: List[str]) -> List[Session]:
        """
        Une bloques contiguos (misma asignatura/aula/modalidad/grupo y mismo día)
        para formar sesiones con hora_inicio y hora_fin correctas.
        """
        if not runs:
            return []

        # Utilidades de tiempo
        def _to_minutes(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        def _in_window(hhmm: str) -> bool:
            return _to_minutes(TIME_WINDOW_START) <= _to_minutes(hhmm) <= _to_minutes(TIME_WINDOW_END)

        def _same_payload(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
            return (
                (a.get("asignatura") or "").strip() == (b.get("asignatura") or "").strip() and
                (a.get("aula") or "").strip() == (b.get("aula") or "").strip() and
                (a.get("grupo") or "").strip() == (b.get("grupo") or "").strip() and
                (a.get("modalidad") or "teoria") == (b.get("modalidad") or "teoria")
            )

        # Agrupar runs por día
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for r in runs:
            by_day.setdefault(r["dia_idx"], []).append(r)

        sesiones: List[Session] = []

        # Recorrer cada día y consolidar
        for dia_idx, day_runs in by_day.items():
            if not day_runs:
                continue

            # Aviso por solapes: mismo row_idx con payload distinto
            seen_by_row: Dict[int, Dict[str, Any]] = {}
            for r in day_runs:
                k = r["row_idx"]
                if k in seen_by_row and not _same_payload(r, seen_by_row[k]):
                    # Warning moderado; seguimos procesando
                    self._warn(f"Solape en día {dia_idx}, fila {k}: múltiples runs distintos.", "moderate")
                else:
                    seen_by_row[k] = r

            # Ordenar por fila (robustez)
            day_runs.sort(key=lambda x: x["row_idx"])

            current: Optional[Dict[str, Any]] = None  # bloque activo (payload del run)
            start_r: Optional[int] = None
            end_r: Optional[int] = None

            def _flush_current():
                nonlocal current, start_r, end_r
                if current is None or start_r is None or end_r is None:
                    return

                # Necesitamos la marca posterior a end_r
                if end_r + 1 >= len(time_axis):
                    self._warn(f"Sin marca de fin para bloque (día {dia_idx}, filas {start_r}-{end_r}).", "low")
                    current = None
                    start_r = None
                    end_r = None
                    return

                hora_inicio = time_axis[start_r]
                hora_fin = time_axis[end_r + 1]

                # Duración válida
                if hora_fin <= hora_inicio:
                    self._warn(f"Duración cero o negativa (día {dia_idx} {hora_inicio}-{hora_fin}).", "low")
                    current = None
                    start_r = None
                    end_r = None
                    return

                # Dentro de la ventana objetivo
                if not (_in_window(hora_inicio) and _in_window(hora_fin)):
                    self._warn(f"Sesión fuera de ventana ({hora_inicio}-{hora_fin}); descartada.", "low")
                    current = None
                    start_r = None
                    end_r = None
                    return

                # Aviso por campos vacíos relevantes
                if not (current.get("asignatura")) and (current.get("aula") or current.get("grupo")):
                    self._warn(f"Sesión sin asignatura (día {dia_idx}, {hora_inicio}-{hora_fin}) con aula/grupo.", "low")

                # Construir Session
                sesiones.append(Session(
                    asignatura=current.get("asignatura"),
                    aula=current.get("aula"),
                    grupo=current.get("grupo"),
                    modalidad=current.get("modalidad") or "teoria",
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                ))

                current = None
                start_r = None
                end_r = None

            for r in day_runs:
                if current is None:
                    current = r
                    start_r = r["row_idx"]
                    end_r = r["row_idx"]
                    continue

                # ¿Es contiguo y con el mismo payload?
                if r["row_idx"] == (end_r + 1) and _same_payload(r, current):
                    end_r = r["row_idx"]
                else:
                    _flush_current()
                    current = r
                    start_r = r["row_idx"]
                    end_r = r["row_idx"]

            # Cerrar último bloque del día
            _flush_current()

        return sesiones

    # -------- Metadatos y validación
    def _validate_sesiones(self, sesiones: List[Session]) -> List[str]:
        """
        Reglas de coherencia:
          - HH:MM válidas; fin > inicio
          - sin solapes exactos por día para misma (asignatura, grupo, aula) tras merge
          - modalidades en el canon
        Devuelve lista de warnings (sin abortar salvo errores críticos en parse()).
        """
        warnings: List[str] = []
        canon_modalidades = {"teoria", "practicas_laboratorio", "practicas_aula"}

        # Utilidad para comparar horas
        def _to_minutes(hhmm: str) -> int:
            h, m = map(int, hhmm.split(":"))
            return h * 60 + m

        # 1. Validar horas y duración
        for idx, s in enumerate(sesiones):
            if not isinstance(s.hora_inicio, str) or not re.fullmatch(r"\d{2}:\d{2}", s.hora_inicio):
                warnings.append(f"Sesión {idx}: hora_inicio inválida: {s.hora_inicio!r}")
            if not isinstance(s.hora_fin, str) or not re.fullmatch(r"\d{2}:\d{2}", s.hora_fin):
                warnings.append(f"Sesión {idx}: hora_fin inválida: {s.hora_fin!r}")
            try:
                if _to_minutes(s.hora_fin) <= _to_minutes(s.hora_inicio):
                    warnings.append(f"Sesión {idx}: hora_fin <= hora_inicio ({s.hora_inicio}-{s.hora_fin})")
            except Exception:
                pass

        # 2. Validar solapes exactos por día y payload
        # Clave: (asignatura, grupo, aula, modalidad, día)
        seen = {}
        for idx, s in enumerate(sesiones):
            key = (
                (s.asignatura or "").strip().lower(),
                (s.grupo or "").strip().lower(),
                (s.aula or "").strip().lower(),
                (s.modalidad or "teoria"),
                # Día no está explícito en Session, pero podrías añadirlo si lo necesitas
                # Si no, puedes omitirlo o inferirlo si tienes esa info
            )
            interval = (_to_minutes(s.hora_inicio), _to_minutes(s.hora_fin))
            if key in seen:
                for other_idx, other_interval in seen[key]:
                    # Solape exacto
                    if interval == other_interval:
                        warnings.append(
                            f"Solape exacto en sesiones {other_idx} y {idx} para {key} en {s.hora_inicio}-{s.hora_fin}"
                        )
            seen.setdefault(key, []).append((idx, interval))

        # 3. Modalidades en el canon
        for idx, s in enumerate(sesiones):
            if (s.modalidad or "teoria") not in canon_modalidades:
                warnings.append(f"Sesión {idx}: modalidad fuera de canon: {s.modalidad!r}")

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