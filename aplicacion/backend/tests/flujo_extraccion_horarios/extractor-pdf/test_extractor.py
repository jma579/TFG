"""
Script de testing para HorarioExtractor.

Flujo:
1. Cargar PDF
2. Extraer tablas usando HorarioExtractor
3. Mostrar resultados y metadatos
4. Guardar resultados:
   - <nombre>.json: Resultado completo con tablas y metadatos
   - <nombre>_tabla_<n>.txt: Contenido de cada tabla extraída

Uso:
    python test_extractor.py <ruta_pdf>
    python test_extractor.py  # Usa PDF por defecto
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.newhorarios.extractor import HorarioExtractor
from core.extraccion.newhorarios.entities import TablaHorario

# ============================================================
#  CONFIGURACIÓN
# ============================================================

DEFAULT_PDF = r"D:\TFG\Horarios\Grado\1C_GRADO FISICA_v6.pdf"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")

def print_separator(char="=", length=80):
    """Imprimir separador visual."""
    print(char * length)

def print_header(title):
    """Imprimir encabezado."""
    print_separator()
    print(f" {title}")
    print_separator()

def print_table(tabla: TablaHorario):
    """
    Imprime una tabla de horario en formato legible.
    
    Args:
        tabla: Tabla de horario a imprimir
    """
    print(f"Curso: {tabla.curso}")
    if tabla.mencion:
        print(f"Mención: {tabla.mencion}")
    print(f"Página: {tabla.pagina}\n")
    
    # Imprimir encabezados
    print("     |", end=" ")
    for day in tabla.day_columns:
        print(f"{day:^15}|", end=" ")
    print("\n" + "-" * 90)
    
    # Imprimir contenido
    for i, hora in enumerate(tabla.time_rows):
        print(f"{hora:5}|", end=" ")
        for j in range(len(tabla.day_columns)):
            contenido = tabla.celdas[i][j] or ""
            print(f"{contenido:^15}|", end=" ")
        print()

def test_extractor(pdf_path: str) -> bool:
    """
    Probar extracción de horarios del PDF.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        bool: True si la extracción fue exitosa
    """
    print_header(f"TEST EXTRACTOR HORARIOS: {os.path.basename(pdf_path)}")
    print(f"Archivo: {pdf_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Validar archivo
    print("📋 [1/3] Validando archivo...")
    if not os.path.exists(pdf_path):
        print(f"❌ ERROR: Archivo no encontrado: {pdf_path}")
        return False
    
    # 2. Crear extractor
    print("🔧 [2/3] Inicializando extractor...")
    try:
        extractor = HorarioExtractor()
        print("✅ Extractor inicializado")
    except Exception as e:
        print(f"❌ ERROR al inicializar extractor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Extraer tablas
    print("📄 [3/3] Extrayendo tablas del PDF...")
    try:
        result = extractor.extract(pdf_path)
        
        # Mostrar resultado
        print("\nRESULTADO DE EXTRACCIÓN")
        print_separator("-")
        print(f"Título: {result.titulo}")
        print(f"Tablas encontradas: {len(result.tablas)}")
        print(f"Status: {result.metadata.status.value}")
        print(f"Calidad: {result.metadata.quality.value}")
        print(f"Tiempo: {result.metadata.processing_time_seconds:.2f}s")
        
        # Mostrar warnings si hay
        if result.metadata.warnings:
            print("\n⚠️  Warnings:")
            for warning in result.metadata.warnings:
                print(f"  - {warning.message}")
        
        # Mostrar preview de cada tabla
        for i, tabla in enumerate(result.tablas, 1):
            print(f"\nTABLA {i}")
            print_separator("-")
            print_table(tabla)
        
        # Guardar resultados
        save_results(result, pdf_path)
        
        print("\n✅ TEST COMPLETADO EXITOSAMENTE")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR en extracción: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_results(result, pdf_path: str):
    """Guardar resultados de la extracción."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Guardar JSON con resultado completo
    json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    data = {
        "metadata": {
            "source_file": os.path.basename(pdf_path),
            "extraction_date": datetime.now().isoformat(),
            "titulo": result.titulo,
            "status": result.metadata.status.value,
            "quality": result.metadata.quality.value,
            "processing_time": result.metadata.processing_time_seconds,
            "warnings": [w.message for w in result.metadata.warnings]
        },
        "tablas": [
            {
                "curso": t.curso,
                "mencion": t.mencion,
                "pagina": t.pagina,
                "dias": t.day_columns,
                "horas": t.time_rows,
                "celdas": t.celdas
            }
            for t in result.tablas
        ]
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Resultados guardados en: {json_path}")

if __name__ == "__main__":
    print("\n")
    
    # Determinar PDF a procesar
    if len(sys.argv) >= 2:
        pdf_path = sys.argv[1]
        print(f"ℹ️  Usando PDF del argumento: {pdf_path}")
    else:
        pdf_path = DEFAULT_PDF
        print(f"ℹ️  No se especificó PDF, usando por defecto:")
        print(f"   {DEFAULT_PDF}")
    
    # Ejecutar test
    success = test_extractor(pdf_path)
    
    # Exit code
    sys.exit(0 if success else 1)