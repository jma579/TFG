"""
Script de testing para flujo completo: Extracción + Parsing de Horarios.

Flujo:
1. Extraer tablas del PDF usando HorarioExtractor
2. Parsear tablas extraídas usando HorarioParser
3. Mostrar resultados de ambas fases
4. Guardar resultados:
   - <nombre>.json: Salida directa del parser (ParsingResult normalizado)

Uso:
    python test_horarios_parsing.py <ruta_pdf>
    python test_horarios_parsing.py  # Usa PDF por defecto

Ejemplo:
    python test_horarios_parsing.py "D:/TFG/Horarios/GRADO/horario_fisica.pdf"
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.newhorarios.extractor import HorarioExtractor
from core.extraccion.newhorarios.parser import HorarioParser
from core.extraccion.common.entities import ParserError

# ============================================================
#  CONFIGURACIÓN
# ============================================================

# PDF por defecto
DEFAULT_PDF = r"D:\TFG\Horarios\Grado\1C_GRADO FISICA_v6.pdf"

# Directorio de salida
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")

# Configuración del parser
PARSER_CONFIG = {
    'log_level': 'DEBUG',
    'strict_validation': True
}

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================

def print_separator(char="=", length=80):
    """Imprimir separador visual."""
    print(char * length)

def print_header(title):
    """Imprimir encabezado."""
    print_separator()
    print(f" {title}")
    print_separator()

def print_step(step, total, message):
    """Imprimir paso del proceso."""
    print(f"\n{'─' * 80}")
    print(f"[{step}/{total}] {message}")
    print(f"{'─' * 80}")

def print_success(message):
    print(f"✅ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def print_error(message):
    print(f"❌ {message}")

def save_json(data: dict, filepath: str):
    """Guardar datos en formato JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def test_flujo_completo(pdf_path: str):
    """Ejecutar flujo completo: extracción + parsing."""
    
    print_header(f"TEST FLUJO COMPLETO: {Path(pdf_path).name}")
    print(f"Archivo: {pdf_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # =========================================================================
    # PASO 1: EXTRACCIÓN
    # =========================================================================
    print_step(1, 3, "Extrayendo tablas del PDF")
    
    try:
        extractor = HorarioExtractor()
        extraction_result = extractor.extract(pdf_path)
        
        if extraction_result.metadata.status != "completed":
            print_error(f"Error en extracción: {extraction_result.metadata.status}")
            if extraction_result.metadata.errors:
                for error in extraction_result.metadata.errors:
                    print(f"   - {error}")
            return None
        
        print_success(f"Extracción completada: {len(extraction_result.tablas)} tablas")
        print(f"   Título: {extraction_result.titulo}")
        for i, tabla in enumerate(extraction_result.tablas, 1):
            print(f"   Tabla {i}: {tabla.curso} ({len(tabla.celdas)} filas)")
        
    except Exception as e:
        print_error(f"Error crítico en extracción: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # =========================================================================
    # PASO 2: PARSING
    # =========================================================================
    print_step(2, 3, "Parseando tablas extraídas")
    
    try:
        parser = HorarioParser(config=PARSER_CONFIG)
        parsing_result = parser.parse(extraction_result)
        
        print_success("Parsing completado")
        print(f"   Horarios procesados: {len(parsing_result.horarios)}")
        
        # Mostrar warnings si existen
        if parsing_result.parsing_metadata.warnings:
            print(f"\n⚠️  Warnings ({len(parsing_result.parsing_metadata.warnings)}):")
            for warning in parsing_result.parsing_metadata.warnings:
                print(f"    - {warning.message} ({warning.severity})")
        
        # Mostrar errors si existen
        if parsing_result.parsing_metadata.errors:
            print(f"\n❌ Errores de parsing ({len(parsing_result.parsing_metadata.errors)}):")
            for error in parsing_result.parsing_metadata.errors:
                print(f"    - {error}")
        
    except ParserError as e:
        print_error(f"Error de parsing: {e}")
        return None
    except Exception as e:
        print_error(f"Error crítico en parsing: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # =========================================================================
    # PASO 3: GUARDAR RESULTADOS
    # =========================================================================
    print_step(3, 3, "Guardando resultados")
    
    # Asegurar que existe el directorio de salida
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Nombre base del archivo
    filename = Path(pdf_path).stem
    json_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    
    # Guardar JSON
    save_json(parsing_result.raw_json, json_path)
    
    print_success("Resultados guardados:")
    print(f"   📋 JSON: {json_path}")
    
    return parsing_result

# ============================================================
#  MAIN
# ============================================================

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
    
    print()
    
    # Ejecutar test completo
    success = test_flujo_completo(pdf_path)
    
    print()
    
    # Exit code
    sys.exit(0 if success else 1)