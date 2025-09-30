from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re
from datetime import time

from core.extraccion.parsers.base_parser import BaseParser
from core.extraccion.entities.common import ParserError
from core.extraccion.entities.extractor import ExtractionMetadata
from core.extraccion.entities.horarios import (
    ScheduleSheet,
    ScheduleEntry,
)

# Constantes/regex y configuración del parser de horarios
from core.extraccion.constants.horarios import (
    DAYS,                 # ["LUNES","MARTES","MIÉRCOLES","MIERCOLES","JUEVES","VIERNES"]
    CURSO_TOKENS,         # [(1, r"\bPRIMER CURSO\b"), (2, r"\bSEGUNDO CURSO\b"), ...]
    PERIODO_RX,           # r"\b(PRIMER|SEGUNDO)\s+CUATRIMESTRE\b"
    PROGRAM_RX,           # r"^(?P<programa>[A-ZÁÉÍÓÚÜÑ ]{10,})$"
    AULA_RX,              # r"\b(AULA\s+[A-Za-z0-9]+|LSC\s*\d+|PL\s*\d+)\b"
    GRUPO_RX,             # r"\b(Grupo\s+\d+)\b"
    LAB_TAGS,             # r"\b(LAB|Pr[aá]ct\.?|Pr[aá]cticas|PL\s*\d+)\b"
    HOUR_TOKEN,           # r"(?:[01]?\d|2[0-3]):?[0-5]\d"
    DAY_SPLIT_RX,         # r"(?=^(LUNES|MARTES|MIÉRCOLES|MIERCOLES|JUEVES|VIERNES)\s*$)"
    DEFAULT_HORARIO_CONFIG,
)


