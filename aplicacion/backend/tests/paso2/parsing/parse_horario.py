import sys
import os
import json
from dataclasses import asdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.pdf_extractor import get_pdf_extractor
from core.extraccion.parsers.horario_parser import HorarioParser

HORARIOS_OUTDIR = os.path.join(os.path.dirname(__file__), "horarios")
def parse_pdf_text(pdf_path):
    extractor = get_pdf_extractor()
    result = extractor.extract_from_pdf(pdf_path)
    if not result or not result.text or result.quality.value == "unusable":
        print(f"No se pudo extraer texto útil de {os.path.basename(pdf_path)} (calidad: {result.quality.value})")
        return None
    print(f"\n--- Extracción PDF: {os.path.basename(pdf_path)} ---")
    print(f"Calidad: {result.quality.value}, Confianza: {result.confidence:.2f}")
    return result.text


def to_serializable(obj):
    """Convierte dataclasses anidados y objetos datetime a tipos serializables."""
    import datetime
    from dataclasses import asdict
    if isinstance(obj, list):
        return [to_serializable(i) for i in obj]
    elif hasattr(obj, "__dataclass_fields__"):
        d = {}
        for k, v in asdict(obj).items():
            d[k] = to_serializable(v)
        return d
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    else:
        return obj

def save_result(obj, outdir, pdf_path):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    outpath_json = os.path.join(outdir, base + ".json")
    data = to_serializable(obj)
    with open(outpath_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Guardado resultado en: {outpath_json}")

def run_horario_parser(pdf_path):
    text = parse_pdf_text(pdf_path)
    if not text:
        return
    parser = HorarioParser()
    try:
        horario = parser.parse_text(text)
        print("\n--- Resultado HorarioParser ---")
        print(horario)
        save_result(horario, HORARIOS_OUTDIR, pdf_path)
    except Exception as e:
        print(f"Error en HorarioParser: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parse_horario.py <ruta_horario.pdf>")
        sys.exit(1)
    horario_pdf = sys.argv[1]
    run_horario_parser(horario_pdf)