"""
Normalización de datos extraídos de restricciones de profesorado.

Transforma los strings parseados en tipos de datos nativos de Python (time)
y miembros de Enums, listos para la persistencia en base de datos.
"""

import logging
from datetime import time
from typing import List, Optional

from core.extraccion.common.entities import ParsingMetadata, Warning
from core.extraccion.restricciones.constants import MAP_DIAS
from core.extraccion.restricciones.entities import (
    ParsedRestriccion, NormalizedRestriccionData
)
from constants.enums import DiaSemana

class RestriccionesNormalizer:
    """
    Normaliza datos de restricciones: mapea enums, convierte horas y limpia nombres.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("RestriccionesNormalizer inicializado")

    def normalize_rows(
        self, 
        parsed_rows: List[ParsedRestriccion], 
        metadata: ParsingMetadata
    ) -> List[NormalizedRestriccionData]:
        """
        Transforma la lista de registros parseados en datos normalizados.
        """
        normalized_list: List[NormalizedRestriccionData] = []

        for row in parsed_rows:
            try:
                nombre_normalizado = self._normalize_name(row.profesor)

                dia_enum = self._map_dia_to_enum(row.dia)
                if not dia_enum:
                    metadata.errors.append(
                        f"Fila {row.fila_origen}: El día '{row.dia}' no es válido."
                    )
                    continue

                h_inicio = self._parse_time(row.hora_inicio_str)
                h_fin = self._parse_time(row.hora_fin_str)

                if h_inicio >= h_fin:
                    metadata.errors.append(
                        f"Fila {row.fila_origen}: La hora de inicio ({h_inicio}) "
                        f"debe ser anterior a la de fin ({h_fin})."
                    )
                    continue

                normalized_list.append(NormalizedRestriccionData(
                    profesor_nombre_completo=nombre_normalizado,
                    dia_semana=dia_enum,
                    hora_inicio=h_inicio,
                    hora_fin=h_fin,
                    fila_origen=row.fila_origen
                ))

            except Exception as e:
                self.logger.error(f"Error normalizando fila {row.fila_origen}: {e}")
                metadata.errors.append(f"Fila {row.fila_origen}: Error inesperado: {str(e)}")

        self.logger.info(f"Normalización completada. {len(normalized_list)} registros listos.")
        return normalized_list

    def _normalize_name(self, name: str) -> str:
        """Limpia espacios y aplica formato de nombre propio."""
        return " ".join(name.split()).title()

    def _map_dia_to_enum(self, dia_str: str) -> Optional[DiaSemana]:
        """Mapea el string del día al Enum DiaSemana usando la constante MAP_DIAS."""
        dia_clean = dia_str.strip().upper()
        # Buscar en el mapa de constantes
        dia_key = MAP_DIAS.get(dia_clean)
        
        if dia_key:
            try:
                return DiaSemana(dia_key.lower())
            except ValueError:
                return None
        return None

    def _parse_time(self, time_str: str) -> time:
        """Convierte string 'HH:MM' a objeto datetime.time."""
        parts = time_str.split(':')
        return time(hour=int(parts[0]), minute=int(parts[1]))

# Factory para Singleton
_normalizer_instance = None

def get_restricciones_normalizer() -> RestriccionesNormalizer:
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = RestriccionesNormalizer()
    return _normalizer_instance