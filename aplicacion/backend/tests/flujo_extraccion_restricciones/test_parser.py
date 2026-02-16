import sys
import os

# Asegurar que el path incluya la raíz del backend para las importaciones
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.extraccion.restricciones.extractor import get_restricciones_extractor
from core.extraccion.restricciones.parser import get_restricciones_parser

def test_full_extraction_and_parsing():
    # 1. Inicializar componentes
    extractor = get_restricciones_extractor()
    parser = get_restricciones_parser()
    
    excel_path = "docs\\Ejemplo restricciones.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Error: No se encuentra el archivo {excel_path}")
        return

    print(f"--- INICIANDO TEST DE FLUJO: {excel_path} ---\n")

    # 2. Paso 1: Extracción
    result_ext = extractor.extract_from_excel(excel_path)
    if not result_ext.success:
        print(f"FALLO EN EXTRACCIÓN: {result_ext.error_message}")
        return
    
    print(f"[EXTRACTOR] Filas crudas leídas: {len(result_ext.filas_crudas)}")

    # 3. Paso 2: Parsing (con la salida del extractor)
    parsed_rows, metadata = parser.parse_rows(result_ext)

    # 4. Mostrar resultados del Parsing
    print(f"[PARSER] Registros generados tras expansión: {len(parsed_rows)}")
    print(f"[PARSER] Duración: {metadata.parse_duration:.4f}s")
    
    if metadata.errors:
        print("\n--- ERRORES ENCONTRADOS ---")
        for err in metadata.errors:
            print(f" X {err}")

    if metadata.warnings:
        print("\n--- WARNINGS ENCONTRADOS ---")
        for warn in metadata.warnings:
            print(f" ! {warn.message}")

    print("\n--- REGISTROS PARSEADOS (VISTA DETALLADA) ---")
    print(f"{'FILA':<5} | {'PROFESOR':<20} | {'DÍA':<5} | {'INICIO':<8} | {'FIN':<8}")
    print("-" * 60)
    
    for p in parsed_rows:
        print(f"{p.fila_origen:<5} | {p.profesor[:20]:<20} | {p.dia:<5} | {p.hora_inicio_str:<8} | {p.hora_fin_str:<8}")

if __name__ == "__main__":
    test_full_extraction_and_parsing()