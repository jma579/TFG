import sys
import os

# Asegurar que el path incluya la raíz del backend para las importaciones
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.extraccion.restricciones.extractor import get_restricciones_extractor
from core.extraccion.restricciones.parser import get_restricciones_parser
from core.extraccion.restricciones.normalize import get_restricciones_normalizer

def test_full_pipeline_fase2():
    # 1. Inicializar los tres componentes
    extractor = get_restricciones_extractor()
    parser = get_restricciones_parser()
    normalizer = get_restricciones_normalizer()
    
    excel_path = "restricciones_test.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Error: No se encuentra el archivo {excel_path}")
        # Intentamos buscarlo en la ruta relativa si se ejecuta desde la raíz
        excel_path = "docs\\Ejemplo restricciones.xlsx" 
        if not os.path.exists(excel_path):
             return

    print(f"--- TEST INTEGRAL FASE 2: {excel_path} ---\n")

    # 2. PASO 1: Extracción (I/O)
    result_ext = extractor.extract_from_excel(excel_path)
    if not result_ext.success:
        print(f"FALLO EN EXTRACCIÓN: {result_ext.error_message}")
        return
    print(f"[1/3] EXTRACTOR: {len(result_ext.filas_crudas)} filas leídas.")

    # 3. PASO 2: Parsing (Expansión 1:N)
    parsed_rows, parsing_metadata = parser.parse_rows(result_ext)
    print(f"[2/3] PARSER: {len(parsed_rows)} registros tras expansión.")

    # 4. PASO 3: Normalización (Tipado y Enums)
    normalized_data = normalizer.normalize_rows(parsed_rows, parsing_metadata)
    print(f"[3/3] NORMALIZER: {len(normalized_data)} registros normalizados con éxito.")

    # 5. Mostrar resultados finales y verificar tipos
    print("\n--- RESULTADOS FINALES (DATOS LISTOS PARA BD) ---")
    print(f"{'FILA':<5} | {'PROFESOR':<20} | {'DÍA (ENUM)':<12} | {'HORARIOS (time)':<15}")
    print("-" * 70)
    
    for row in normalized_data:
        # Verificamos que sean los tipos correctos
        h_inicio = row.hora_inicio.strftime("%H:%M")
        h_fin = row.hora_fin.strftime("%H:%M")
        
        print(f"{row.fila_origen:<5} | "
              f"{row.profesor_nombre_completo:<20} | "
              f"{row.dia_semana.value:<12} | "
              f"{h_inicio} - {h_fin}")

    # 6. Informe de errores/warnings acumulados
    if parsing_metadata.errors:
        print("\n[!] ERRORES DETECTADOS:")
        for err in parsing_metadata.errors:
            print(f"  - {err}")

    if parsing_metadata.warnings:
        print("\n[!] WARNINGS DETECTADOS:")
        for warn in parsing_metadata.warnings:
            print(f"  - {warn.message}")

if __name__ == "__main__":
    test_full_pipeline_fase2()