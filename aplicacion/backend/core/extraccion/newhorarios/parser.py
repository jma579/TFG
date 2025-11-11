
"""Parser para transformar las tablas de horarios en sesiones estructuradas."""

from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple
import re
import time
import logging

from core.extraccion.common.entities import ParserError, ParsingMetadata, Warning

from core.extraccion.newhorarios.constants import DEFAULT_PARSER_CONFIG, RX_HORA, DIAS_SEMANA, DAYS_MAP
from core.extraccion.newhorarios.entities import (
	Horario,
	HorarioExtractionResult,
	ParsingResult,
	Sesion,
	TablaHorario,
)


class HorarioParser:
	"""Parser especializado para convertir tablas de horarios en sesiones."""

	def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
		cfg = DEFAULT_PARSER_CONFIG.copy()
		if config:
			cfg.update(config)
		self.config = cfg
		self.name = self.__class__.__name__

		# Logger
		self.logger = logging.getLogger(__name__)
		if 'log_level' in self.config:
			try:
				self.logger.setLevel(getattr(logging, str(self.config['log_level']).upper(), logging.INFO))
			except Exception:
				self.logger.setLevel(logging.INFO)

	# ------------------------------------------------------------------
	# API pública
	# ------------------------------------------------------------------
	def parse(self, extraction_result: HorarioExtractionResult) -> ParsingResult:
		"""Parsea el resultado de extracción y construye sesiones estructuradas."""

		start_time = time.time()
		# usar atributos de instancia para acumular warnings/errores durante el parseo
		self.warnings: List[Warning] = []
		self.errors: List[str] = []
		self.logger.info(f"Iniciando parseo: titulo='{extraction_result.titulo}' tablas={len(extraction_result.tablas)}")

		if not extraction_result.tablas:
			raise ParserError("No se encontraron tablas de horario para parsear.")

		plan, periodo = self._parse_title(extraction_result.titulo)
		if periodo is None:
			self.warnings.append(Warning(
				message="No se pudo determinar el periodo a partir del título.",
				severity="moderate",
			))
			self.logger.warning("No se pudo determinar el periodo a partir del título")
			periodo = "DESCONOCIDO"

		horarios: List[Horario] = []
		for tabla in extraction_result.tablas:
			self.logger.debug(f"Parseando tabla: curso={tabla.curso} pagina={tabla.pagina} filas={len(tabla.celdas) if tabla.celdas else 0} cols={len(tabla.day_columns) if tabla.day_columns else 0}")
			try:
				horario = self._parse_tabla(tabla=tabla, periodo=periodo)
				horarios.append(horario)
			except ParserError as exc:
				# errores de tabla se registran en self.errors
				msg = str(exc)
				self.errors.append(msg)
				self.logger.error(f"Error parseando tabla: {msg}")

		if not horarios:
			raise ParserError("El parser no generó horarios válidos.")

		metadata = self._build_parsing_metadata(start_time=start_time)

		raw_json = self._build_raw_json(
			titulo=extraction_result.titulo,
			plan=plan,
			periodo=periodo,
			horarios=horarios,
		)
		parse_duration = time.time() - start_time
		self.logger.info(f"Parseo finalizado: tablas_procesadas={len(horarios)} sesiones_totales={sum(len(h.sesiones) for h in horarios)} warnings={len(self.warnings)} errors={len(self.errors)} duracion_s={parse_duration:.2f}")

		return ParsingResult(
			titulo=extraction_result.titulo,
			horarios=horarios,
			extraction_metadata=extraction_result.metadata,
			parsing_metadata=metadata,
			raw_json=raw_json,
		)

	# ------------------------------------------------------------------
	# Helpers principales
	# ------------------------------------------------------------------
	def _parse_tabla(self, tabla: TablaHorario, periodo: str) -> Horario:
		"""Convierte una tabla en un `Horario` con sus sesiones."""

		sesiones: List[Sesion] = []

		if not tabla.celdas:
			self.warnings.append(Warning(
				message="Tabla sin contenido de celdas detectada.",
				severity="moderate",
			))
			self.logger.warning(f"Tabla vacía detectada: curso={tabla.curso} pagina={tabla.pagina}")

		horario = Horario(
			curso=tabla.curso or "DESCONOCIDO",
			periodo=periodo,
			sesiones=sesiones,
			mencion=tabla.mencion,
			pagina=tabla.pagina,
		)

		# -------------------------------------------------------------
		# Recorremos filas (franjas horarias) y columnas (días)
		# tabla.time_rows :: List[str]
		# tabla.day_columns :: List[str]
		# tabla.celdas :: List[List[Optional[str]]]  (filas x columnas)
		# -------------------------------------------------------------
		n_rows = len(tabla.time_rows or [])
		n_cols = len(tabla.day_columns or [])

		if not n_rows or not n_cols:
			self.warnings.append(Warning(
				message="Tabla sin filas de hora o sin columnas de día.",
				severity="moderate",
			))
			self.logger.warning(f"Tabla sin filas o columnas válidas: curso={tabla.curso} pagina={tabla.pagina} n_rows={n_rows} n_cols={n_cols}")
			return horario

		# Recorremos cada celda
		for i_row, row in enumerate(tabla.celdas):
			# hora de inicio (puede fallar si formato no esperado)
			hora_inicio = None
			if i_row < len(tabla.time_rows):
				hora_inicio = self._parse_time(tabla.time_rows[i_row])

			for j_col in range(n_cols):
				cell = None
				if j_col < len(row):
					cell = row[j_col]

				if not cell or not str(cell).strip():
					continue

				entries = self._split_cell_into_entries(str(cell))
				dia_label = tabla.day_columns[j_col] if j_col < len(tabla.day_columns) else None
				dia_norm = self._normalize_day(dia_label) if dia_label else None

				for entry in entries:
					asignatura, aula, tipo, grupo = self._infer_aula_tipo_grupo(entry)

					if hora_inicio is None:
						msg = f"Hora de inicio no válida en fila {i_row}: '{tabla.time_rows[i_row] if i_row < len(tabla.time_rows) else ''}'"
						self.warnings.append(Warning(message=msg, severity="minor"))
						self.logger.warning(msg)
						continue

					hora_fin = self._infer_hora_fin(i_row, tabla.time_rows, hora_inicio)

					ses = Sesion(
						asignatura=asignatura,
						aula=aula,
						dia=dia_norm or (dia_label or "DESCONOCIDO"),
						hora_inicio=hora_inicio,
						hora_fin=hora_fin,
						tipo=tipo,
						grupo=grupo,
					)
					sesiones.append(ses)
					self.logger.debug(f"Sesion añadida: dia={ses.dia} hora={ses.hora_inicio.strftime('%H:%M')}-{ses.hora_fin.strftime('%H:%M')} asignatura='{ses.asignatura}' aula={ses.aula} tipo={ses.tipo} grupo={ses.grupo}")

		horario.sesiones = sesiones
		return horario

	def _parse_title(self, titulo: str) -> Tuple[Optional[str], Optional[str]]:
		"""Extrae titulacion y periodo del título del documento."""

		if not titulo:
			return None, None

		normalized = " ".join(titulo.split())
		upper = normalized.upper()

		periodo: Optional[str] = None
		if "PRIMER" in upper and "CUATRIMESTRE" in upper:
			periodo = "PRIMER CUATRIMESTRE"
		elif "SEGUNDO" in upper and "CUATRIMESTRE" in upper:
			periodo = "SEGUNDO CUATRIMESTRE"

		# Intenta extraer la parte del plan eliminando el periodo detectado
		plan = normalized
		if periodo:
			plan = re.sub(periodo, "", plan, flags=re.IGNORECASE).strip()

		return plan or None, periodo

	def _build_parsing_metadata(self, start_time: float) -> ParsingMetadata:
		"""Genera los metadatos del proceso de parsing usando atributos de instancia.

		Args:
			start_time: timestamp de inicio (time.time()).

		Returns:
			ParsingMetadata con warnings y errors recogidos en la instancia.
		"""

		return ParsingMetadata(
			parser_name=self.name,
			parser_version=self.config.get("version"),
			parse_timestamp=datetime.now().isoformat(),
			parse_duration=time.time() - start_time,
			warnings=getattr(self, 'warnings', []),
			errors=getattr(self, 'errors', []),
		)

	def _build_raw_json(
		self,
		titulo: str,
		plan: Optional[str],
		periodo: str,
		horarios: List[Horario],
	) -> Dict[str, Any]:
		"""Construye una representación serializable del resultado."""

		raw_horarios: List[Dict[str, Any]] = []
		for horario in horarios:
			raw_sesiones: List[Dict[str, Any]] = []
			for sesion in horario.sesiones:
				raw_sesiones.append(
					{
						"asignatura": sesion.asignatura,
						"aula": sesion.aula,
						"dia": sesion.dia,
						"hora_inicio": sesion.hora_inicio.strftime("%H:%M"),
						"hora_fin": sesion.hora_fin.strftime("%H:%M"),
						"tipo": sesion.tipo,
						"grupo": sesion.grupo,
					}
				)

			raw_horarios.append(
				{
					"curso": horario.curso,
					"periodo": horario.periodo,
					"mencion": horario.mencion,
					"pagina": horario.pagina,
					"sesiones": raw_sesiones,
				}
			)

		return {
			"titulo": titulo,
			"plan": plan,
			"periodo": periodo,
			"horarios": raw_horarios,
		}

	# ------------------------------------------------------------------
	# Funciones auxiliares para parsing
	# ------------------------------------------------------------------
	def _parse_time(self, text: str) -> Optional[dt_time]:
		"""Parsea una cadena que contiene una hora y devuelve datetime.time.

		Acepta formatos como '08:30', '8:30', '08.30', '0830'.

		Args:
			text: Cadena que puede contener una hora.

		Returns:
			datetime.time si se detecta una hora válida, o None si no se puede parsear.
		"""
		if not text:
			return None
		m = RX_HORA.search(text)
		if not m:
			self.logger.debug(f"_parse_time: no se encontró hora en '{text}'")
			return None
		raw = m.group(0)
		# Normalizar separadores
		raw = raw.replace('.', ':')
		# Si viene sin separador y tiene 3 o 4 dígitos, convertir a HH:MM
		digits = re.sub(r'\D', '', raw)
		if len(digits) in (3,4) and ':' not in raw:
			if len(digits) == 3:
				h = int(digits[0])
				m_ = int(digits[1:])
			else:
				h = int(digits[:2])
				m_ = int(digits[2:])
			try:
				return dt_time(hour=h, minute=m_)
			except ValueError:
				return None
		# Si tiene separador
		parts = raw.split(':')
		try:
			h = int(parts[0])
			mi = int(parts[1]) if len(parts) > 1 else 0
			return dt_time(hour=h, minute=mi)
		except Exception:
			self.logger.debug(f"_parse_time: fallo al parsear partes de hora '{text}' -> {parts}")
			return None

	def _infer_hora_fin(self, row_idx: int, time_rows: List[str], hora_inicio: dt_time) -> dt_time:
		"""Inferir la hora de fin para una sesión.

		Si existe una franja siguiente en time_rows se usa como fin; si no, se aplica
		la duración máxima configurada (por defecto 120 minutos).

		Args:
			row_idx: índice de la franja de inicio
			time_rows: lista de strings con horas de inicio de cada franja
			hora_inicio: datetime.time del inicio

		Returns:
			datetime.time calculada como fin de la sesión
		"""
		# Intentar siguiente franja
		if row_idx + 1 < len(time_rows):
			next_time = self._parse_time(time_rows[row_idx + 1])
			if next_time:
				self.logger.debug(f"_infer_hora_fin: usando siguiente franja '{time_rows[row_idx+1]}' como fin")
				return next_time

		# Fallback: añadir duración máxima
		max_minutes = int(self.config.get('max_session_duration_minutes', 120))
		self.logger.debug(f"_infer_hora_fin: aplicando fallback max_minutes={max_minutes} para hora_inicio={hora_inicio}")
		# Usar fecha arbitraria para sumar
		base = datetime(2000,1,1, hora_inicio.hour, hora_inicio.minute)
		end_dt = base + timedelta(minutes=max_minutes)
		return dt_time(hour=end_dt.hour, minute=end_dt.minute)

	def _split_cell_into_entries(self, cell_text: str) -> List[str]:
		"""Divide el texto de una celda en una o más entradas de sesión.

		Heurísticas:
		- Normaliza espacios y saltos de línea
		- Si el contenido tiene varias líneas y alguna línea contiene 'AULA' o 'PL' se
		  considera todo el bloque como una única entrada (nombre + aula)
		- En otros casos, separa por líneas y por delimitadores comunes (';', '/')

		Args:
			cell_text: texto bruto de la celda

		Returns:
			Lista de entradas (cada entrada se procesa como una sesión separada)
		"""
		if not cell_text:
			return []
		lines = [ln.strip() for ln in re.split(r'\r?\n', cell_text) if ln and ln.strip()]
		if not lines:
			return []
		# Si hay varias líneas y alguna indica aula o PL/PA, unir en un solo bloque
		indicator = any(re.search(r'\bAULA\b|\bPL\b|\bPA\b|LABORATORIO|SEMINARIO', ln, re.IGNORECASE) for ln in lines)
		if len(lines) > 1 and indicator:
			merged = ' '.join(lines)
			self.logger.debug(f"_split_cell_into_entries: merge lines -> '{merged}'")
			return [merged]

		entries: List[str] = []
		for ln in lines:
			# dividir por separadores internos
			parts = re.split(r'\s*[;/|\\]\s*', ln)
			for p in parts:
				p = p.strip()
				if p:
					entries.append(p)
		self.logger.debug(f"_split_cell_into_entries: '{cell_text}' -> {entries}")
		return entries

	def _infer_aula_tipo_grupo(self, entry: str) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
		"""Inferir nombre de asignatura, aula, tipo y grupo a partir de una entrada de celda.

		Reglas:
		- Detecta patrones 'AULA <ident>' (ej. 'AULA 4')
		- Detecta grupos de prácticas 'PL <n>' o 'PA <n>' y los asigna a tipo/grupo
		- El resto del texto se considera el nombre de la asignatura

		Args:
			entry: cadena con la información de la celda (puede contener aula y grupo)

		Returns:
			(asignatura, aula_or_None, tipo_or_None, grupo_or_None)
		"""
		text = ' '.join(entry.split())
		# Buscar aula
		aula = None
		ma = re.search(r'\bAULA\s*[:\-]?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
		if ma:
			aula = ma.group(1).strip()
			# eliminar del texto
			text = re.sub(ma.group(0), '', text, flags=re.IGNORECASE).strip()

		# Buscar tipo/grupo PL/PA
		tipo = None
		grupo = None
		mg = re.search(r'\b(P[Ll]|P[Aa])\s*[:\-]?\s*(\d+)', entry)
		if mg:
			tipo = mg.group(1).upper()
			grupo = mg.group(2)
			# eliminar
			text = re.sub(mg.group(0), '', text)

		# Limpiar sufijos comunes como 'AULA', 'LAB', 'SEMINARIO' que no aporten
		text = re.sub(r'\b(AULA|AUL|LABORATORIO|LAB|SEMINARIO)\b\s*[:\-]?\s*', '', text, flags=re.IGNORECASE)
		# Final asignatura
		asignatura = text.strip()
		if not asignatura:
			asignatura = "DESCONOCIDO"
		self.logger.debug(f"_infer_aula_tipo_grupo: entry='{entry}' -> asignatura='{asignatura}', aula='{aula}', tipo='{tipo}', grupo='{grupo}'")
		return asignatura, aula, tipo, grupo

	def _normalize_day(self, dia_label: str) -> Optional[str]:
		"""Normaliza una etiqueta de columna de día a los nombres estandarizados.

		Ejemplos: 'LUN', 'LUNES' -> 'LUNES'
		"""
		if not dia_label:
			return None
		lab = dia_label.strip().upper()
		# Direct match
		if lab in DIAS_SEMANA:
			return lab
		# Abreviaturas
		short = lab[:3]
		if short in DAYS_MAP:
			return DAYS_MAP[short]
		# Fallback: devolver la etiqueta en mayúsculas
		return lab
