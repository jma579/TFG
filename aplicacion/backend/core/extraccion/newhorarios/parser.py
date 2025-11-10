from typing import Any, Dict, Optional, List, Tuple
import logging
import time
from datetime import datetime
import re
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


from core.extraccion.newhorarios.entities import (
    ParsingResult, HorarioExtractionResult, Horario, Sesion,
    TablaHorario
)
from core.extraccion.newhorarios.constants import (
    DEFAULT_PARSER_CONFIG,
    PATRON_TITULO, PERIODO_MAP,
    PROMPT_HEADER_CONTEXT, PROMPT_LABEL_CURSO, PROMPT_LABEL_MENCION, PROMPT_LABEL_PAGINA,
    PROMPT_HEADER_KEYS, PROMPT_LABEL_DAYS, PROMPT_LABEL_TIMES,
    PROMPT_HEADER_CANDIDATES, PROMPT_DIVIDER_CANDIDATE, PROMPT_LABEL_DAY,
    PROMPT_LABEL_START_TIME, PROMPT_LABEL_RAW_CONTENT,
    PROMPT_TASK_HEADER, PROMPT_TASK_BODY, PROMPT_RULES_HEADER,
    PROMPT_RULE_DURATION, PROMPT_RULE_TYPE_MAPPING_HEADER, PROMPT_RULE_EXTRACTION,
    PROMPT_OUTPUT_HEADER, EXAMPLE_JSON_OUTPUT,
    TIPOS_SESION, DIAS_MAP
)
from core.extraccion.common.entities import (
    ParsingMetadata, Warning
)

