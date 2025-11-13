
"""Parser para transformar las tablas de horarios en sesiones estructuradas."""

from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple
import re
import time
import logging

from core.extraccion.common.entities import ParserError, ParsingMetadata, Warning

from core.extraccion.newhorarios.constants import (
    DEFAULT_PARSER_CONFIG, 
	RX_HORA, PATRON_MAYUSCULA_SIN_ESPACIO, PATRON_NORMALIZAR_ESPACIOS,
	PATRON_GRUPO_PL, PATRON_GRUPO_PA, PATRON_GRUPO_GENERICO,
	TIPO_PRACTICA_AULA, TIPO_PRACTICA, PATRON_AULA_COMBINADO,
	TIPO_TEORIA, DURACION_MAXIMA_SESION, DURACION_DEFAULT_ULTIMA_SESION,
	DURACION_MINIMA_SESION, PATRON_PERIODO
)
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

		# Valores iniciales del parsing
		start_time = time.time()
		self.warnings: List[Warning] = []
		self.errors: List[str] = []

		self.logger.info(f"Iniciando parseo: titulo='{extraction_result.titulo}' tablas={len(extraction_result.tablas)}")

		if not extraction_result.tablas:
			raise ParserError("No se encontraron tablas de horario para parsear.")

		# Parseo del título
		try: 
			plan, periodo = self._parse_title(extraction_result.titulo)
			if plan is None:
				self.errors.append("No se pudo determinar el plan a partir del título.")
				self.logger.error("No se pudo determinar el plan a partir del título.")
			if periodo is None:
				self.errors.append("No se pudo determinar el periodo a partir del título.")
				self.logger.error("No se pudo determinar el periodo a partir del título.")
		except Exception as exc:
			self.logger.error(f"Error al parsear el título: {exc}")
			self.errors.append(f"Error al parsear el título: {exc}")


		horarios: List[Horario] = []
		for tabla in extraction_result.tablas:
			self.logger.debug(f"Parseando tabla: curso={tabla.curso} pagina={tabla.pagina} filas={len(tabla.celdas) if tabla.celdas else 0} cols={len(tabla.day_columns) if tabla.day_columns else 0}")
			try:
				horario = self._parse_tabla(tabla=tabla, periodo=periodo)
				if not horario.sesiones:
					self.errors.append(f"La tabla en la página {tabla.pagina} no generó sesiones válidas.")
					self.logger.error(f"La tabla en la página {tabla.pagina} no generó sesiones válidas.")
				else:
					horarios.append(horario)
			except ParserError as exc:
				msg = str(exc)
				self.errors.append(msg)
				self.logger.error(f"Error parseando tabla: {msg}")

		if not horarios:
			raise ParserError("El parser no generó horarios válidos.")

		# Construcción de los metadatos de parsing
		parser_metadata = ParsingMetadata(
            parser_name=self.name,
            parser_version=self.config.get("version"),
            parse_timestamp=datetime.now(),
            parse_duration=time.time() - start_time,
            warnings=self.warnings,
            errors=self.errors,
        )

		resultado = ParsingResult(
			titulo=plan,
			horarios=horarios,
			extraction_metadata=extraction_result.metadata,
			parsing_metadata=parser_metadata,
		)
		
		self.logger.info(
			f"Parseo finalizado: tablas_procesadas={len(horarios)} sesiones_totales={sum(len(h.sesiones) for h in horarios)} "
			f"warnings={len(self.warnings)} errors={len(self.errors)} duracion_s={parser_metadata.parse_duration:.2f}")

		return self._to_normalize(
			parsed=resultado,
			extraction_metadata=extraction_result.metadata,
			parser_metadata=parser_metadata,
		)

	# ------------------------------------------------------------------
	# Helpers principales
	# ------------------------------------------------------------------
	def _parse_title(self, titulo: str) -> Tuple[Optional[str], Optional[str]]:
		"""
        Extrae plan (titulación) y periodo a partir del título bruto del documento.
        Ejemplos:
            "DOBLE GRADO EN FÍSICA Y MATEMÁTICAS PRIMER CUATRIMESTRE"
            "GRADO EN INGENIERÍA INFORMÁTICA SEGUNDO CUATRIMESTRE"
        Retorna (plan, periodo). Si no se detecta periodo, devuelve (plan, None).
        """
		if not titulo:
			self.logger.error("Título vacío proporcionado al parser.")
			raise ParserError("Título vacío")

		titulo = titulo.strip()

        # Patrón de periodo (solo PRIMER / SEGUNDO CUATRIMESTRE por ahora)
		m_periodo = PATRON_PERIODO.search(titulo)

		if not m_periodo:
            # No se pudo identificar periodo
			self.logger.error("_parse_title: No se pudo determinar el periodo a partir del título.")
			plan = titulo.strip() or None
			return plan, None

        # Cortar directamente sobre el original para preservar acentos/formato
		start, end = m_periodo.span()
		periodo = titulo[start:end].strip()
		plan = titulo[:start].strip()

        # Normalización ligera
		plan = PATRON_NORMALIZAR_ESPACIOS.sub(" ", plan).strip(" -–—") or None 
		periodo = PATRON_NORMALIZAR_ESPACIOS.sub(" ", periodo) or None 

		if plan is None:
			self.logger.error("_parse_title: No se pudo determinar el plan a partir del título.")

		self.logger.debug(f"_parse_title: titulo='{titulo}' -> plan='{plan}' periodo='{periodo}'")
		return plan, periodo


	def _parse_tabla(self, tabla: TablaHorario, periodo: str) -> Horario:
		"""
		Parsea una tabla individual de horario y construye sus sesiones.
		
		Args:
			tabla: Tabla extraída con estructura día/hora/celdas
			periodo: Periodo académico (ej: "PRIMER CUATRIMESTRE")
		
		Returns:
			Horario con todas las sesiones parseadas
			
		Raises:
			ParserError: Si la tabla no tiene estructura válida
		"""
		self.logger.debug(
			f"Iniciando parseo de tabla: curso={tabla.curso} "
			f"mencion={tabla.mencion} pagina={tabla.pagina} "
			f"filas={len(tabla.celdas)} cols={len(tabla.day_columns)}"
		)
		
		# Validación previa de estructura
		if not tabla.day_columns:
			raise ParserError(f"Tabla en página {tabla.pagina} no tiene columnas de días")
		
		if not tabla.time_rows:
			raise ParserError(f"Tabla en página {tabla.pagina} no tiene filas de horas")
		
		if not tabla.celdas:
			raise ParserError(f"Tabla en página {tabla.pagina} no tiene celdas de contenido")
		
		# Validar dimensiones consistentes
		num_dias = len(tabla.day_columns)
		num_horas = len(tabla.time_rows)
		
		if len(tabla.celdas) != num_horas:
			self.warnings.append(Warning(
				message=f"Inconsistencia: {len(tabla.celdas)} filas de celdas vs {num_horas} horas",
				context={'pagina': tabla.pagina, 'curso': tabla.curso}
			))
		
		sesiones: List[Sesion] = []
		
		# Iterar sobre la matriz: fila (hora) x columna (día)
		for idx_fila, fila_celdas in enumerate(tabla.celdas):
			if idx_fila >= len(tabla.time_rows):
				self.warnings.append(Warning(
					message=f"Fila {idx_fila} excede time_rows disponibles, saltando, 'pagina': {tabla.pagina}, 'curso': {tabla.curso}",
					severity='medium',
				))
				self.logger.warning(f"Fila {idx_fila} excede time_rows disponibles, saltando")
				continue
			
			hora_inicio_str = tabla.time_rows[idx_fila]
			
			# Validar que tenemos suficientes columnas
			if len(fila_celdas) != num_dias:
				self.warnings.append(Warning(
					message=f"Fila {idx_fila} tiene {len(fila_celdas)} celdas, esperadas {num_dias}, {'hora': hora_inicio_str, 'pagina': tabla.pagina}",
					severity='medium',
				))
			
			for idx_col, contenido_celda in enumerate(fila_celdas):
				if idx_col >= len(tabla.day_columns):
					self.logger.warning(f"Columna {idx_col} excede day_columns disponibles, saltando")
					self.warnings.append(Warning(
						message=f"Columna {idx_col} excede day_columns disponibles, saltando, 'pagina': {tabla.pagina}, 'curso': {tabla.curso}",
						severity='medium',
					))
					continue
				
				dia = tabla.day_columns[idx_col]
				
				# Ignorar celdas vacías/null
				if not contenido_celda or not contenido_celda.strip():
					continue
				
				try:
					# 1. Parsear contenido de la celda
					info_celda = self._parse_celda(contenido_celda)
					
					# 2. Manejar herencia de asignatura si es necesario
					if not info_celda['asignatura'] and info_celda['aula']:
						# Buscar asignatura en celdas anteriores de la misma columna
						asignatura_heredada = self._buscar_asignatura_previa(
							tabla.celdas, idx_fila, idx_col
						)
						if asignatura_heredada:
							info_celda['asignatura'] = asignatura_heredada
							self.logger.debug(
								f"Heredada asignatura '{asignatura_heredada}' "
								f"en [{idx_fila}, {idx_col}]"
							)
					
					# 3. Validar que tenemos asignatura
					if not info_celda['asignatura']:
						self.logger.warning(
							f"Celda [{idx_fila}, {idx_col}] sin asignatura identificable: "
							f"'{contenido_celda}'"
						)
						continue
					
					# 4. Inferir hora de fin
					hora_inicio = self._parse_time(hora_inicio_str)
					hora_fin = self._inferir_hora_fin(
						hora_inicio=hora_inicio,
						time_rows=tabla.time_rows,
						fila_actual=idx_fila,
						celdas=tabla.celdas,
						columna_actual=idx_col
					)
					
					# 5. Crear sesión
					sesion = self._crear_sesion(
						asignatura=info_celda['asignatura'],
						aula=info_celda['aula'],
						dia=dia,
						hora_inicio=hora_inicio,
						hora_fin=hora_fin,
						tipo=info_celda['tipo'],
						grupo=info_celda['grupo']
					)
					
					sesiones.append(sesion)
					
					self.logger.debug(
						f"Sesión creada: {sesion.asignatura} | {dia} "
						f"{sesion.hora_inicio}-{sesion.hora_fin} | {sesion.aula}"
					)
					
				except Exception as exc:
					msg = (
						f"Error parseando celda [{idx_fila}, {idx_col}] "
						f"('{contenido_celda}'): {exc}"
					)
					self.logger.error(msg)
					self.warnings.append(Warning(
						message=msg,
						context={
							'fila': idx_fila,
							'columna': idx_col,
							'dia': dia,
							'hora': hora_inicio_str,
							'contenido': contenido_celda
						}
					))
					continue
		
		# Construir objeto Horario
		horario = Horario(
			curso=tabla.curso,
			periodo=periodo,
			sesiones=sesiones,
			mencion=tabla.mencion,
			pagina=tabla.pagina
		)
		
		self.logger.info(
			f"Tabla parseada: curso={tabla.curso} pagina={tabla.pagina} "
			f"sesiones_generadas={len(sesiones)}"
		)
		
		return horario
		
	def _to_normalize(self, parsed: ParsingResult, extraction_metadata: Any, parser_metadata: ParsingMetadata) -> Dict[str, Any]:
		"""
		Convierte el objeto ParsingResult a un dict alineado con los modelos/JSON
		esperados por el flujo de horarios.
			"""
		def _fmt_time(t) -> Optional[str]:
			# Acepta datetime.time, cadenas "HH:MM" o None
			if t is None:
				return None
			if isinstance(t, dt_time):
				return t.strftime("%H:%M")
			if isinstance(t, str):
				m = RX_HORA.search(t)
				if m:
					return m.group(0).replace(".", ":")
				return t
			# Fallback: convertir a cadena
			return str(t)
	
		def _serialize_sesion(s: Sesion) -> Dict[str, Any]:
			return {
				"asignatura": s.asignatura,
				"aula": s.aula,
				"dia": s.dia,
				"hora_inicio": _fmt_time(s.hora_inicio),
				"hora_fin": _fmt_time(s.hora_fin),
				"tipo": s.tipo,
				"grupo": s.grupo,
			}
	
		def _serialize_horario(h: Horario) -> Dict[str, Any]:
			return {
				"curso": h.curso,
				"periodo": h.periodo,
				"mencion": h.mencion,
				"pagina": h.pagina,
				"sesiones": [ _serialize_sesion(s) for s in (h.sesiones or []) ],
			}
	
		# Periodo global: toma el primero no vacío presente en los horarios
		periodo_global: Optional[str] = None
		for h in parsed.horarios:
			if getattr(h, "periodo", None):
				periodo_global = h.periodo
				break
	
		result: Dict[str, Any] = {
			"titulo": parsed.titulo,
			"plan": parsed.titulo,   # 'plan' y 'titulo' significan lo mismo en este flujo
			"periodo": periodo_global,
			"horarios": [ _serialize_horario(h) for h in (parsed.horarios or []) ],
		}
	
		# Metadatos de parsing (similar al flujo de fichas)
		if parser_metadata:
			result["parsing_metadata"] = {
				"parser_name": parser_metadata.parser_name,
				"parser_version": parser_metadata.parser_version,
				"parse_timestamp": parser_metadata.parse_timestamp.isoformat() + "Z" if parser_metadata.parse_timestamp else None,
				"parse_duration": parser_metadata.parse_duration,
				"warnings": [w.__dict__ for w in (parser_metadata.warnings or [])],
				"errors": parser_metadata.errors or [],
			}
	
		# Metadatos de extracción (propagación simple)
		if extraction_metadata:
			result["extraction_metadata"] = {
				"quality": extraction_metadata.quality,
				"confidence": extraction_metadata.confidence,
				"status": extraction_metadata.status,
				"processing_time_seconds": extraction_metadata.processing_time_seconds,
				"page_count": extraction_metadata.page_count,
				"file_size_mb": extraction_metadata.file_size_mb,
				"has_embedded_text": extraction_metadata.has_embedded_text,
				"char_count": extraction_metadata.char_count,
				"word_count": extraction_metadata.word_count,
				"errors": extraction_metadata.errors or [],
				"warnings": [w.__dict__ for w in (extraction_metadata.warnings or [])],
				"pages_with_text": getattr(extraction_metadata, "pages_with_text", None),
			}
	
		return result

	def _limpiar_texto(self, texto: str) -> str:
		"""
		Limpia y normaliza texto extraído de celdas.
		
		- Añade espacios antes de mayúsculas precedidas de minúsculas
		- Normaliza múltiples espacios a uno solo
		- Elimina espacios al inicio/final
		
		Args:
			texto: Texto a limpiar
			
		Returns:
			Texto limpio y normalizado
			
		Examples:
			"MecánicaClásica yrelatividad" → "Mecánica Clásica y relatividad"
			"Física  Básica   I" → "Física Básica I"
		"""
		if not texto:
			return ""
		
		# Añadir espacio antes de mayúscula precedida de minúscula
		texto = PATRON_MAYUSCULA_SIN_ESPACIO.sub(r'\1 \2', texto)
		
		# Normalizar múltiples espacios
		texto = PATRON_NORMALIZAR_ESPACIOS.sub(' ', texto)
		
		return texto.strip()


	def _parse_time(self, hora_str: str) -> dt_time:
		"""
		Convierte una cadena de hora en objeto datetime.time.
		
		Args:
			hora_str: Hora en formato "HH:MM", "HH.MM" o "HHMM"
			
		Returns:
			Objeto datetime.time
			
		Raises:
			ValueError: Si el formato no es válido
			
		Examples:
			"08:30" → time(8, 30)
			"14.45" → time(14, 45)
			"0930" → time(9, 30)
		"""
		if not hora_str:
			raise ValueError("Hora vacía proporcionada")
		
		# Usar regex para extraer hora
		match = RX_HORA.search(hora_str)
		if not match:
			raise ValueError(f"Formato de hora inválido: '{hora_str}'")
		
		hora_limpia = match.group(0).replace('.', ':')
		
		try:
			# Parsear con formato HH:MM
			if ':' in hora_limpia:
				partes = hora_limpia.split(':')
				horas = int(partes[0])
				minutos = int(partes[1])
			else:
				# Formato HHMM
				if len(hora_limpia) == 4:
					horas = int(hora_limpia[:2])
					minutos = int(hora_limpia[2:])
				elif len(hora_limpia) == 3:
					horas = int(hora_limpia[0])
					minutos = int(hora_limpia[1:])
				else:
					raise ValueError(f"Formato no reconocido: '{hora_limpia}'")
			
			# Validar rangos
			if not (0 <= horas <= 23):
				raise ValueError(f"Hora fuera de rango: {horas}")
			if not (0 <= minutos <= 59):
				raise ValueError(f"Minutos fuera de rango: {minutos}")
			
			return dt_time(hour=horas, minute=minutos)
			
		except (ValueError, IndexError) as e:
			raise ValueError(f"Error parseando hora '{hora_str}': {e}")


	def _parse_celda(self, contenido: str) -> Dict[str, Optional[str]]:
		"""
		Parsea el contenido de una celda y extrae sus componentes.
		
		Estructura esperada (por líneas):
			Línea 1: Asignatura
			Línea 2: Aula (opcional)
			Línea 3: Grupo (opcional, solo en prácticas)
		
		Args:
			contenido: Contenido de la celda (puede tener múltiples líneas)
			
		Returns:
			Diccionario con claves: 'asignatura', 'aula', 'tipo', 'grupo'
			
		Examples:
			"Cálculo Diferencial\\nAULA 4" → 
				{'asignatura': 'Cálculo Diferencial', 'aula': 'AULA 4', 
				'tipo': 'TEORÍA', 'grupo': None}
			
			"Física Básica I\\nLAB\\nPL1" →
				{'asignatura': 'Física Básica I', 'aula': 'LAB',
				'tipo': 'PRÁCTICA', 'grupo': 'PL1'}
		"""
		if not contenido or not contenido.strip():
			return {
				'asignatura': None,
				'aula': None,
				'tipo': None,
				'grupo': None
			}
		
		# Limpiar y dividir en líneas
		contenido_limpio = self._limpiar_texto(contenido)
		lineas = [linea.strip() for linea in contenido_limpio.split('\n') if linea.strip()]
		
		if not lineas:
			return {
				'asignatura': None,
				'aula': None,
				'tipo': None,
				'grupo': None
			}
		
		asignatura = None
		aula = None
		grupo = None
		tipo = None
		
		# Procesar cada línea
		for linea in lineas:
			# 1. Intentar detectar grupo (PL, PA, Grupo)
			match_pl = PATRON_GRUPO_PL.search(linea)
			match_pa = PATRON_GRUPO_PA.search(linea)
			match_generico = PATRON_GRUPO_GENERICO.search(linea)
			
			if match_pa:
				grupo = f"PA{match_pa.group(1)}"
				tipo = TIPO_PRACTICA_AULA
				continue
			elif match_pl:
				grupo = f"PL{match_pl.group(1)}"
				tipo = TIPO_PRACTICA
				continue
			elif match_generico:
				# "Grupo X" → convertir a "PLX"
				grupo = f"PL{match_generico.group(1)}"
				tipo = TIPO_PRACTICA
				continue
			
			# 2. Intentar detectar aula
			match_aula = PATRON_AULA_COMBINADO.search(linea)
			if match_aula:
				aula = match_aula.group(0).strip()
				continue
			
			# 3. Si no es grupo ni aula, asumimos que es asignatura
			# (tomamos la primera línea que no sea grupo/aula)
			if not asignatura:
				asignatura = linea
		
		# Si no se detectó tipo, asumimos TEORÍA
		if tipo is None:
			tipo = TIPO_TEORIA if self.config.get('infer_teoria_when_no_group', True) else None
		
		# Si tenemos asignatura pero no aula, marcar como desconocida
		if asignatura and not aula:
			aula = 'DESCONOCIDA'
		
		return {
			'asignatura': asignatura,
			'aula': aula,
			'tipo': tipo,
			'grupo': grupo
		}


	def _buscar_asignatura_previa(
		self, 
		celdas: List[List[Optional[str]]], 
		fila_actual: int, 
		columna: int
	) -> Optional[str]:
		"""
		Busca la asignatura en celdas anteriores de la misma columna.
		
		Útil cuando una celda solo contiene "AULA X" y necesitamos heredar
		el nombre de la asignatura de una celda superior.
		
		Args:
			celdas: Matriz completa de celdas
			fila_actual: Índice de la fila actual
			columna: Índice de la columna a buscar
			
		Returns:
			Nombre de la asignatura encontrada o None
			
		Examples:
			Si en fila 2, col 1 está "Física Básica I"
			y en fila 3, col 1 está solo "AULA 4"
			→ retorna "Física Básica I"
		"""
		# Buscar hacia atrás en la misma columna
		for idx_fila in range(fila_actual - 1, -1, -1):
			if idx_fila >= len(celdas):
				continue
			
			fila = celdas[idx_fila]
			if columna >= len(fila):
				continue
			
			contenido = fila[columna]
			if not contenido or not contenido.strip():
				continue
			
			# Parsear la celda anterior
			info_celda = self._parse_celda(contenido)
			
			# Si encontramos una asignatura, retornarla
			if info_celda['asignatura']:
				return info_celda['asignatura']
		
		return None


	def _inferir_hora_fin(
		self,
		hora_inicio: dt_time,
		time_rows: List[str],
		fila_actual: int,
		celdas: List[List[Optional[str]]],
		columna_actual: int
	) -> dt_time:
		"""
		Infiere la hora de finalización de una sesión.
		
		Lógica:
		1. Buscar hacia adelante en la misma columna
		2. Si encuentra otra asignatura diferente → hora_fin = hora_inicio de esa sesión
		3. Si solo encuentra aulas (continuación) → seguir buscando
		4. Si no hay más sesiones → hora_fin = hora_inicio + DURACION_DEFAULT_ULTIMA_SESION
		5. Máximo permitido: DURACION_MAXIMA_SESION (3 horas)
		
		Args:
			hora_inicio: Hora de inicio de la sesión actual
			time_rows: Lista de horas disponibles
			fila_actual: Índice de fila actual
			celdas: Matriz completa de celdas
			columna_actual: Índice de columna actual
			
		Returns:
			Hora de finalización calculada
		"""
		asignatura_actual = None
		
		# Obtener asignatura actual
		if fila_actual < len(celdas) and columna_actual < len(celdas[fila_actual]):
			contenido_actual = celdas[fila_actual][columna_actual]
			if contenido_actual:
				info_actual = self._parse_celda(contenido_actual)
				asignatura_actual = info_actual['asignatura']
		
		# Buscar hacia adelante en la misma columna
		for idx_fila in range(fila_actual + 1, len(time_rows)):
			# Verificar que no excedemos duración máxima
			if idx_fila >= len(time_rows):
				break
			
			hora_siguiente_str = time_rows[idx_fila]
			hora_siguiente = self._parse_time(hora_siguiente_str)
			
			# Calcular duración hasta esta franja
			duracion_minutos = (
				hora_siguiente.hour * 60 + hora_siguiente.minute -
				hora_inicio.hour * 60 - hora_inicio.minute
			)
			
			# Si excede el máximo, cortar aquí
			if duracion_minutos > DURACION_MAXIMA_SESION:
				# Usar la hora máxima permitida
				hora_maxima = (
					datetime.combine(datetime.today(), hora_inicio) + 
					timedelta(minutes=DURACION_MAXIMA_SESION)
				).time()
				return hora_maxima
			
			# Verificar si hay contenido en esta celda
			if idx_fila >= len(celdas):
				continue
			
			fila = celdas[idx_fila]
			if columna_actual >= len(fila):
				continue
			
			contenido = fila[columna_actual]
			
			# Si la celda está vacía, seguir buscando
			if not contenido or not contenido.strip():
				continue
			
			# Parsear la celda siguiente
			info_siguiente = self._parse_celda(contenido)
			
			# Si tiene asignatura diferente, termina aquí la sesión actual
			if info_siguiente['asignatura'] and info_siguiente['asignatura'] != asignatura_actual:
				return hora_siguiente
			
			# Si solo tiene aula (continuación), seguir buscando
			if not info_siguiente['asignatura'] and info_siguiente['aula']:
				continue
		
		# No se encontró siguiente sesión → usar duración por defecto
		duracion_default = timedelta(minutes=DURACION_DEFAULT_ULTIMA_SESION)
		hora_fin = (datetime.combine(datetime.today(), hora_inicio) + duracion_default).time()
		
		return hora_fin


	def _crear_sesion(
		self,
		asignatura: str,
		aula: str,
		dia: str,
		hora_inicio: dt_time,
		hora_fin: dt_time,
		tipo: Optional[str],
		grupo: Optional[str]
	) -> Sesion:
		"""
		Crea un objeto Sesion con validaciones.
		
		Args:
			asignatura: Nombre de la asignatura
			aula: Aula donde se imparte
			dia: Día de la semana
			hora_inicio: Hora de inicio
			hora_fin: Hora de finalización
			tipo: Tipo de sesión (TEORÍA/PRÁCTICA/PRÁCTICA_AULA)
			grupo: Grupo de prácticas (opcional)
			
		Returns:
			Objeto Sesion construido
			
		Raises:
			ValueError: Si los datos son inválidos
		"""
		# Validaciones básicas
		if not asignatura:
			raise ValueError("Asignatura es obligatoria")
		
		if not aula:
			raise ValueError("Aula es obligatoria")
		
		if not dia:
			raise ValueError("Día es obligatorio")
		
		if hora_inicio >= hora_fin:
			raise ValueError(
				f"Hora inicio ({hora_inicio}) debe ser anterior a hora fin ({hora_fin})"
			)
		
		# Validar duración
		duracion_minutos = (
			hora_fin.hour * 60 + hora_fin.minute -
			hora_inicio.hour * 60 - hora_inicio.minute
		)
		
		if duracion_minutos < DURACION_MINIMA_SESION:
			self.warnings.append(Warning(
				message=f"Sesión con duración menor a {DURACION_MINIMA_SESION} min: {duracion_minutos} min",
				context={
					'asignatura': asignatura,
					'dia': dia,
					'hora_inicio': str(hora_inicio),
					'hora_fin': str(hora_fin)
				}
			))
		
		if duracion_minutos > DURACION_MAXIMA_SESION:
			self.warnings.append(Warning(
				message=f"Sesión con duración mayor a {DURACION_MAXIMA_SESION} min: {duracion_minutos} min",
				context={
					'asignatura': asignatura,
					'dia': dia,
					'hora_inicio': str(hora_inicio),
					'hora_fin': str(hora_fin)
				}
			))
		
		# Crear sesión
		return Sesion(
			asignatura=asignatura,
			aula=aula,
			dia=dia,
			hora_inicio=hora_inicio,
			hora_fin=hora_fin,
			tipo=tipo,
			grupo=grupo
		)