class HorarioParser(BaseParser[ScheduleSheet]):
    """
    Parser de Horarios Académicos.

    A partir del texto extraido de un horario, detecta sesiones semanales por:
    - asignatura, curso (si está presente), grupo, día de la semana,
      franja horaria, aula y modalidad (teoría/prácticas/lab).

    Produce un objeto `ScheduleSheet` y ofrece `to_normalized()` para
    generar un dict listo para persistencia (agrupando por grupo docente
    y listando las sesiones).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Inicializa el parser con una configuración por defecto ampliable.

        Args:
            config: Diccionario opcional para sobreescribir ajustes por defecto.
        """
        cfg = DEFAULT_HORARIO_CONFIG.copy()
        if config:
            cfg.update(config)
        super().__init__(cfg)
        self.name = self.__class__.__name__

    def parse_text(self, text: str, metadata: Optional[ExtractionMetadata] = None) -> ScheduleSheet:
        """
        Punto de entrada: parsea el texto de un horario y devuelve un ScheduleSheet.

        Flujo:
          1) Preprocesa el texto para mitigar artefactos del OCR.
          2) Extrae programa y periodo si están presentes.
          3) Segmenta por bloques de 'CURSO'.
          4) Dentro de cada bloque, segmenta por día.
          5) Extrae entradas (sesiones) por día y acumula.

        Args:
            text: Texto OCR del horario.
            metadata: Metadatos de extracción (opcional).

        Returns:
            ScheduleSheet con todas las entradas (sesiones) detectadas.

        Raises:
            ParserError: Si la validación final detecta errores bloqueantes.
        """
        # Preprocesamiento
        t = self._preprocess_text(text)

        # Extrae programa y periodo
        programa, periodo_text = self._extract_programa_periodo(t)

        # Segmenta por bloques de curso
        bloques_curso = self._segment_by_curso(t)

        # Segmenta por día y extrae sesiones
        entries: List[ScheduleEntry] = []
        for curso, bloque in bloques_curso.items():
            bloques_dia = self._segment_days(bloque)
            for day_name, bloque_dia in bloques_dia.items():
                entries.extend(self._extract_entries_from_day(day_name, bloque_dia, curso))

        # Construye el ScheduleSheet
        sheet = ScheduleSheet(
            programa=programa,
            periodo_text=periodo_text,
            entries=entries,
            raw_text=text,
            metadata=metadata,
        )

        # Validación
        ok, errors = self.validate(sheet)
        if not ok:
            raise ParserError(f"HorarioParser: errores de validación: {errors}")
        
        # Retorno del objeto tipado
        return sheet

    # Extractores de alto nivel
    def _extract_programa_periodo(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Intenta extraer el nombre del programa y el texto del periodo.

        Heurística:
          - Programa: primeras líneas en mayúsculas 'anchas'.
          - Periodo: 'PRIMER/SEGUNDO CUATRIMESTRE' si aparece en el documento.

        Args:
            text: Texto preprocesado.

        Returns:
            (programa, periodo_text) como tupla de opcionales.
        """
        programa = None
        periodo_text = None

        # Buscar programa en las primeras líneas (mayúsculas y longitud mínima)
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(PROGRAM_RX, line)
            if m:
                programa = m.group("programa").strip()
                break

        # Buscar periodo en todo el texto
        m_periodo = re.search(PERIODO_RX, text, flags=re.IGNORECASE)
        if m_periodo:
            periodo_text = m_periodo.group(0).strip()

        return programa, periodo_text

    def _segment_by_curso(self, text: str) -> Dict[Optional[int], str]:
        """
        Divide el documento en bloques por 'CURSO' (PRIMER/SEGUNDO/…).

        Si no se detectan tokens de curso, devuelve un único bloque con clave None.

        Args:
            text: Texto preprocesado.

        Returns:
            Diccionario {curso:int|None -> bloque_de_texto:str}.
        """
        # Buscar posiciones de los tokens de curso
        curso_pos = []
        for curso_num, curso_rx in CURSO_TOKENS:
            for m in re.finditer(curso_rx, text, flags=re.IGNORECASE):
                curso_pos.append((m.start(), curso_num))

        # Si no hay tokens, todo el texto es un único bloque
        if not curso_pos:
            return {None: text}

        # Ordenar por posición
        curso_pos.sort()
        bloques = {}
        for idx, (start, curso_num) in enumerate(curso_pos):
            end = curso_pos[idx + 1][0] if idx + 1 < len(curso_pos) else len(text)
            bloque = text[start:end].strip()
            bloques[curso_num] = bloque

        return bloques

    def _segment_days(self, block: str) -> Dict[str, str]:
        """
        Divide un bloque de 'CURSO' en sub-bloques por día de la semana.

        Estrategia:
          - Usa un split por líneas que contienen exactamente el nombre del día.
          - Normaliza 'MIERCOLES' -> 'MIÉRCOLES'.

        Args:
            block: Texto del bloque de curso.

        Returns:
            Diccionario {nombre_dia:str -> bloque_dia:str}.
        """
        # Normaliza los nombres de los días
        day_map = {d.upper(): d for d in DAYS}
        lines = block.splitlines()
        day_indices = []
        for idx, line in enumerate(lines):
            l = line.strip().upper()
            if l in day_map:
                day_indices.append((idx, day_map[l]))

        # Si no hay días, todo el bloque se asocia a None
        if not day_indices:
            return {None: block}

        # Segmenta por índices de días
        bloques = {}
        for i, (start_idx, day_name) in enumerate(day_indices):
            end_idx = day_indices[i + 1][0] if i + 1 < len(day_indices) else len(lines)
            bloque_dia = "\n".join(lines[start_idx + 1:end_idx]).strip()
            bloques[day_name] = bloque_dia

        return bloques

    def _extract_entries_from_day(self, day_name: str, block: str, curso: Optional[int]) -> List[ScheduleEntry]:
        """
        Extrae todas las sesiones de un sub-bloque de día.

        Mantiene un contexto local con (asignatura, grupo, aula, modalidad)
        y empareja tokens de hora en parejas (inicio, fin).

        Args:
            day_name: Día de la semana (LUNES..VIERNES).
            block: Texto del día.
            curso: Curso numérico (1..5) o None si no está definido.

        Returns:
            Lista de ScheduleEntry para ese día.
        """
        entries: List[ScheduleEntry] = []
        time_buffer: List[str] = []
        current_subject: Optional[str] = None
        current_group: Optional[str] = None
        current_aula: Optional[str] = None
        current_mode: Optional[str] = None

        lines = block.splitlines()

        def flush_times():
            """Crea entradas a partir de los tokens acumulados de hora y limpia el buffer."""
            nonlocal entries, time_buffer, current_subject, current_group, current_aula, current_mode
            if not current_subject or not current_aula or not time_buffer:
                time_buffer = []
                return
            pairs = self._parse_times(" ".join(time_buffer))
            for t_ini, t_fin in pairs:
                entries.append(
                    ScheduleEntry(
                        asignatura=current_subject,
                        curso=curso,
                        grupo=current_group or "G0",
                        dia_semana=day_name,
                        hora_inicio=t_ini,
                        hora_fin=t_fin,
                        aula=current_aula,
                        modalidad=current_mode,
                        recurrencia="SEMANAL",
                    )
                )
            time_buffer = []

        for ln in lines:
            aula = self._parse_aula(ln)
            if aula:
                current_aula = aula

            subj, grp, mode = self._parse_subject_and_tags(ln)
            if subj:
                if time_buffer:
                    flush_times()
                current_subject = subj
                current_group = grp
                current_mode = mode or self._infer_modalidad(ln) or current_mode

            if re.search(HOUR_TOKEN, ln):
                time_buffer.extend(re.findall(HOUR_TOKEN, ln))

        if time_buffer:
            flush_times()

        return entries
        

    # Utilidades de parsing
    def _normalize_line(self, s: str) -> str:
        """
        Limpia espacios redundantes en una línea.

        Args:
            s: Línea de texto original.

        Returns:
            Línea con espacios colapsados y bordes recortados.
        """
        s = s.replace('\xa0', ' ')
        s = re.sub(r'\s+', ' ', s)
        return s.strip()

    def _parse_subject_and_tags(self, line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detecta (asignatura, grupo, modalidad) presentes en una línea.

        Heurística:
          - `grupo`: busca patrón 'Grupo N'.
          - `modalidad`: si detecta etiquetas LAB/PL/Práct., la marca como 'LAB'
            (o práctica, según la decisión de negocio).
          - `asignatura`: la línea que no es pura hora/aula/curso se asume como
            nombre de asignatura (permite nombres cortos tipo 'ODS').

        Args:
            line: Línea normalizada.

        Returns:
            Tupla (asignatura|None, grupo|None, modalidad|None).
        """
        line = self._normalize_line(line)
        grupo = None
        modalidad = None

        m_grupo = re.search(GRUPO_RX, line)
        if m_grupo:
            grupo = m_grupo.group(0).strip()

        if re.search(LAB_TAGS, line, flags=re.IGNORECASE):
            modalidad = "LAB"
        else:
            modalidad = None

        # Si la línea no es pura hora ni aula ni grupo, la asumimos como asignatura
        if not re.search(HOUR_TOKEN, line) and not re.search(AULA_RX, line) and not m_grupo:
            asignatura = line if line else None
        else:
            asignatura = None

        return asignatura, grupo, modalidad

    def _parse_aula(self, s: str) -> Optional[str]:
        """
        Extrae el identificador de aula si aparece en la línea.

        Args:
            s: Línea normalizada.

        Returns:
            Nombre/código de aula en mayúsculas o None si no se detecta.
        """
        m = re.search(AULA_RX, s)
        if m:
            return m.group(0).strip().upper()
        return None

    def _parse_times(self, s: str) -> List[Tuple[time, time]]:
        """
        Convierte una secuencia de tokens de hora en parejas (inicio, fin).

        Acepta formatos '8:30', '0830', '18:30' o '1830'. Ignora tokens
        que no puedan formar parejas válidas (ini < fin).

        Args:
            s: Cadena con los tokens capturados.

        Returns:
            Lista de parejas (hora_inicio, hora_fin) como objetos datetime.time.
        """
        tokens = re.findall(HOUR_TOKEN, s)
        times = []
        for tok in tokens:
            # Normaliza formato
            if ':' in tok:
                h, m = tok.split(':')
            else:
                h, m = tok[:-2], tok[-2:]
            try:
                t = time(int(h), int(m))
                times.append(t)
            except Exception:
                continue
        # Empareja en pares (inicio, fin)
        pairs = []
        for i in range(0, len(times) - 1, 2):
            ini, fin = times[i], times[i + 1]
            if ini < fin:
                pairs.append((ini, fin))
        return pairs

    def _infer_modalidad(self, s: str) -> str:
        """
        Determina modalidad a partir de etiquetas presentes en la línea.

        Args:
            s: Línea normalizada.

        Returns:
            'LAB' si detecta tags de laboratorio/prácticas; en caso contrario,
            el valor por defecto configurado (p. ej., 'TEORIA').
        """
        if re.search(LAB_TAGS, s, flags=re.IGNORECASE):
            return "LAB"
        return self.config.get("default_modalidad", "TEORIA")

    # Preprocesamiento
    def _preprocess_text(self, text: str) -> str:
        """
        Normaliza el texto manteniendo saltos de línea útiles.

        Aplica:
          - Sustitución de NBSP.
          - Normalización de finales de línea.
          - Inserta salto tras 'AULA <id>' si está pegado al siguiente token.
          - Elimina guiones de corte de palabra al final de línea.
          - Colapsa espacios en cada línea sin perder estructura vertical.

        Args:
            text: Texto OCR original.

        Returns:
            Texto preprocesado apto para segmentación y extracción.
        """
            # Sustituye NBSP y normaliza saltos de línea
        t = text.replace('\xa0', ' ')
        t = t.replace('\r\n', '\n').replace('\r', '\n')

        # Elimina guiones de corte de palabra al final de línea
        t = re.sub(r'-\n', '', t)

        # Inserta salto tras 'AULA <id>' si está pegado al siguiente token
        t = re.sub(r'(AULA\s+[A-Za-z0-9]+)(\S)', r'\1\n\2', t)

        # Colapsa espacios en cada línea
        lines = t.split('\n')
        lines = [re.sub(r'\s+', ' ', ln).strip() for ln in lines if ln.strip()]
        return '\n'.join(lines)

    # Validación/salida
    def validate(self, parsed: ScheduleSheet) -> Tuple[bool, List[str]]:
        """
        Valida el `ScheduleSheet` resultante.

        Reglas mínimas:
          - Debe haber al menos una sesión.
          - Cada sesión debe tener asignatura, aula, día válido
            y un rango horario (inicio < fin).

        Args:
            parsed: Objeto `ScheduleSheet` ya construido.

        Returns:
            (ok, errores) con bandera booleana y lista de mensajes.
        """
        errors = []
        if not parsed.entries or len(parsed.entries) == 0:
            errors.append("No se detectó ninguna sesión en el horario.")
        for i, entry in enumerate(parsed.entries):
            if not entry.asignatura:
                errors.append(f"Sesión {i+1}: asignatura vacía.")
            if not entry.aula:
                errors.append(f"Sesión {i+1}: aula vacía.")
            if not entry.dia_semana or entry.dia_semana not in DAYS:
                errors.append(f"Sesión {i+1}: día de semana inválido ({entry.dia_semana}).")
            if not entry.hora_inicio or not entry.hora_fin or entry.hora_inicio >= entry.hora_fin:
                errors.append(f"Sesión {i+1}: rango horario inválido ({entry.hora_inicio} - {entry.hora_fin}).")
        ok = len(errors) == 0
        return ok, errors
    
    def to_normalized(self, parsed: ScheduleSheet) -> Dict[str, Any]:
        """
        Genera un payload estable para la capa de persistencia.

        Agrupa entradas por (asignatura, curso, grupo, modalidad) para
        proponer un `GrupoDocente` con un código derivado, y anexa sus
        `Sesiones` semanales con datos de día, horas y aula.

        Nota: el mapeo a Enums (DiaSemana, ModalidadSesion, TipoRecurrencia)
        y la resolución de `aula_nombre` a `Aula` concreta se recomienda
        realizarla en la capa de servicio.

        Args:
            parsed: Objeto `ScheduleSheet` ya validado.

        Returns:
            Diccionario con claves:
              - programa
              - periodo_text
              - grupos_docentes: lista de grupos con sus sesiones
              - _meta: información auxiliar
        """
        grupos: Dict[str, Dict[str, Any]] = {}
        for entry in parsed.entries:
            # Clave de agrupación: asignatura, curso, grupo, modalidad
            key = (
                (entry.asignatura or ""),
                (entry.curso or ""),
                (entry.grupo or ""),
                (entry.modalidad or "")
            )
            key_str = "|".join([str(k) for k in key])
            if key_str not in grupos:
                grupos[key_str] = {
                    "codigo": self._slug("-".join([str(k) for k in key if k])),
                    "asignatura": entry.asignatura,
                    "curso": entry.curso,
                    "grupo": entry.grupo,
                    "modalidad": entry.modalidad,
                    "sesiones": []
                }
            grupos[key_str]["sesiones"].append({
                "dia_semana": entry.dia_semana,
                "hora_inicio": entry.hora_inicio.strftime("%H:%M") if entry.hora_inicio else None,
                "hora_fin": entry.hora_fin.strftime("%H:%M") if entry.hora_fin else None,
                "aula": entry.aula,
                "recurrencia": entry.recurrencia
            })
        return {
            "programa": parsed.programa,
            "periodo_text": parsed.periodo_text,
            "grupos_docentes": list(grupos.values()),
            "_meta": {
                "num_sesiones": len(parsed.entries),
                "raw_text": parsed.raw_text,
                "metadata": parsed.metadata,
            }
        }

    # -----------------------
    # Auxiliares
    # -----------------------

    def _slug(self, s: str) -> str:
        """
        Genera un identificador compacto (código de grupo) a partir de un nombre.

        Args:
            s: Texto base (normalmente, nombre de asignatura).

        Returns:
            Cadena en MAYÚSCULAS con separadores '-', sin duplicados ni extremos.
        """
        s = re.sub(r"[^A-Za-z0-9]+", "-", s.strip(), flags=re.UNICODE)
        return re.sub(r"-{2,}", "-", s).strip("-").upper()