class HorarioParser:
    """
    Parser especializado para horarios académicos.
    
    Esta clase procesa los datos extraídos por el HorarioExtractor y genera
    una estructura normalizada de sesiones y horarios. Utiliza Gemini para
    el análisis avanzado del contenido de las celdas.
    
    Flujo principal:
    1. Procesamiento de tablas extraídas
    2. Análisis de contenido de celdas con Gemini
    3. Construcción de sesiones y horarios
    4. Validación y normalización de datos
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Inicializa el parser con configuración opcional.
        
        Args:
            config: Configuración personalizada para el parser
        """
        self.logger = logging.getLogger(__name__)
        self.config = DEFAULT_PARSER_CONFIG.copy()
        if config:
            self.config.update(config)
        self.name = self.__class__.__name__

    
    def parse(self, input_data: HorarioExtractionResult) -> ParsingResult:
        """
        Punto de entrada principal del parser. Procesa los resultados de extracción
        y genera una estructura normalizada de horarios.
        
        Args:
            input_data: Resultado de la extracción con tablas y metadata
                
        Returns:
            ParsingResult: Resultado del parsing con horarios procesados y metadata
                
        Raises:
            ParserError: Si hay errores críticos en el parsing
        """
        start_time = time.time()
        self.warnings: List[Warning] = []
        self.errors: List[str] = []

        # Extraer informacion global
        try: 
            titulacion, periodo = self._process_title(input_data.titulo)
            if not titulacion:
                self.errors.append("No se pudo extraer la titulación del título.")
            if not periodo:
                self.errors.append("No se pudo extraer el periodo del título.")
        except Exception as e:
            self.logger.error(f"Error al extraer la titulacion/cuatrimestre: {e}")
            self.errors.append(f"Error al extraer la titulacion/cuatrimestre: {e}")

        # Iniciar el cliente de Gemini para parsing avanzado
        self._init_gemini_client()

        # Procesar cada tabla para construir la lista de sesiones
        horarios: List[Horario] = []
        for i, tabla in enumerate(input_data.tablas):
            try:
                horario = self._process_table(tabla, periodo)
                if horario:
                    horarios.append(horario)
                else:
                    self.warnings.append(Warning(
                        message=f"La tabla {i+1} no generó ningún horario válido",
                        severity="severe"
                    ))
            except Exception as e:
                self.logger.error(f"Error al procesar la tabla {i+1}: {e}")
                self.errors.append(f"Error al procesar la tabla {i+1}: {e}")
        if not horarios:
            self.errors.append("No se pudo procesar ningún horario válido del documento")

        # Construir metadata de parsing
        parsing_metadata = ParsingMetadata(
            parser_name=self.name,
            parser_version=self.config.get('version', 'unknown'),
            parse_timestamp=datetime.now(),
            parse_duration=time.time() - start_time,
            warnings=self.warnings,
            errors=self.errors
        )

        # Construir resultado final
        return ParsingResult(
            titulo=input_data.titulo,
            horarios=horarios,
            extraction_metadata=input_data.metadata,
            parsing_metadata=parsing_metadata,
            raw_json={
                "titulo": input_data.titulo,
                "tablas": [tabla.__dict__ for tabla in input_data.tablas],
                "metadata": input_data.metadata.to_dict()
            }
        )
    

    def _process_title(self, titulo: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Procesa el título del documento para extraer titulación y periodo.
        
        Args:
            titulo: Título del documento de horarios
                
        Returns:
            Tuple[Optional[str], Optional[str]]: (titulacion, periodo)
                - titulacion: Nombre normalizado de la titulación
                - periodo: PRIMER_CUATRIMESTRE o SEGUNDO_CUATRIMESTRE
                    
        Examples:
            >>> _process_title("GRADO EN FÍSICA PRIMER CUATRIMESTRE")
            ("FÍSICA", "PRIMER_CUATRIMESTRE")
            >>> _process_title("DOBLE GRADO EN FÍSICA Y MATEMÁTICAS SEGUNDO CUATRIMESTRE")
            ("FÍSICA Y MATEMÁTICAS", "SEGUNDO_CUATRIMESTRE")
        """
        if not titulo:
            return None, None
                
        # Normalizar el título
        titulo = titulo.upper().strip()
        
        # Probar cada patrón en orden
        for tipo_grado, patron in PATRON_TITULO.items():
            match = re.search(patron, titulo, re.IGNORECASE)
            if match:
                # Extraer y normalizar titulación
                titulacion = match.group("titulacion").strip()
                # Extraer y mapear periodo si existe
                periodo_raw = match.group("periodo")
                periodo = PERIODO_MAP.get(periodo_raw) if periodo_raw else None
                
                self.logger.debug(
                    f"Título procesado ({tipo_grado}): {titulo} -> "
                    f"Titulación: {titulacion}, Periodo: {periodo}"
                )
                return titulacion, periodo
        
        # Si no hay coincidencia exacta, intentar extracción más flexible
        try:
            # Detectar si es doble grado o grado simple
            if "DOBLE GRADO EN" in titulo:
                titulacion = titulo.split("DOBLE GRADO EN")[1].strip()
            elif "GRADO EN" in titulo:
                titulacion = titulo.split("GRADO EN")[1].strip()
            else:
                self.logger.error(f"No se reconoce el tipo de grado en el título: {titulo}")
                self.errors.append(f"No se reconoce el tipo de grado en el título: {titulo}")
                return None, None

            # Intentar extraer el periodo del resto del título
            titulacion_parts = titulacion.split()
            if "CUATRIMESTRE" in titulacion_parts:
                idx = titulacion_parts.index("CUATRIMESTRE")
                if idx > 0 and titulacion_parts[idx-1] in ["PRIMER", "SEGUNDO"]:
                    periodo = PERIODO_MAP.get(titulacion_parts[idx-1])
                    titulacion = " ".join(titulacion_parts[:idx-1]).strip()
                else:
                    periodo = None
            else:
                periodo = None
                
            if not periodo:
                self.warnings.append(Warning(
                    message="No se pudo extraer el periodo del título, se asume None",
                    severity="moderate"
                ))
                
            self.logger.debug(
                f"Título procesado (fallback): {titulo} -> "
                f"Titulación: {titulacion}, Periodo: {periodo}"
            )
            return titulacion, periodo
                
        except Exception as e:
            self.logger.error(f"Error procesando título '{titulo}': {str(e)}")
            self.errors.append(f"Error procesando título '{titulo}': {str(e)}")
            return None, None
        
    def _init_gemini_client(self) -> None:
        """
        Inicializa el cliente de Gemini para el parsing avanzado.
        
        Raises:
            ImportError: Si el módulo google.generativeai no está instalado
            ValueError: Si no se proporciona la API key en la configuración
            RuntimeError: Si hay errores en la configuración del cliente
        """
        try:            
            # 1. Obtener la clave de la variable de entorno
            api_key = os.getenv(self.config['gemini_api_key_env'])
            if not api_key:
                self.logger.critical(f"La clave de API '{self.config['gemini_api_key_env']}' no está configurada en el entorno.")
                raise ValueError(f"Falta la clave de API: {self.config['gemini_api_key_env']}")
            
            # 2. Configurar el cliente de la API
            genai.configure(api_key=api_key)
            
            # 3. Crear modelo con configuración personalizada
            self.gemini_client = genai.GenerativeModel(
                model_name=self.config['gemini_model'],
                generation_config=genai.types.GenerationConfig(
                    temperature=self.config['gemini_temperature']
                )
            )
            
            self.logger.info(
                f"Cliente Gemini {self.config['gemini_model']} inicializado "
                f"(temperature={self.config['gemini_temperature']})"
            )
                
        except ImportError:
            self.logger.error("No se pudo importar google.generativeai. Instale con: pip install google-generativeai")
            raise
        except Exception as e:
            self.logger.critical(f"Error al inicializar el cliente Gemini: {e}")
            raise RuntimeError(f"Error de configuración de Gemini: {e}")

    def _process_table(self, tabla: TablaHorario, periodo: str) -> Optional[Horario]:
        # 1. Preparar la entrada estructurada para Gemini (Consolidación)
        gemini_input_text = self._consolidate_single_table(tabla) 
        
        # 2. Obtener el JSON de Sesiones de Gemini
        json_output_str = self._parse_table_with_gemini(
            tabla=tabla, 
            consolidated_text=gemini_input_text
        )
        
        if not json_output_str:
            self.errors.append(f"Error al procesar la tabla del curso {tabla.curso} (Pág {tabla.pagina})")
            return None
            
        # 3. Normalizar el JSON a la dataclass Horario/Sesion
        horario_obj = self._normalize_parsed_horario(
            json_output_str=json_output_str, 
            tabla=tabla, 
            periodo=periodo
        )
        
        return horario_obj
    
    # FUNCIONES AUXILIARES DE  _process_table
    def _consolidate_single_table(self, tabla: TablaHorario) -> str:
        """
        Traduce un objeto TablaHorario a una cadena de texto estructurada
        (prompt-friendly) para que Gemini la pueda interpretar.

        Inyecta el contexto explícito (Día, Hora_Inicio) a cada celda
        no vacía, filtrando las celdas vacías.
        
        Args:
            tabla: El objeto TablaHorario a procesar.
            
        Returns:
            Una única cadena de texto lista para ser usada en el prompt de Gemini.
        """
        # Usar una lista de strings y .join() es más eficiente
        prompt_parts = []

        # --- Parte 1: Contexto Global de la Tabla ---
        prompt_parts.append(f"{PROMPT_HEADER_CONTEXT}\n")
        prompt_parts.append(f"{PROMPT_LABEL_CURSO} {tabla.curso}\n")
        if tabla.mencion:
            prompt_parts.append(f"{PROMPT_LABEL_MENCION} {tabla.mencion}\n")
        prompt_parts.append(f"{PROMPT_LABEL_PAGINA} {tabla.pagina}\n\n")

        # --- Parte 2: Clave de Coordenadas (El "Mapa") ---
        # Esto es crucial para que Gemini infiera la hora_fin (duración)
        prompt_parts.append(f"{PROMPT_HEADER_KEYS}\n")
        prompt_parts.append(f"{PROMPT_LABEL_DAYS} {tabla.day_columns}\n")
        prompt_parts.append(f"{PROMPT_LABEL_TIMES} {tabla.time_rows}\n\n")

        # --- Parte 3: Cuerpo Principal (Las "Sesiones Candidatas") ---
        prompt_parts.append(f"{PROMPT_HEADER_CANDIDATES}\n")

        candidate_count = 0
        # Bucle anidado para iterar sobre la matriz de celdas
        for row_index, time_start in enumerate(tabla.time_rows):
            # Asegurarse de que el índice de fila esté dentro de los límites de las celdas
            if row_index >= len(tabla.celdas):
                self.logger.warning(f"Discrepancia de tamaño en celdas: fila {row_index} fuera de límites.")
                self.warnings.append(Warning(
                    message=f"Discrepancia de tamaño en celdas: fila {row_index} fuera de límites.",
                    severity="moderate"
                ))
                continue

            for col_index, day in enumerate(tabla.day_columns):
                # Asegurarse de que el índice de columna esté dentro de los límites
                if col_index >= len(tabla.celdas[row_index]):
                    self.logger.warning(f"Discrepancia de tamaño en celdas: col {col_index} (Día {day}) fuera de límites.")
                    self.warnings.append(Warning(
                        message=f"Discrepancia de tamaño en celdas: col {col_index} (Día {day}) fuera de límites.",
                        severity="moderate"
                    ))
                    continue
                
                # Acceder al contenido de la celda
                raw_content = tabla.celdas[row_index][col_index]

                # El filtro clave: Solo procesar celdas con contenido real
                # (Ignoramos celdas 'None' o vacías)
                if raw_content and raw_content.strip():
                    candidate_count += 1
                    prompt_parts.append(f"\n{PROMPT_DIVIDER_CANDIDATE}\n")
                    prompt_parts.append(f"{PROMPT_LABEL_DAY} {day}\n")
                    prompt_parts.append(f"{PROMPT_LABEL_START_TIME} {time_start}\n")
                    prompt_parts.append(f"{PROMPT_LABEL_RAW_CONTENT}\n{raw_content}\n")

        if candidate_count == 0:
            self.logger.warning(f"La tabla de {tabla.curso} (Pág {tabla.pagina}) no contenía celdas con contenido para procesar.")
            self.warnings.append(Warning(
                message=f"La tabla de {tabla.curso} (Pág {tabla.pagina}) no contenía celdas con contenido para procesar.",
                severity="severe"
            ))
            # Adjuntamos una nota para que Gemini sepa que la tabla estaba vacía
            prompt_parts.append("\n(No se encontraron sesiones candidatas en esta tabla.)\n")

        # Unir todas las partes en una sola cadena de texto
        return "".join(prompt_parts)

    def _parse_table_with_gemini(self, tabla: TablaHorario, consolidated_text: str) -> Optional[str]:
        """
        Toma el texto consolidado de UNA tabla, construye el prompt y llama a 
        la API de Gemini para obtener una lista JSON de sesiones.

        Args:
            tabla: El objeto TablaHorario (para logging y contexto).
            consolidated_text: El texto pre-procesado por _consolidate_single_table.

        Returns:
            Optional[str]: El JSON de la lista de sesiones si la operación fue exitosa,
                        None si hubo algún error.
        """
        try:
            # Construir el prompt
            prompt = self._build_gemini_prompt(consolidated_text)
            
            self.logger.info(f"Llamando a Gemini API para {tabla.curso} (Pág {tabla.pagina})...")
            response = self.gemini_client.generate_content(prompt)
            
            # Verificar respuesta válida
            if not response or not response.text:
                self.logger.error("Respuesta vacía de Gemini API")
                return None
                
            json_output_str = response.text
            
            # Validación de JSON y schema
            try:
                parsed_json = json.loads(json_output_str)
                if not isinstance(parsed_json, list):
                    self.logger.error("La respuesta no es una lista JSON")
                    self.errors.append("La respuesta de Gemini no es una lista JSON como se esperaba")
                    return None
                    
                # Validar schema básico de cada sesión
                required_fields = {"asignatura", "tipo", "dia", "hora_inicio", "hora_fin"}
                for sesion in parsed_json:
                    missing_fields = required_fields - set(sesion.keys())
                    if missing_fields:
                        self.logger.error(f"Campos requeridos faltantes: {missing_fields}")
                        self.errors.append(f"Campos requeridos faltantes en la respuesta de Gemini: {missing_fields}")
                        return None
                        
            except json.JSONDecodeError as json_err:
                self.logger.error(f"Error decodificando JSON: {str(json_err)}")
                self.errors.append(f"Error decodificando JSON: {str(json_err)}")
                return None
            except ValueError as val_err:
                self.logger.error(f"Error de validación: {str(val_err)}")
                self.errors.append(f"Error de validación: {str(val_err)}")
                return None

            self.logger.info(f"Respuesta JSON válida recibida de Gemini")
            return json_output_str

        except Exception as e:
            self.logger.error(f"Error crítico al llamar a Gemini API para {tabla.curso}: {e}")
            self.errors.append(f"Error crítico al llamar a Gemini API para {tabla.curso}: {e}")
            return None
        
    def _normalize_parsed_horario(self, json_output_str: str, tabla: TablaHorario, periodo: str) -> Optional[Horario]:
        """
        Normaliza y valida el JSON de sesiones devuelto por Gemini.
        
        Args:
            json_output_str: String JSON con la lista de sesiones
            tabla: Tabla original para metadata
            periodo: Periodo académico normalizado
            
        Returns:
            Optional[Horario]: Horario procesado o None si hay errores críticos
        """
        try:
            # 1. Parse JSON
            sesiones_raw = json.loads(json_output_str)
            if not isinstance(sesiones_raw, list):
                raise ValueError("El JSON debe contener una lista de sesiones")
                
            # 2. Procesar cada sesión
            sesiones_normalizadas = []
            for idx, sesion_data in enumerate(sesiones_raw, 1):
                try:
                    # 2.1 Validar campos requeridos
                    required = {"asignatura", "tipo", "dia", "hora_inicio", "hora_fin"}
                    if missing := (required - set(sesion_data.keys())):
                        raise ValueError(f"Campos requeridos faltantes: {missing}")
                        
                    # 2.2 Normalizar tipo de sesión
                    tipo_raw = sesion_data["tipo"].upper()
                    tipo = TIPOS_SESION.get(tipo_raw)
                    if not tipo or tipo not in self.config['tipos_validos']:
                        self.warnings.append(Warning(
                            message=f"Tipo de sesión no reconocido o inválido: {tipo_raw}",
                            severity="moderate"
                        ))
                        tipo = self.config['tipo_default']
                        
                    # 2.3 Normalizar día
                    dia_raw = sesion_data["dia"].upper()
                    dia = DIAS_MAP.get(dia_raw)
                    if not dia:
                        raise ValueError(f"Día no válido: {dia_raw}")
                        
                    # 2.4 Convertir y validar horas
                    try:
                        hora_inicio = datetime.strptime(sesion_data["hora_inicio"], "%H:%M").time()
                        hora_fin = datetime.strptime(sesion_data["hora_fin"], "%H:%M").time()
                        
                        hora_min = datetime.strptime(self.config['hora_min'], "%H:%M").time()
                        hora_max = datetime.strptime(self.config['hora_max'], "%H:%M").time()
                        
                        if not (hora_min <= hora_inicio <= hora_max):
                            raise ValueError(f"Hora inicio {hora_inicio} fuera de rango válido")
                        if not (hora_min <= hora_fin <= hora_max):
                            raise ValueError(f"Hora fin {hora_fin} fuera de rango válido")
                            
                    except ValueError as e:
                        raise ValueError(f"Formato de hora inválido: {str(e)}")
                        
                    # 2.5 Validar orden y duración temporal
                    if hora_inicio >= hora_fin:
                        raise ValueError(f"Hora inicio ({hora_inicio}) >= hora fin ({hora_fin})")
                        
                    duracion = (
                        datetime.combine(datetime.min, hora_fin) - 
                        datetime.combine(datetime.min, hora_inicio)
                    ).seconds / 60
                    
                    if not (self.config['duracion_min_minutos'] <= duracion <= self.config['duracion_max_minutos']):
                        raise ValueError(
                            f"Duración de sesión ({duracion} min) fuera de rango "
                            f"[{self.config['duracion_min_minutos']}, "
                            f"{self.config['duracion_max_minutos']}]"
                        )
                        
                    # 2.6 Crear objeto Sesion
                    sesion = Sesion(
                        asignatura=sesion_data["asignatura"].strip(),
                        tipo=tipo,
                        dia=dia,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        aula=sesion_data.get("aula", "").strip() or None,
                        grupo=sesion_data.get("grupo", "").strip() or None
                    )
                    sesiones_normalizadas.append(sesion)
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando sesión {idx}: {str(e)}")
                    self.warnings.append(Warning(
                        message=f"Error procesando sesión {idx}: {str(e)}",
                        severity="moderate"
                    ))
                    continue
                    
            # 3. Verificar que hay al menos una sesión válida
            if not sesiones_normalizadas:
                raise ValueError("No se pudo normalizar ninguna sesión")
                
            # 4. Construir y retornar el horario
            return Horario(
                curso=tabla.curso,
                mencion=tabla.mencion,
                periodo=periodo,
                pagina=tabla.pagina,
                sesiones=sesiones_normalizadas
            )
                
        except Exception as e:
            self.logger.error(f"Error normalizando horario: {str(e)}")
            self.errors.append(f"Error normalizando horario: {str(e)}")
            return None


    def _build_gemini_prompt(self, consolidated_text: str) -> str:
        """
        Construye el prompt final para Gemini.
        
        Args:
            consolidated_text: El texto consolidado de la tabla
            
        Returns:
            str: El prompt completo
            
        Raises:
            ValueError: Si el texto consolidado está vacío o mal formado
        """
        if not consolidated_text or not consolidated_text.strip():
            raise ValueError("El texto consolidado no puede estar vacío")
            
        # Verificar secciones requeridas
        required_sections = [PROMPT_HEADER_CONTEXT, PROMPT_HEADER_KEYS, PROMPT_HEADER_CANDIDATES]
        for section in required_sections:
            if section not in consolidated_text:
                raise ValueError(f"Falta la sección requerida: {section}")

        # Construir el prompt con las constantes definidas
        prompt_parts = [
            consolidated_text,
            f"\n{PROMPT_TASK_HEADER}\n{PROMPT_TASK_BODY}\n",
            f"\n{PROMPT_RULES_HEADER}\n",
            f"{PROMPT_RULE_DURATION}\n",
            f"{PROMPT_RULE_TYPE_MAPPING_HEADER}\n",
            f"{PROMPT_RULE_EXTRACTION}\n",
            f"\n{PROMPT_OUTPUT_HEADER}\n",
            "Tu respuesta debe ser una única lista JSON, sin texto introductorio.",
            "Ejemplo de formato de salida (debe ser una lista, no un objeto):",
            json.dumps(EXAMPLE_JSON_OUTPUT, indent=4, ensure_ascii=False)
        ]
        
        return "\n".join(prompt_parts)
    
