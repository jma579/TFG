# -*- coding: utf-8 -*-
"""
Script de testing para el extractor de horarios (Excel).

Flujo:
1) Validar el .xlsx
2) Inicializar extractor de Excel
3) Ejecutar extracción
4) Mostrar metadatos y pequeño resumen
5) Guardar resultados en ./results:
   - excel_full_<timestamp>.json   (payload completo serializable)
   - excel_summary_<timestamp>.json (resumen útil)

Uso:
    python test_excel_extractor.py <ruta_xlsx>
    python test_excel_extractor.py  # usa ruta por defecto

Este script replica la estructura y estilo de tu test_extractor.py de fichas. 
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# -------------------------------------------------------------------
# Ajuste del sys.path para poder importar tu paquete del proyecto
# (sube 3 niveles como en el script de fichas)
# -------------------------------------------------------------------
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[2]  # ajusta si tu árbol difiere
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------------------------
# Import dinámico del extractor (probamos varias rutas/clases)
# -------------------------------------------------------------------
ExtractorCls = None
import_error = None
try:
    # Ruta estilo "core"
    from core.extraccion.horarios.excel_extractor import ExcelScheduleExtractor as ExtractorCls  # type: ignore
except Exception as e1:
    import_error = e1
    try:
        # Ruta estilo "backend"
        from backend.extraction.excel_extractor import ExcelExtractor as ExtractorCls  # type: ignore
    except Exception as e2:
        import_error = (e1, e2)

# Enums comunes (para mostrar status/quality legibles)
try:
    from core.extraccion.common.entities import ProcessingStatus, ExtractionQuality  # type: ignore
except Exception:
    ProcessingStatus = None
    ExtractionQuality = None

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
DEFAULT_XLSX = r"D:\TFG\Horarios\Grado\HORARIOS 2025-26.xlsx"   # <-- cambia si lo necesitas
OUTPUT_DIR = THIS_DIR / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# Utilidades de impresión
# -------------------------------------------------------------------
def print_separator(char="=", length=80):
    print(char * length)

def print_header(title: str):
    print_separator()
    print(f" {title}")
    print_separator()

# -------------------------------------------------------------------
# Serialización segura (dataclasses / enums / objetos)
# -------------------------------------------------------------------
def to_serializable(obj: Any) -> Any:
    """Convierte dataclasses/enums/objetos a algo serializable por JSON."""
    # dataclasses
    try:
        import dataclasses as _dc
        if _dc.is_dataclass(obj):
            return {k: to_serializable(v) for k, v in _dc.asdict(obj).items()}
    except Exception:
        pass
    # enums
    if hasattr(obj, "value"):
        try:
            return obj.value
        except Exception:
            pass
    # listas / tuplas
    if isinstance(obj, (list, tuple)):
        return [to_serializable(x) for x in obj]
    # dicts
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    # tipos básicos o fallback
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


# -------------------------------------------------------------------
# Lógica principal de test
# -------------------------------------------------------------------
def test_excel_extractor(xlsx_path: str) -> bool:
    print_header(f"TEST EXTRACTOR EXCEL: {os.path.basename(xlsx_path)}")
    print(f"Archivo: {xlsx_path}")
    print(f"Fecha:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 0) Comprobación de import
    if ExtractorCls is None:
        print("❌ No se pudo importar el extractor de Excel.")
        print("   Intentos: core.extraccion.horarios.excel_extractor / backend.extraction.excel_extractor")
        print(f"   Detalle: {import_error}\n")
        return False

    # 1) Validación del archivo
    print("📋 [1/4] Validando archivo...")
    xp = Path(xlsx_path)
    if not xp.exists():
        print(f"❌ ERROR: Archivo no encontrado: {xlsx_path}")
        return False
    if xp.suffix.lower() not in [".xlsx", ".xlsm", ".xls"]:
        print(f"❌ ERROR: No es un Excel válido: {xlsx_path}")
        return False
    size = xp.stat().st_size
    print(f"✅ Archivo válido: {size:,} bytes ({size/1024:.1f} KB)\n")

    # 2) Inicializar extractor
    print("🔧 [2/4] Inicializando extractor...")
    try:
        # Soporta distintos constructores
        try:
            config = {
                'log_level': 'DEBUG',  # ← AÑADE ESTO
                'log_block_details': True  # ← Y ESTO
            }
            extractor = ExtractorCls(config=config)  # ← Pasar config
            print("✅ Extractor inicializado")
        except TypeError:
            extractor = ExtractorCls(str(xp))
        print("✅ Extractor inicializado\n")
    except Exception as e:
        print(f"❌ ERROR al inicializar extractor: {e}")
        import traceback; traceback.print_exc()
        return False

    # 3) Ejecutar extracción
    print("📄 [3/4] Ejecutando extracción del Excel...")
    try:
        # Soporta distintas APIs públicas
        result = None
        for call in (
            lambda: extractor.extract(str(xp)),
            lambda: extractor.extract(),  # por si el path se pasó al __init__
        ):
            try:
                result = call()
                break
            except TypeError:
                continue

        if result is None:
            print("❌ No se pudo invocar la función pública de extracción.")
            return False

        # Unificar metadatos (metadata / extraccion_metadata)
        metadata = getattr(result, "metadata", None) or getattr(result, "extraccion_metadata", None)

        print()
        print_separator("-")
        print("RESULTADO DE EXTRACCIÓN")
        print_separator("-")

        if metadata:
            # Enums legibles
            status_str = getattr(metadata, "status", None)
            quality_str = getattr(metadata, "quality", None)
            status_show = getattr(status_str, "value", str(status_str))
            quality_show = getattr(quality_str, "value", str(quality_str))

            print(f"Status:           {status_show}")
            print(f"Calidad:          {quality_show}")
            conf = getattr(metadata, "confidence", 0.0)
            print(f"Confianza:        {conf:.2%}")

            page_count = getattr(metadata, "page_count", None)
            pages_with_text = getattr(metadata, "pages_with_text", None)
            if page_count is not None:
                print(f"Hojas (page_count):     {page_count}")
            if pages_with_text is not None:
                print(f"Hojas con horarios:     {pages_with_text}")

            proc = getattr(metadata, "processing_time_seconds", 0.0)
            print(f"Tiempo:           {proc:.2f}s")

            file_mb = getattr(metadata, "file_size_mb", None)
            if file_mb is not None:
                print(f"Tamaño archivo:   {file_mb:.3f} MB")

            chars = getattr(metadata, "char_count", None)
            words = getattr(metadata, "word_count", None)
            if chars is not None:
                print(f"Caracteres:       {chars:,}")
            if words is not None:
                print(f"Palabras:         {words:,}")

            # Errores / Warnings
            errs = getattr(metadata, "errors", None) or []
            warns = getattr(metadata, "warnings", None) or []
            if errs:
                print(f"\n⚠️  Errores ({len(errs)}):")
                for i, e in enumerate(errs, 1):
                    print(f"    {i}. {e}")
            if warns:
                print(f"\n⚠️  Warnings ({len(warns)}):")
                for i, w in enumerate(warns, 1):
                    print(f"    {i}. {w}")

        else:
            print("(sin metadatos)")

        # Determinar éxito
        success = True
        if ProcessingStatus and metadata and hasattr(metadata, "status"):
            success = (metadata.status == ProcessingStatus.COMPLETED)

        if not success:
            print("\n❌ EXTRACCIÓN FALLIDA\n")
        else:
            print("\n✅ EXTRACCIÓN COMPLETADA\n")

        # 4) Guardar resultados
        print("💾 [4/4] Guardando resultados...")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_full = OUTPUT_DIR / f"excel_full_{ts}.json"
        out_summary = OUTPUT_DIR / f"excel_summary_{ts}.json"

        # Construir payload serializable
        payload = {
            "metadata": to_serializable(metadata) if metadata else None,
            "result": to_serializable(result),
        }
        with open(out_full, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # Resumen legible
        summary = {
            "source_file": str(xp),
            "extracted_at": ts,
            "status": getattr(metadata.status, "value", str(getattr(metadata, "status", None))) if metadata else None,
            "quality": getattr(metadata.quality, "value", str(getattr(metadata, "quality", None))) if metadata else None,
            "confidence": getattr(metadata, "confidence", None) if metadata else None,
            "page_count": getattr(metadata, "page_count", None) if metadata else None,
            "pages_with_text": getattr(metadata, "pages_with_text", None) if metadata else None,
            "coverage": getattr(getattr(extractor, "stats", {}), "get", lambda *_: None)("coverage") if hasattr(extractor, "stats") else None,
            "coherence": getattr(getattr(extractor, "stats", {}), "get", lambda *_: None)("coherence") if hasattr(extractor, "stats") else None,
            "blocks_detected": getattr(getattr(extractor, "stats", {}), "get", lambda *_: None)("blocks_detected") if hasattr(extractor, "stats") else None,
        }
        with open(out_summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"📋 JSON completo: {out_full}")
        print(f"📋 JSON resumen:  {out_summary}")

        return success

    except Exception as e:
        print(f"\n❌ ERROR en extracción: {e}")
        import traceback; traceback.print_exc()
        return False


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
if __name__ == "__main__":
    print()
    if len(sys.argv) >= 2:
        xlsx = sys.argv[1]
        print(f"ℹ️  Usando Excel del argumento: {xlsx}")
    else:
        xlsx = DEFAULT_XLSX
        print("ℹ️  No se especificó Excel, usando por defecto:")
        print(f"    {DEFAULT_XLSX}")
    print()

    ok = test_excel_extractor(xlsx)
    print()
    sys.exit(0 if ok else 1)
