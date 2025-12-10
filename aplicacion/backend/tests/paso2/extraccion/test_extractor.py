"""
Pequeño runner para validar el extractor PDF con un lote de archivos.

Qué hace por cada PDF:
- Llama al extractor nativo (solo PDFs con texto embebido).
- Guarda el texto limpio en OUTPUT_DIR/*.txt (opcional).
- Guarda un JSON con calidad, confianza, metadatos y errores en OUTPUT_DIR/*.json.
- Muestra un resumen por consola al final.

Configura rutas y opciones en el bloque CONFIG.
"""


from __future__ import annotations

# === Permitir imports absolutos desde cualquier ubicación ===
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[3]))

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional, List


# === CONFIGURACIÓN PARA UN SOLO PDF ===
PDF_PATH = Path(r"C:/Users/usuario/TFG/Fichas/GRADO/G49.pdf")
TXT_OUTPUT_DIR = Path(r"c:/Users/usuario/TFG/aplicacion/backend/tests/paso2/extraccion/extraction_results/txt")
JSON_OUTPUT_DIR = Path(r"c:/Users/usuario/TFG/aplicacion/backend/tests/paso2/extraccion/extraction_results/json")
SAVE_TEXT = True
SAVE_JSON = True

# =========================
# IMPORTS DEL PROYECTO
# =========================
try:
    # Tu extractor y entidades/constantes
    from core.extraccion.fichas.extractor import get_pdf_extractor, PDFExtractor  # type: ignore
except Exception:
    # Si no tienes factory, instanciamos directamente más abajo
    get_pdf_extractor = None  # type: ignore
    PDFExtractor = None       # type: ignore

from core.extraccion.entities.extractor import (
    ExtractionResult,
    ProcessingStatus,
    ExtractionQuality,
)

# =========================
# UTILIDADES
# =========================
def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def safe_stem(p: Path) -> str:
    """Nombre base seguro para archivos de salida."""
    return p.stem.replace(" ", "_").replace("/", "_").replace("\\", "_")

def summarize_result(pdf_path: Path, result: ExtractionResult) -> dict:
    md = result.metadata
    return {
        "file": str(pdf_path),
        "status": result.status.value,
        "quality": result.quality.value,
        "confidence": round(float(result.confidence), 4),
        "pages": md.page_count,
        "chars": md.char_count,
        "words": md.word_count,
        "has_embedded_text": md.has_embedded_text,
        "processing_time_s": round(float(md.processing_time_seconds), 3),
        "warnings": len(md.warnings or []),
        "errors": len(md.errors or []),
        "error_type": getattr(result.error_type, "value", None),
        "error_message": result.error_message,
    }

def to_jsonable(result: ExtractionResult) -> dict:
    """Convierte el ExtractionResult a un dict serializable (incluye enums como string)."""
    d = result.to_dict() if hasattr(result, "to_dict") else asdict(result)  # por si tu clase ya implementa to_dict()
    # Asegura que metadata está en dict
    if "metadata" in d and hasattr(result.metadata, "to_dict"):
        d["metadata"] = result.metadata.to_dict()
    return d

# =========================
# MAIN
# =========================

def main() -> int:

    if not PDF_PATH.exists():
        print(f"[ERROR] PDF no existe: {PDF_PATH}", file=sys.stderr)
        return 2

    ensure_dir(TXT_OUTPUT_DIR)
    ensure_dir(JSON_OUTPUT_DIR)

    pdf_paths: List[Path] = [PDF_PATH]

    # Instanciamos el extractor
    extractor = None
    if callable(get_pdf_extractor):
        try:
            extractor = get_pdf_extractor()
        except Exception:
            extractor = None

    if extractor is None:
        if PDFExtractor is None:
            print("[ERROR] No se pudo importar/instanciar el extractor. Revisa core/extraccion/pdf_extractor.py", file=sys.stderr)
            return 3
        extractor = PDFExtractor()  # type: ignore

    print(f"[INFO] Procesando {len(pdf_paths)} PDF(s): {PDF_PATH}")
    t0 = time.time()

    summary_rows = []
    ok_count = 0
    usable_count = 0
    fail_count = 0

    for i, pdf_path in enumerate(pdf_paths, 1):
        print(f"  [{i}/{len(pdf_paths)}] {pdf_path.name} ...", end="", flush=True)
        try:
            result: ExtractionResult = extractor.extract_from_pdf(str(pdf_path))
        except Exception as e:
            print(" ERROR")
            row = {
                "file": str(pdf_path),
                "status": "failed",
                "quality": "unusable",
                "confidence": 0.0,
                "error_type": "unknown_error",
                "error_message": str(e),
            }
            summary_rows.append(row)
            fail_count += 1
            continue

        # Guardar outputs en carpetas separadas
        base_txt = TXT_OUTPUT_DIR / safe_stem(pdf_path)
        base_json = JSON_OUTPUT_DIR / safe_stem(pdf_path)

        if SAVE_TEXT and result.status == ProcessingStatus.COMPLETED:
            txt_path = base_txt.with_suffix(".txt")
            with txt_path.open("w", encoding="utf-8") as f:
                f.write(result.text or "")

        if SAVE_JSON:
            json_path = base_json.with_suffix(".json")
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(to_jsonable(result), f, ensure_ascii=False, indent=2)

        row = summarize_result(pdf_path, result)
        summary_rows.append(row)

        if result.status == ProcessingStatus.COMPLETED:
            ok_count += 1
            if result.quality in {
                ExtractionQuality.EXCELLENT,
                ExtractionQuality.GOOD,
                ExtractionQuality.ACCEPTABLE,
            }:
                usable_count += 1

        print(f" {row['status']}, {row['quality']}, {row['words']} palabras, {row['pages']} pág., {row['processing_time_s']}s")

    # Guardar un CSV resumen (opcional pero útil)
    csv_path = JSON_OUTPUT_DIR.parent / "summary.csv"
    try:
        import csv
        keys = [
            "file", "status", "quality", "confidence", "pages", "chars", "words",
            "has_embedded_text", "processing_time_s", "warnings", "errors", "error_type", "error_message"
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in summary_rows:
                writer.writerow({k: row.get(k, "") for k in keys})
    except Exception as e:
        print(f"[WARN] No se pudo escribir summary.csv: {e}", file=sys.stderr)

    dt = time.time() - t0
    print("\n========== RESUMEN ==========")
    print(f"Total: {len(pdf_paths)} | OK: {ok_count} | Usables: {usable_count} | Fallos: {fail_count}")
    print(f"Salida TXT: {TXT_OUTPUT_DIR}")
    print(f"Salida JSON: {JSON_OUTPUT_DIR}")
    print(f"Tiempo total: {dt:.2f}s")
    print("=============================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
