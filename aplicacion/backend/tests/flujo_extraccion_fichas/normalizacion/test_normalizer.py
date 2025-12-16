"""
Script de testing para flujo completo: Extracción + Parsing + Normalización de Fichas.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from dataclasses import is_dataclass, asdict

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.fichas.extractor import FichaExtractor
from core.extraccion.fichas.parser import FichaParser
from core.extraccion.fichas.normalize import DataNormalizer
from core.extraccion.common.entities import ParserError

# ============================================================
#  CONFIGURACIÓN
# ============================================================

DEFAULT_PDF = r"D:\TFG\Fichas\GRADO\G33.pdf"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")


# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================

def print_separator(char="=", length=80):
    print(char * length)

def print_header(title):
    print_separator()
    print(f" {title}")
    print_separator()

def print_step(step, total, message):
    print(f"\n{'─' * 80}")
    print(f"[{step}/{total}] {message}")
    print(f"{'─' * 80}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(label, value, indent=3):
    spaces = " " * indent
    print(f"{spaces}{label}: {value}")


def convert_to_dict(obj):
    """
    Convertir objetos dataclass a dict recursivamente.
    Maneja enums, listas y objetos anidados.
    """
    # Si es un dataclass detectado por is_dataclass()
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for field_name, field_value in obj.__dict__.items():
            result[field_name] = convert_to_dict(field_value)
        return result
    
    # Si es una lista, convertir cada elemento
    elif isinstance(obj, list):
        return [convert_to_dict(item) for item in obj]
    
    # Si es un enum, extraer su valor
    elif hasattr(obj, 'value') and hasattr(obj, 'name'):
        return obj.value
    
    # Si es un tipo primitivo o None, retornar tal cual
    elif obj is None or isinstance(obj, (dict, str, int, float, bool)):
        return obj
    
    # Fallback: Si tiene __dict__, intentar convertirlo manualmente
    elif hasattr(obj, '__dict__') and not callable(getattr(obj, '__dict__', None)):
        result = {}
        for field_name, field_value in obj.__dict__.items():
            if not field_name.startswith('_'):
                result[field_name] = convert_to_dict(field_value)
        return result
    
    # Último recurso: convertir a string
    else:
        try:
            return str(obj)
        except:
            return obj


def save_json(data: dict, filepath: str):
    """Guardar datos en formato JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def test_flujo_completo(pdf_path: str):
    """Ejecutar flujo completo: extracción + parsing + normalización."""
    
    print_header(f"TEST FLUJO COMPLETO: {Path(pdf_path).name}")
    print(f"Archivo: {pdf_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # PASO 1: EXTRACCIÓN
    print_step(1, 4, "Extrayendo texto del PDF")
    
    try:
        extractor = FichaExtractor()
        extraction_result = extractor.extract_from_pdf(pdf_path)
        
        if extraction_result.metadata.status != "completed":
            print_error(f"Error en extracción: {extraction_result.metadata.status}")
            return None
        
        print_success(f"Extracción completada: {extraction_result.metadata.char_count} caracteres")
        print_info("Calidad", extraction_result.metadata.quality.value)
        print_info("Confianza", f"{extraction_result.metadata.confidence:.2%}")
        
    except Exception as e:
        print_error(f"Error crítico en extracción: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # PASO 2: PARSING
    print_step(2, 4, "Parseando texto extraído")
    
    try:
        parser = FichaParser()
        parsed_data = parser.parse_text(
            text=extraction_result.text,
            extraction_metadata=extraction_result.metadata
        )
        
        print_success("Parsing completado")
        print_info("Asignatura", f"{parsed_data.codigo_plan} - {parsed_data.nombre}")
        print_info("Titulaciones", len(parsed_data.titulaciones))
        print_info("Profesores", len(parsed_data.profesores))
        
    except Exception as e:
        print_error(f"Error crítico en parsing: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # PASO 3: NORMALIZACIÓN
    print_step(3, 4, "Normalizando datos parseados")
    
    try:
        normalizer = DataNormalizer()
        
        # parsed_data ya es un SubjectSheet, usarlo directamente
        normalized_data = normalizer.normalize_ficha(parsed_data)
        
        print_success("Normalización completada")
        print_info("Código normalizado", normalized_data.asignatura.codigo_plan)
        print_info("Nombre normalizado", normalized_data.asignatura.nombre)
        print_info("Periodo enum", normalized_data.asignatura.periodo.value)
        
        print(f"\n   Titulaciones normalizadas:")
        for i, tit in enumerate(normalized_data.titulaciones, 1):
            print(f"      {i}. {tit.programa_nombre}")
            print(f"         - Tipo: {tit.tipo_asignatura.value}")
            print(f"         - Curso: {tit.curso}")
        
        print(f"\n   Profesores normalizados:")
        for i, prof in enumerate(normalized_data.profesores, 1):
            print(f"      {i}. {prof.nombre} {prof.apellidos}")
        
    except Exception as e:
        print_error(f"Error crítico en normalización: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # PASO 4: GUARDAR RESULTADOS
    print_step(4, 4, "Guardando resultados")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = Path(pdf_path).stem
    
    # Convertir y guardar JSON normalizado (sin sufijo)
    print("   📋 Convirtiendo datos normalizados a dict...")
    normalized_dict = convert_to_dict(normalized_data)
    
    if not isinstance(normalized_dict, dict):
        print_error(f"Error: convert_to_dict() retornó {type(normalized_dict)}")
        return None
    
    normalized_json_path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    save_json(normalized_dict, normalized_json_path)
    
    print_success("Resultado guardado:")
    print_info("JSON normalizado", normalized_json_path)
    
    return {
        'parsed': parsed_data,
        'normalized': normalized_data
    }


if __name__ == "__main__":
    print("\n")
    
    if len(sys.argv) >= 2:
        pdf_path = sys.argv[1]
    else:
        pdf_path = DEFAULT_PDF
        print(f"ℹ️  Usando PDF por defecto: {DEFAULT_PDF}\n")
    
    results = test_flujo_completo(pdf_path)
    
    print()
    sys.exit(0 if results else 1)