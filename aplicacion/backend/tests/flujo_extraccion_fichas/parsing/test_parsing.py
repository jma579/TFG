"""
Script de testing para flujo completo: Extracción + Parsing de Fichas.

Flujo:
1. Extraer texto del PDF usando FichaExtractor
2. Parsear texto extraído usando FichaParser
3. Mostrar resultados de ambas fases
4. Guardar resultados:
   - <nombre>.json: Salida directa del parser (SubjectSheet normalizado)

Uso:
    python test_parsing.py <ruta_pdf>
    python test_parsing.py  # Usa PDF por defecto

Ejemplo:
    python test_parsing.py "D:/TFG/Fichas/GRADO/G652.pdf"
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.fichas.extractor import FichaExtractor
from core.extraccion.fichas.parser import FichaParser
from core.extraccion.common.entities import ParserError

# ============================================================
#  CONFIGURACIÓN
# ============================================================

# PDF por defecto
DEFAULT_PDF = r"D:\TFG\Fichas\GRADO\G31.pdf"

# Directorio de salida
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")


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
    """Imprimir mensaje de éxito."""
    print(f"✅ {message}")


def print_error(message):
    """Imprimir mensaje de error."""
    print(f"❌ {message}")


def print_warning(message):
    """Imprimir mensaje de advertencia."""
    print(f"⚠️  {message}")


def json_serializer(obj):
    """Serializador personalizado para objetos no estándar en JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, 'value'):  # Para Enums
        return obj.value
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)


def save_json(data: dict, filepath: str):
    """Guardar datos en formato JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=json_serializer)


def test_flujo_completo(pdf_path: str):
    """Ejecutar flujo completo: extracción + parsing."""
    
    print_header(f"TEST FLUJO COMPLETO: {Path(pdf_path).name}")
    print(f"Archivo: {pdf_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # =========================================================================
    # PASO 1: EXTRACCIÓN
    # =========================================================================
    print_step(1, 3, "Extrayendo texto del PDF")
    
    try:
        extractor = FichaExtractor()
        extraction_result = extractor.extract_from_pdf(pdf_path)
        
        # ✅ CORRECCIÓN: Verificar el status en metadata, no has_error
        if extraction_result.metadata.status != "completed":
            print_error(f"Error en extracción: {extraction_result.metadata.status}")
            if extraction_result.metadata.errors:
                for error in extraction_result.metadata.errors:
                    print(f"   - {error}")
            return None
        
        print_success(f"Extracción completada: {extraction_result.metadata.char_count} caracteres")
        print(f"   Calidad: {extraction_result.metadata.quality}")
        print(f"   Confianza: {extraction_result.metadata.confidence:.2%}")
        
    except Exception as e:
        print_error(f"Error crítico en extracción: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # =========================================================================
    # PASO 2: PARSING
    # =========================================================================
    print_step(2, 3, "Parseando texto extraído")
    
    try:
        parser = FichaParser()
        
        # ✅ Pasar extraction_metadata al parser
        parsed_data = parser.parse_text(
            text=extraction_result.text,
            extraction_metadata=extraction_result.metadata
        )
        
        print_success("Parsing completado")
        print(f"   Asignatura: {parsed_data.codigo_plan} - {parsed_data.nombre}")
        print(f"   Profesores: {len(parsed_data.profesores)}")
        
        # Mostrar warnings si existen
        if parsed_data.parsing_metadata and parsed_data.parsing_metadata.warnings:
            warnings = parsed_data.parsing_metadata.warnings
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"    - {warning}")
        
        # Mostrar errors si existen
        if parsed_data.parsing_metadata and parsed_data.parsing_metadata.errors:
            errors = parsed_data.parsing_metadata.errors
            print(f"\n❌ Errores de parsing ({len(errors)}):")
            for error in errors:
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
    json_path = os.path.join(OUTPUT_DIR, f"{filename}_parsed.json")
    
    # Convertir SubjectSheet a diccionario usando asdict (dataclass helper)
    try:
        parsed_dict = asdict(parsed_data)
    except Exception as e:
        print_warning(f"No se pudo convertir a diccionario: {e}")
        parsed_dict = parsed_data.__dict__ if hasattr(parsed_data, '__dict__') else {}
    
    # Guardar JSON
    save_json(parsed_dict, json_path)
    
    print_success("Resultado guardado:")
    print(f"   📋 JSON: {json_path}")
    
    return parsed_data


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