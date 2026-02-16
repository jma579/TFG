"""
Parser especializado para restricciones de profesorado.

Se encarga de limpiar el ruido de las cadenas y expandir las filas que 
contienen múltiples días en registros individuales.
"""

import re
import time
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from core.extraccion.common.entities import ParsingMetadata, Warning
from core.extraccion.restricciones.constants import PATTERN_FRANJA
from core.extraccion.restricciones.entities import (
    ParsedRestriccion, ExtractionResultRestricciones
)

class RestriccionesParser:
    """
    Parser que transforma filas crudas de Excel en datos parseados y expandidos.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("RestriccionesParser inicializado")

    def parse_rows(self, extraction_result: ExtractionResultRestricciones) -> Tuple[List[ParsedRestriccion], ParsingMetadata]:
        """
        Procesa las filas crudas, valida formatos y expande los días.
        
        Returns:
            Tuple con la lista de ParsedRestriccion y los metadatos del proceso.
        """
        start_time = time.time()
        parsed_list: List[ParsedRestriccion] = []
        warnings: List[Warning] = []
        errors: List[str] = []

        for raw_row in extraction_result.filas_crudas:
            if not raw_row.profesor or not raw_row.dias or not raw_row.franja:
                msg = f"Fila {raw_row.fila_excel}: Datos incompletos. Se omite la fila."
                self.logger.warning(msg)
                errors.append(msg)
                continue

            match_franja = re.match(PATTERN_FRANJA, raw_row.franja.strip())
            if not match_franja:
                msg = f"Fila {raw_row.fila_excel}: Formato de franja '{raw_row.franja}' inválido. Se espera 'HH:MM-HH:MM'."
                self.logger.error(msg)
                errors.append(msg)
                continue

            hora_inicio_str = match_franja.group(1)
            hora_fin_str = match_franja.group(2)

            # 3. Lógica de Expansión: Separar por días (ej: "L, M, X" -> 3 registros)
            lista_dias = [d.strip().upper() for d in raw_row.dias.split(",") if d.strip()]
            
            if not lista_dias:
                msg = f"Fila {raw_row.fila_excel}: No se detectaron días válidos en la celda."
                warnings.append(Warning(message=msg, severity="moderate"))
                continue

            for dia in lista_dias:
                parsed_list.append(ParsedRestriccion(
                    profesor=raw_row.profesor.strip(),
                    dia=dia,
                    hora_inicio_str=hora_inicio_str,
                    hora_fin_str=hora_fin_str,
                    fila_origen=raw_row.fila_excel
                ))

        metadata = ParsingMetadata(
            parser_name=self.__class__.__name__,
            parser_version="1.0.0",
            parse_timestamp=datetime.now(),
            parse_duration=time.time() - start_time,
            warnings=warnings,
            errors=errors
        )

        self.logger.info(f"Parsing completado. {len(parsed_list)} registros generados tras expansión.")
        return parsed_list, metadata


_parser_instance = None

def get_restricciones_parser() -> RestriccionesParser:
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = RestriccionesParser()
    return _parser_instance