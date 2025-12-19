from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re
from datetime import datetime
import time

from core.extraccion.common.entities import ExtractionMetadata, ParserError, ParsingMetadata, Warning

from core.extraccion.fichas.constants import (
    BASE_PARSER_CONFIG, PATTERN_CODIGO_NOMBRE, PATTERN_TITULACION, PATTERN_ECTS, PATTERN_PERIODO,
    PATTERN_MODALIDAD, PATTERN_IDIOMA, PATTERN_ENGLISH_FRIENDLY, PATTERN_PROFESORADO,
    PATTERN_NUM_CUATRIMESTRE, PROFESOR_SUFIXES, MAP_MODALIDAD, MAP_PERIODO, MAP_IDIOMA
)
from core.extraccion.fichas.entities import SubjectSheet, Teacher, Titulacion

class FichaParser:  
    """
    Parser especializado para fichas académicas universitarias.
    
    Esta clase se encarga de extraer, validar y normalizar los datos relevantes de una ficha académica
    (asignatura) a partir de texto plano, alineando la salida con los modelos de base de datos definidos.
    
    Principales responsabilidades:
    - Preprocesar el texto fuente para facilitar la extracción.
    - Extraer campos clave como código, nombre, créditos ECTS, periodo, modalidad, idioma y profesorado.
    - Validar la integridad y formato de los datos extraídos.
    - Normalizar la salida para su integración en sistemas de persistencia o análisis.
    
    Uso típico:
        parser = FichaParser()
        ficha = parser.parse_text(texto_extraido)
        dict_normalizado = parser.to_normalized(ficha)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Inicializa el parser de fichas académicas con la configuración por defecto o personalizada.
        Args:
            config: Diccionario opcional con parámetros de configuración específicos.
        """
        cfg = BASE_PARSER_CONFIG.copy()
        if config:
            cfg.update(config)
        self.config = cfg
        self.name = self.__class__.__name__


    def parse_text(self, text: str, extraction_metadata: Optional[ExtractionMetadata] = None) -> SubjectSheet:
        """
        Punto de entrada principal del parser. Extrae y valida todos los campos relevantes de la ficha académica.
        Args:
            text: Texto plano extraído de la ficha.
            metadata: Metadatos opcionales de la extracción.
        Returns:
            Objeto SubjectSheet con los datos estructurados y validados.
        Raises:
            ParserError: Si la validación de la ficha falla.
        """
        # Valores iniciales del parsing
        start_time = time.time()
        warnings: List[Warning] = []
        errors: List[str] = []

        # Preprocesamiento del texto
        text = self.preprocess_text(text)

        # Extracción de campos principales usando los extractores
        try:
            codigo, nombre = self._extract_codigo_nombre(text)
            if not codigo:
                errors.append("No se pudo extraer el código de la asignatura.")
            if not nombre:
                errors.append("No se pudo extraer el nombre de la asignatura.")
        except Exception as e:
            codigo, nombre = "", ""
            errors.append(f"Error extrayendo código/nombre: {e}")
        try:
            titulaciones = self._extract_titulaciones(text)
            if not titulaciones:
                warnings.append(Warning(
                    message="No se encontraron titulaciones asociadas.",
                    severity="moderate"
                ))
        except Exception as e:
            titulaciones = []
            errors.append(f"Error extrayendo titulaciones: {e}")
        try:
            ects = self._extract_ects(text)
        except Exception as e:
            ects = 0
            errors.append(f"Error extrayendo ECTS: {e}")
        try:
            periodo = self._extract_periodo(text)
            if not periodo or periodo == "N.A.":
                warnings.append(Warning(
                    message="No se pudo extraer el periodo de impartición.",
                    severity="moderate"
                ))
        except Exception as e:
            periodo = "N.A."
            errors.append(f"Error extrayendo periodo: {e}")
        try:
            num_periodo = self._extract_num_periodo(text)
        except Exception as e:
            num_periodo = None
            errors.append(f"Error extrayendo número de periodo: {e}")
        try:
            modalidad = self._extract_modalidad(text)
            if not modalidad or modalidad == "N.A.":
                warnings.append(Warning(
                    message="No se pudo extraer la modalidad de impartición.",
                    severity="minor"
                ))
        except Exception as e:
            modalidad = "N.A."
            errors.append(f"Error extrayendo modalidad: {e}")
        try:
            idioma, english_friendly = self._extract_idioma_ef(text)
        except Exception as e:
            idioma, english_friendly = "N.A.", False
            errors.append(f"Error extrayendo idioma/english friendly: {e}")
        try:
            profesores = self._extract_profesorado(text)
            if not profesores:
                warnings.append(Warning(
                    message="No se extrajo ningún profesor.",
                    severity="moderate"
                ))
        except Exception as e:
            profesores = []
            errors.append(f"Error extrayendo profesorado: {e}")
        try:
            centro = self._extract_centro(text)
            if not centro:
                warnings.append(Warning(
                    message="No se pudo extraer el centro responsable.",
                    severity="minor"
                ))
        except Exception as e:
            centro = None
            errors.append(f"Error extrayendo centro: {e}")
        try:
            departamento = self._extract_departamento(text)
            if not departamento:
                warnings.append(Warning(
                    message="No se pudo extraer el departamento responsable.",
                    severity="minor"
                ))
        except Exception as e:
            departamento = None
            errors.append(f"Error extrayendo departamento: {e}")

        # Construcción de los metadatos de parsing
        parser_metadata = ParsingMetadata(
            parser_name=self.name,
            parser_version=self.config.get("version"),
            parse_timestamp=datetime.now(),
            parse_duration=time.time() - start_time,
            warnings=warnings,
            errors=errors,
        )

        # Construcción del objeto SubjectSheet
        ficha = SubjectSheet(
            codigo_plan=codigo,
            nombre=nombre,
            titulaciones=titulaciones,
            periodo=periodo,
            num_periodo=num_periodo,
            ects=ects,
            modalidad=modalidad,
            idioma=idioma,
            english_friendly=english_friendly,
            profesores=profesores,
            centro=centro,
            departamento=departamento,
            raw_text=text,
            parsing_metadata=parser_metadata,
            extraction_metadata=extraction_metadata,
        )

        # Validación de la ficha
        is_valid, errores = self.validate(ficha)
        if not is_valid:
            raise ParserError(f"Errores de validación: {errores}")

        # Retorno del objeto tipado
        return ficha


    # Extractores principales
    def _extract_codigo_nombre(self, text: str) -> Tuple[str, str]:
        """
        Extrae el código y el nombre de la asignatura usando el patrón definido.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Tuple con el código (str) y el nombre (str) normalizados.
        Raises:
            ParserError: Si no se encuentra el patrón esperado.
        """
        match = re.search(PATTERN_CODIGO_NOMBRE, text, re.IGNORECASE)
        if not match:
            raise ParserError("No se pudo extraer el código y nombre de la asignatura.")
        codigo = match.group(1).strip()
        nombre = match.group(2).strip()
        # Solo tomar la primera línea del nombre (evita capturar bloques enteros)
        nombre = nombre.split('\n')[0].strip()
        return codigo, nombre
    
    def _extract_titulaciones(self, text: str) -> List[Titulacion]:
        """
        Extrae las titulaciones, tipo de asignatura y curso.
        Ejemplo de línea: 'Grado en Física OBLIGATORIA 2'
        """
        titulaciones = []
        # Busca líneas tipo: Grado en Física OBLIGATORIA 2
        patron = re.compile(PATTERN_TITULACION, re.IGNORECASE)
        for match in patron.finditer(text):
            programa_nombre = match.group(1).strip()
            tipo = match.group(2).strip().capitalize()
            curso = match.group(3).strip()
            titulaciones.append(Titulacion(
                programa_nombre=programa_nombre,
                tipo_asignatura=tipo,
                curso=curso
            ))
        return titulaciones
    
    def _extract_ects(self, text: str) -> int:
        """
        Extrae el número de créditos ECTS de la asignatura.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Número de créditos ECTS como entero.
        Raises:
            ParserError: Si el formato es incorrecto o el campo está ausente.
        """
        match = re.search(PATTERN_ECTS, text, re.IGNORECASE)
        if not match:
            raise ParserError("No se pudo extraer el número de ECTS.")
        ects_str = match.group(1).replace(',', '.')
        try:
            ects = float(ects_str)
        except ValueError:
            raise ParserError(f"ECTS no numérico: {ects_str}")
        return int(ects)

    def _extract_periodo(self, text: str) -> str:
        """
        Extrae el periodo/cuatrimestre de impartición de la asignatura.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Periodo normalizado (str) o "N.A." si no se encuentra.
        """
        m = re.search(PATTERN_PERIODO, text, flags=re.IGNORECASE)
        if not m:
            return "N.A."
        periodo_raw = m.group(1).strip()
        return MAP_PERIODO.get(periodo_raw, periodo_raw.upper())
    
    def _extract_num_periodo(self, text: str) -> Optional[int]:
        """
        Extrae el número de periodo/cuatrimestre si está presente en el texto.
        Ejemplo: 'Nº: 1' -> 1
        """
        match = re.search(PATTERN_NUM_CUATRIMESTRE, text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_modalidad(self, text: str) -> str:
        """
        Extrae la modalidad de impartición de la asignatura.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Modalidad normalizada (str) o "N.A." si no se encuentra.
        """
        m = re.search(PATTERN_MODALIDAD, text, flags=re.IGNORECASE)
        if not m:
            return "N.A."
        modalidad_raw = m.group(1).strip()
        return MAP_MODALIDAD.get(modalidad_raw, modalidad_raw.upper())

    def _extract_idioma_ef(self, text: str) -> Tuple[str, bool]:
        """
        Extrae el idioma principal y si la asignatura es 'english friendly'.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Tupla (idioma normalizado, english_friendly: bool).
        """
        idioma = self.config.get("default_idioma", "ESPAÑOL")
        m = re.search(PATTERN_IDIOMA, text, flags=re.IGNORECASE)
        if m:
            idioma_raw = m.group(1).strip()
            idioma = MAP_IDIOMA.get(idioma_raw, idioma_raw.upper())

        ef = False
        mef = re.search(PATTERN_ENGLISH_FRIENDLY, text, flags=re.IGNORECASE)
        if mef:
            ef_value = mef.group(1).strip().lower()
            ef = ef_value in ("sí", "si", "yes", "true", "1")
        return idioma, ef

    def _extract_profesorado(self, text: str) -> List[Teacher]:
        """
        Extrae la lista de profesores y sus tipos desde el bloque de profesorado.
        Args:
            text: Texto plano de la ficha.
        Returns:
            Lista de objetos Teacher con nombre, apellidos y tipo.
        """
        profesores = []
        bloque = re.search(PATTERN_PROFESORADO, text, re.DOTALL | re.IGNORECASE)
        if not bloque:
            return []
        bloque_texto = bloque.group(1)
        patron_sufijos = re.compile('|'.join(PROFESOR_SUFIXES), re.IGNORECASE)
        
        for linea in bloque_texto.splitlines():
            linea = linea.strip()
            if not linea or "PROFESOR" in linea.upper() or "TIPO" in linea.upper():
                continue
                
            # 1. LIMPIEZA DEL PREFIJO SUCIO 
            linea_limpia = re.sub(r"^(?:[\w\.]{1,3}\s+)", "", linea, count=1).strip()
            
            # 2. LIMPIEZA DE SUFIJOS (Universidad, totales, etc.)
            linea_limpia = patron_sufijos.split(linea_limpia)[0]
            linea_limpia = re.sub(r"(?i)hospital\s+universitario.*", "", linea_limpia).strip()
            linea_limpia = re.sub(r"(?i)(?<=[a-z])hospital\s+universitario.*", "", linea_limpia).strip()
            
            # 3. ELIMINAR COLUMNAS NUMÉRICAS DE HORAS
            linea_limpia = re.split(r'\s+\d+([,.]\d+)?\s*', linea_limpia)[0]
            linea_limpia = linea_limpia.strip()
            
            # 4. EXTRACCIÓN FINAL (APELLIDOS, NOMBRE)
            match = re.match(r"^([A-ZÁÉÍÓÚÑÜ\s]+),\s*([A-ZÁÉÍÓÚÑÜ\s]+)$", linea_limpia, re.IGNORECASE)
            
            if match:
                apellidos = match.group(1).title().strip()
                nombre = match.group(2).title().strip()
                
                # Validación mínima de sanidad
                if len(apellidos) < 2 and not apellidos.isalpha():
                    continue
                    
                profesores.append(Teacher(nombre=nombre, apellidos=apellidos))
                
        return profesores

    def _extract_centro(self, text: str) -> Optional[str]:
        match = re.search(r'CENTRO RESPONSABLE\s*:\s*([^\n\r]+)', text, re.IGNORECASE)
        if match:
            centro = match.group(1).strip()
            # Elimina números iniciales y espacios
            centro = re.sub(r'^\d+\s*', '', centro)
            return centro
        return None

    def _extract_departamento(self, text: str) -> Optional[str]:
        match = re.search(r'DEPARTAMENTO RESPONSABLE\s*:\s*([^\n\r]+)', text, re.IGNORECASE)
        if match:
            departamento = match.group(1).strip()
            # Elimina números iniciales y espacios
            departamento = re.sub(r'^\d+\s*', '', departamento)
            return departamento
        return None
    
    
    # Validación y normalización
    def preprocess_text(self, text: str) -> str:
        """
        Preprocesa el texto plano antes de la extracción (normaliza espacios, saltos de línea, etc.).
        Args:
            text: Texto original extraído.
        Returns:
            Texto preprocesado listo para parsing.
        """
        # Elimina espacios dobles y normaliza saltos de línea
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\r\n?', '\n', text)
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()

    def validate(self, parsed: SubjectSheet) -> Tuple[bool, List[str]]:
        """
        Valida que el objeto SubjectSheet cumple los requisitos mínimos de integridad y formato.
        Args:
            parsed: Objeto SubjectSheet a validar.
        Returns:
            Tupla (bool, lista de errores). True si es válido, False si hay errores.
        """
        errores: List[str] = []
        if not re.match(r"^[A-Z]{1,2}\d{1,4}[A-Z]?$", parsed.codigo_plan):
            errores.append("Código de plan no válido: " + parsed.codigo_plan)
        if not parsed.nombre:
            errores.append("Nombre de asignatura vacío.")
        if parsed.ects <= 0:
            errores.append("ECTS no válido.")
        return (len(errores) == 0, errores)
