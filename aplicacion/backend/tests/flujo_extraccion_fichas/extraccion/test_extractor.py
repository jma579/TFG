"""
Script de testing para FichaExtractor (solo extracción de texto).

Flujo:
1. Cargar PDF
2. Extraer texto usando FichaExtractor
3. Mostrar resultados y metadatos
4. Guardar resultados:
   - <nombre>.txt: Solo texto extraído (sin metadatos)
   - <nombre>.json: Metadatos completos del ExtractionResult

Uso:
    python test_extractor.py <ruta_pdf>
    python test_extractor.py  # Usa PDF por defecto

Ejemplo:
    python test_extractor.py "D:/TFG/Fichas/GRADO/G51.pdf"
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.fichas.extractor import FichaExtractor

# ============================================================
#  CONFIGURACIÓN
# ============================================================

# PDF por defecto (cambiar según necesites)
DEFAULT_PDF = r"D:\TFG\Fichas\GRADO\G31.pdf"

# Directorio de salida (mismo directorio del script)
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


def test_extractor(pdf_path: str):
    """
    Probar extracción de texto del PDF.
    
    Args:
        pdf_path: Ruta al archivo PDF
    """
    print_header(f"TEST EXTRACTOR: {os.path.basename(pdf_path)}")
    print(f"Archivo: {pdf_path}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. VALIDAR ARCHIVO
    print("📋 [1/3] Validando archivo...")
    if not os.path.exists(pdf_path):
        print(f"❌ ERROR: Archivo no encontrado: {pdf_path}")
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ ERROR: No es un archivo PDF: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path)
    print(f"✅ Archivo válido: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print()
    
    # 2. CREAR EXTRACTOR
    print("🔧 [2/3] Inicializando extractor...")
    try:
        extractor = FichaExtractor()
        print("✅ Extractor inicializado")
    except Exception as e:
        print(f"❌ ERROR al inicializar extractor: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # 3. EXTRAER TEXTO
    print("📄 [3/3] Extrayendo texto del PDF...")
    try:
        result = extractor.extract_from_pdf(pdf_path)
        
        # Verificar resultado
        print()
        print_separator("-")
        print("RESULTADO DE EXTRACCIÓN")
        print_separator("-")
        
        # ✅ MOSTRAR SOLO CAMPOS QUE EXISTEN EN ExtractionMetadata
        if result.metadata:
            print(f"Status:       {result.metadata.status.value}")
            print(f"Calidad:      {result.metadata.quality.value}")
            print(f"Confianza:    {result.metadata.confidence:.2%}")
            print(f"Páginas:      {result.metadata.page_count}")
            print(f"Caracteres:   {result.metadata.char_count:,}")
            print(f"Palabras:     {result.metadata.word_count:,}")
            print(f"Tiempo:       {result.metadata.processing_time_seconds:.2f}s")
            print(f"Tiene texto:  {'Sí' if result.metadata.has_embedded_text else 'No'}")
            
            # Páginas con texto (si está disponible)
            if result.metadata.pages_with_text is not None:
                print(f"Pág. c/texto: {result.metadata.pages_with_text}")
            
            # Errores (si existen)
            if result.metadata.errors:
                print(f"\n⚠️  Errores ({len(result.metadata.errors)}):")
                for i, error in enumerate(result.metadata.errors, 1):
                    print(f"    {i}. {error}")
            
            # Warnings (si existen)
            if result.metadata.warnings:
                print(f"\n⚠️  Warnings ({len(result.metadata.warnings)}):")
                for i, warning in enumerate(result.metadata.warnings, 1):
                    print(f"    {i}. {warning}")
        else:
            print("(sin metadatos)")
        
        # Verificar si hay error en ExtractionResult
        if hasattr(result, 'error_message') and result.error_message:
            print(f"\n⚠️  Error:       {result.error_message}")
        
        if hasattr(result, 'error_type') and result.error_type:
            error_type_str = result.error_type.value if hasattr(result.error_type, 'value') else str(result.error_type)
            print(f"⚠️  Tipo error:  {error_type_str}")
        
        print()
        
        # Verificar éxito usando ProcessingStatus
        from core.extraccion.common.entities import ProcessingStatus
        success = result.metadata and result.metadata.status == ProcessingStatus.COMPLETED
        
        if not success:
            print("❌ EXTRACCIÓN FALLIDA")
            if hasattr(result, 'error_message'):
                print(f"   Razón: {result.error_message}")
            elif result.metadata:
                print(f"   Status: {result.metadata.status.value}")
            # Guardar resultados para análisis
            save_results(result, pdf_path)
            return False
        
        # Verificar si es usable (quality GOOD o ACCEPTABLE)
        from core.extraccion.common.entities import ExtractionQuality
        is_usable = result.metadata.quality in [ExtractionQuality.GOOD, ExtractionQuality.ACCEPTABLE]
        
        if not is_usable:
            print("⚠️  ADVERTENCIA: Calidad insuficiente para procesamiento")
            print(f"   Calidad: {result.metadata.quality.value}")
        
        # Mostrar preview del texto
        print_separator("-")
        print("PREVIEW DEL TEXTO EXTRAÍDO (primeros 500 caracteres)")
        print_separator("-")
        preview = result.text[:500] if result.text else "(vacío)"
        print(preview)
        if result.text and len(result.text) > 500:
            print("\n[... texto truncado ...]")
        print()
        
        # 4. GUARDAR RESULTADOS
        print("💾 Guardando resultados...")
        save_results(result, pdf_path)
        
        print()
        print_separator("=")
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print_separator("=")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR en extracción: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_results(result, pdf_path: str):
    """
    Guardar resultados de extracción (TXT + JSON).
    
    Args:
        result: ExtractionResult
        pdf_path: Ruta al PDF original
    """
    # Crear directorio de salida si no existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Nombre base del archivo
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 1. GUARDAR TEXTO EXTRAÍDO (.txt)
    txt_file = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
    save_text_file(result, pdf_path, txt_file)
    
    # 2. GUARDAR METADATOS (.json)
    json_file = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    save_json_file(result, pdf_path, json_file)


def save_text_file(result, pdf_path: str, output_path: str):
    """
    Guardar SOLO el texto extraído en archivo TXT (sin metadatos).
    
    Args:
        result: ExtractionResult
        pdf_path: Ruta al PDF original
        output_path: Ruta del archivo TXT de salida
    """
    with open(output_path, "w", encoding="utf-8") as f:
        # ✅ SOLO ESCRIBIR EL TEXTO EXTRAÍDO (sin encabezados ni metadatos)
        f.write(result.text if result.text else "")
    
    print(f"📄 TXT guardado: {output_path}")


def save_json_file(result, pdf_path: str, output_path: str):
    """
    Guardar metadatos y resultado completo en JSON.
    
    Args:
        result: ExtractionResult
        pdf_path: Ruta al PDF original
        output_path: Ruta del archivo JSON de salida
    """
    # Construir diccionario serializable
    data = {
        "metadata": {
            "source_file": os.path.basename(pdf_path),
            "source_path": pdf_path,
            "extraction_date": datetime.now().isoformat(),
            "test_script": "test_extractor.py"
        },
        "extraction_result": {
            "text": result.text if result.text else "",
            "text_length": len(result.text) if result.text else 0,
            "has_error": bool(hasattr(result, 'error_message') and result.error_message),
            "error_message": result.error_message if hasattr(result, 'error_message') and result.error_message else None,
            "error_type": result.error_type.value if hasattr(result, 'error_type') and result.error_type and hasattr(result.error_type, 'value') else None
        },
        "extraction_metadata": {}
    }
    
    # ✅ AGREGAR SOLO CAMPOS QUE EXISTEN EN ExtractionMetadata
    if result.metadata:
        metadata_dict = {
            "status": result.metadata.status.value,
            "quality": result.metadata.quality.value,
            "confidence": result.metadata.confidence,
            "processing_time_seconds": round(result.metadata.processing_time_seconds, 4),
            "page_count": result.metadata.page_count,
            "file_size_mb": round(result.metadata.file_size_mb, 4),
            "has_embedded_text": result.metadata.has_embedded_text,
            "char_count": result.metadata.char_count,
            "word_count": result.metadata.word_count
        }
        
        # Campos opcionales
        if result.metadata.pages_with_text is not None:
            metadata_dict["pages_with_text"] = result.metadata.pages_with_text
        
        if result.metadata.errors:
            metadata_dict["errors"] = result.metadata.errors
        
        if result.metadata.warnings:
            metadata_dict["warnings"] = [str(w) for w in result.metadata.warnings]
        
        data["extraction_metadata"] = metadata_dict
    
    # Guardar JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"📋 JSON guardado: {output_path}")


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
    
    # Ejecutar test
    success = test_extractor(pdf_path)
    
    print()
    
    # Exit code
    sys.exit(0 if success else 1)