import sys
import os
import json
from dataclasses import asdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.fichas.extractor import get_ficha_extractor
from core.extraccion.fichas.parser import FichaParser

FICHAS_OUTDIR = os.path.join(os.path.dirname(__file__), "fichas")

def parse_pdf_text(pdf_path):
    extractor = get_ficha_extractor()
    result = extractor.extract_from_pdf(pdf_path)
    if not result or not result.text or result.metadata.quality == "unusable":
        print(f"No se pudo extraer texto útil de {os.path.basename(pdf_path)} (calidad: {getattr(result.quality, 'value', 'N/A')})")
        return None
    print(f"\n--- Extracción PDF: {os.path.basename(pdf_path)} ---")
    print(f"Calidad: {result.metadata.quality}, Confianza: {result.metadata.confidence:.2f}")
    return result.text, result.metadata

def save_result(obj, outdir, pdf_path):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    # Guardar como texto plano
    outpath_txt = os.path.join(outdir, base + ".txt")
    with open(outpath_txt, "w", encoding="utf-8") as f:
        f.write(str(obj))
    print(f"Guardado resultado en: {outpath_txt}")
    # Guardar como JSON
    outpath_json = os.path.join(outdir, base + ".json")
    try:
        # Si es dataclass
        data = asdict(obj)
    except Exception:
        # Si no es dataclass, intenta __dict__
        data = obj.__dict__
    with open(outpath_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Guardado resultado en: {outpath_json}")

def run_ficha_parser(pdf_path):
    text, extraction_metadata = parse_pdf_text(pdf_path)
    if not text:
        return
    parser = FichaParser()
    try:
        ficha = parser.parse_text(text, extraction_metadata=extraction_metadata)
        print("\n--- Resultado FichaParser ---")
        print(ficha)
        save_result(ficha, FICHAS_OUTDIR, pdf_path)
    except Exception as e:
        print(f"Error en FichaParser: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parse_ficha.py <ruta_ficha.pdf>")
        sys.exit(1)
    ficha_pdf = sys.argv[1]
    run_ficha_parser(ficha_pdf)
