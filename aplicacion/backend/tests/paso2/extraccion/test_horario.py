import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.extraccion.horarios.extractor import get_schedule_extractor

# === CONFIGURACIÓN ===
PDF_PATH = Path(r"C:\Users\usuario\TFG\Horarios\Grado\1C_DOBLE GRADO_v6.pdf")  # Cambia la ruta al PDF real
TXT_OUTPUT_DIR = Path(r"c:/Users/usuario/TFG/aplicacion/backend/tests/paso2/extraccion/extraction_results/txt")
JSON_OUTPUT_DIR = Path(r"c:/Users/usuario/TFG/aplicacion/backend/tests/paso2/extraccion/extraction_results/json")

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def safe_stem(p: Path) -> str:
    return p.stem.replace(" ", "_").replace("/", "_").replace("\\", "_")

def main():
    if not PDF_PATH.exists():
        print(f"[ERROR] PDF no existe: {PDF_PATH}", file=sys.stderr)
        return 2

    ensure_dir(TXT_OUTPUT_DIR)
    ensure_dir(JSON_OUTPUT_DIR)

    extractor = get_schedule_extractor()
    result = extractor.extract(str(PDF_PATH))

    # Guardar JSON
    json_path = JSON_OUTPUT_DIR / (safe_stem(PDF_PATH) + ".json")
    with json_path.open("w", encoding="utf-8") as f:
        # Convierte los warnings a dict si son dataclasses
        def warning_to_dict(w):
            return {"message": w.message, "severity": w.severity}
        metadata = result.extraccion_metadata
        meta_dict = metadata.__dict__.copy()
        meta_dict["warnings"] = [warning_to_dict(w) for w in meta_dict.get("warnings", [])]
        meta_dict["errors"] = list(meta_dict.get("errors", []))
        out = {
            "titulacion": result.titulacion,
            "raw_tables": [rt.__dict__ for rt in result.raw_tables],
            "clean_tables": [ct.__dict__ for ct in result.clean_tables],
            "extraccion_metadata": meta_dict,
        }
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Guardar TXT de la primera tabla limpia (si existe)
    if result.clean_tables:
        txt_path = TXT_OUTPUT_DIR / (safe_stem(PDF_PATH) + ".txt")
        with txt_path.open("w", encoding="utf-8") as f:
            ct = result.clean_tables[0]
            # Escribe cabecera
            f.write("\t".join(ct.header_days) + "\n")
            # Escribe filas
            for i, row in enumerate(ct.cells):
                hora = ct.time_axis[i] if i < len(ct.time_axis) else ""
                f.write(hora + "\t" + "\t".join(row) + "\n")

    print(f"[OK] Guardado JSON en: {json_path}")
    if result.clean_tables:
        print(f"[OK] Guardado TXT en: {txt_path}")
    else:
        print("[WARN] No se extrajo ninguna tabla limpia.")

if __name__ == "__main__":
    main()