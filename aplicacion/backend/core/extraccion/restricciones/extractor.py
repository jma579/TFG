"""
Módulo de extracción de Excel para Restricciones de Profesorado.
"""
import pandas as pd
import time
import logging
from typing import Any

from core.extraccion.common.entities import (
    ExtractionMetadata, ProcessingStatus, ErrorType, Warning, ExtractionQuality
)
from core.extraccion.restricciones.entities import (
    RawRestriccionRow, ExtractionResultRestricciones
)
from core.extraccion.restricciones.constants import REQUIRED_COLUMNS

class RestriccionesExtractor:
    """
    Extractor de datos en bruto desde archivos Excel (.xlsx) para restricciones.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("RestriccionesExtractor inicializado")

    def extract_from_excel(self, file_path_or_bytes: Any) -> ExtractionResultRestricciones:
        """
        Lee el Excel, valida las columnas y devuelve una lista de filas crudas.
        """
        start_time = time.time()
        self.logger.info("Iniciando extracción de restricciones desde Excel")
        
        try:
            df = pd.read_excel(file_path_or_bytes, engine='openpyxl')
            
            df.columns = df.columns.str.strip().str.title()
            
            df.rename(columns={'Días': 'Dias'}, inplace=True)
            
            df_cols = set(df.columns)
            req_cols = set(REQUIRED_COLUMNS)
            
            if not req_cols.issubset(df_cols):
                missing = req_cols - df_cols
                raise ValueError(f"Formato inválido. Faltan las siguientes columnas en el Excel: {', '.join(missing)}")
            
            df = df.dropna(how='all')
            
            filas_crudas = []
            warnings = []
            
            for index, row in df.iterrows():
                # Zero-index de pandas + 2 (por la cabecera y por ser 1-indexed en Excel)
                fila_excel = index + 2 
                
                profesor = str(row.get('Profesor', '')).strip()
                dias = str(row.get('Dias', '')).strip()
                franja = str(row.get('Franja', '')).strip()
                
                # Pandas convierte celdas vacías a string "nan" si usamos str(), lo corregimos
                if profesor.lower() == 'nan': profesor = ""
                if dias.lower() == 'nan': dias = ""
                if franja.lower() == 'nan': franja = ""

                if not profesor and not dias and not franja:
                    continue
                    
                if not profesor or not dias or not franja:
                    warnings.append(Warning(
                        message=f"Fila {fila_excel}: Contiene celdas en blanco. El parser intentará procesarlo.",
                        severity="minor"
                    ))

                filas_crudas.append(RawRestriccionRow(
                    fila_excel=fila_excel,
                    profesor=profesor,
                    dias=dias,
                    franja=franja
                ))

            metadata = ExtractionMetadata(
                quality=ExtractionQuality.EXCELLENT if not warnings else ExtractionQuality.ACCEPTABLE,
                confidence=1.0,
                status=ProcessingStatus.COMPLETED,
                processing_time_seconds=time.time() - start_time,
                page_count=1,
                file_size_mb=0.0, 
                has_embedded_text=True,
                char_count=0,
                word_count=0,
                errors=[],
                warnings=warnings
            )
            
            self.logger.info(f"Extracción completada. {len(filas_crudas)} filas válidas leídas.")
            
            return ExtractionResultRestricciones(
                filas_crudas=filas_crudas,
                metadata=metadata
            )

        except ValueError as ve:
            return self._handle_error(ve, ErrorType.INVALID_FORMAT, start_time)
        except Exception as e:
            return self._handle_error(e, ErrorType.UNKNOWN_ERROR, start_time)

    def _handle_error(self, error: Exception, error_type: ErrorType, start_time: float) -> ExtractionResultRestricciones:
        """Manejador centralizado de errores para generar metadatos de fallo."""
        self.logger.error(f"Error en extracción de Excel: {error}")
        metadata = ExtractionMetadata(
            quality=ExtractionQuality.UNUSABLE,
            confidence=0.0,
            status=ProcessingStatus.FAILED,
            processing_time_seconds=time.time() - start_time,
            page_count=0,
            file_size_mb=0.0,
            has_embedded_text=False,
            char_count=0,
            word_count=0,
            errors=[str(error)],
            warnings=[]
        )
        return ExtractionResultRestricciones(
            filas_crudas=[],
            metadata=metadata,
            error_type=error_type,
            error_message=str(error)
        )

# Factory para mantener una única instancia (Singleton pattern)
extractor_restricciones = None

def get_restricciones_extractor() -> RestriccionesExtractor:
    global extractor_restricciones
    if extractor_restricciones is None:
        extractor_restricciones = RestriccionesExtractor()
    return extractor_restricciones