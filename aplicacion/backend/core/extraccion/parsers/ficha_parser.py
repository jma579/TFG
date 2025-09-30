from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from core.extraccion.entities.extractor import ExtractionMetadata
from core.extraccion.entities.common import ParserError
from core.extraccion.parsers.base_parser import BaseParser

from core.extraccion.constants.fichas import (
    DEFAULT_FICHA_CONFIG, PATTERN_CODIGO_NOMBRE, PATTERN_ECTS, PATTERN_PERIODO,
    PATTERN_MODALIDAD, PATTERN_IDIOMA, PATTERN_ENGLISH_FRIENDLY, PATTERN_PROFESORADO,
    MAP_MODALIDAD, MAP_PERIODO, MAP_IDIOMA
)
from core.extraccion.entities.fichas import SubjectSheet, Teacher

class FichaParser(BaseParser[SubjectSheet]):
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
        cfg = DEFAULT_FICHA_CONFIG.copy()
        if config:
            cfg.update(config)
        super().__init__(cfg)
        self.name = self.__class__.__name__ # TODO: Si ya se asigna en la clase padre revisar


    def parse_text(self, text: str, metadata: Optional[ExtractionMetadata] = None) -> SubjectSheet:
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
        # Preprocesamiento del texto
        t = self.preprocess_text(text)

        # Extracción de campos principales usando los extractores
        codigo, nombre = self._extract_codigo_nombre(t)
        ects = self._extract_ects(t)
        periodo = self._extract_periodo(t)
        modalidad = self._extract_modalidad(t)
        idioma, english_friendly = self._extract_idioma_ef(t)
        profesores = self._extract_profesorado(t)

        # Construcción del objeto SubjectSheet
        ficha = SubjectSheet(
            codigo_plan=codigo,
            nombre=nombre,
            periodo=periodo,
            ects=ects,
            modalidad=modalidad,
            idioma=idioma,
            english_friendly=english_friendly,
            profesores=profesores,
            raw_text=t,
            metadata=metadata,
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
        m = re.search(PATTERN_CODIGO_NOMBRE, text, flags=re.IGNORECASE)
        if not m:
            raise ParserError("No se pudo extraer el código y nombre de la asignatura.")
        codigo = m.group(1).strip().upper()
        nombre = re.sub(r"\s{2,}", " ", m.group(2).strip())
        # Capitalización conservadora del nombre (opcional):
        if nombre:
            nombre = nombre[0].upper() + nombre[1:]
        return codigo, nombre

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
        m = re.search(PATTERN_ECTS, text, flags=re.IGNORECASE)
        if not m:
            raise ParserError("No se pudo extraer el número de créditos ECTS.")
        ects_str = m.group(1).replace(",", ".").strip()
        try:
            ects_int = int(float(ects_str))
        except ValueError:
            raise ParserError(f"Formato de créditos ECTS no válido: {ects_str}")
        # Normaliza a entero (si usas enums/validador que exijan int)
        return ects_int

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
        profesores: List[Teacher] = []
        mblock = re.search(PATTERN_PROFESORADO, text, flags=re.IGNORECASE | re.DOTALL)
        if not mblock:
            return profesores

        block = mblock.group(1)

        # Nuevo patrón: tipo + apellidos + nombre
        line_rx = re.compile(
            r"^\s*([A-Z]{2})\s+([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ\s\-'’]+?),\s*([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ\s\-'’]+)\s*$"
        )
        for raw in block.splitlines():
            line = raw.strip()
            if not line:
                continue
            m = line_rx.match(line)
            if m:
                apellidos = m.group(2).title().replace(" De ", " de ").replace(" Del ", " del ")
                nombre = m.group(3).title()
                profesores.append(Teacher(nombre=nombre, apellidos=apellidos))
        return profesores
    
    
    # Validación y normalización
    def preprocess_text(self, text: str) -> str:
        """
        Preprocesa el texto plano antes de la extracción (normaliza espacios, saltos de línea, etc.).
        Args:
            text: Texto original extraído.
        Returns:
            Texto preprocesado listo para parsing.
        """
        return super().preprocess(text)

    def validate(self, parsed: SubjectSheet) -> Tuple[bool, List[str]]:
        """
        Valida que el objeto SubjectSheet cumple los requisitos mínimos de integridad y formato.
        Args:
            parsed: Objeto SubjectSheet a validar.
        Returns:
            Tupla (bool, lista de errores). True si es válido, False si hay errores.
        """
        errores: List[str] = []
        if not parsed.codigo_plan or not re.match(r"^[A-Z]{1,2}\d{1,4}$", parsed.codigo_plan):
            errores.append("Código de plan inválido o ausente.")
        if not parsed.nombre or len(parsed.nombre) < 3:
            errores.append("Nombre de asignatura inválido o ausente.")
        if not isinstance(parsed.ects, int) or parsed.ects <= 0:
            errores.append("ECTS debe ser un entero positivo.")
        # Opcional: valida enums si los usas como strings
        if not parsed.periodo or not isinstance(parsed.periodo, str):
            errores.append("Periodo ausente o inválido.")
        if not parsed.modalidad or not isinstance(parsed.modalidad, str):
            errores.append("Modalidad ausente o inválida.")
        if not parsed.idioma or not isinstance(parsed.idioma, str):
            errores.append("Idioma ausente o inválido.")
        return (len(errores) == 0), errores

    def to_normalized(self, parsed: SubjectSheet) -> Dict[str, Any]:
        """
        Convierte el objeto SubjectSheet a un dict alineado con los modelos de BD.
        Args:
            parsed: Objeto SubjectSheet a normalizar.
        Returns:
            Diccionario con la estructura esperada por la capa de persistencia o integración.
        """
        return {
            "subject": {
                "codigo_plan": parsed.codigo_plan,
                "nombre": parsed.nombre,
                "periodo": parsed.periodo,            # Map a Enum en capa de servicio si procede
                "ects": parsed.ects,
                "modalidad": parsed.modalidad,        # Idem
                "idioma": parsed.idioma,              # Idem
                "english_friendly": parsed.english_friendly,
            },
            "teaching_staff": [
                {
                    "nombre": t.nombre,
                    "apellidos": t.apellidos,
                }
                for t in (parsed.profesores or [])
            ],
            # Útil si quieres auditar
            "_meta": {
                "source": "ficha",
                "chars": len(parsed.raw_text or ""),
            },
        }
