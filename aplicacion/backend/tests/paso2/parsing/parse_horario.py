import sys
import os
import json
from dataclasses import asdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.horarios.extractor import get_schedule_extractor
from core.extraccion.horarios.parser import ScheduleParser

HORARIOS_OUTDIR = os.path.join(os.path.dirname(__file__), "horarios")

def extract_and_parse_horario(pdf_path):
    extractor = get_schedule_extractor()
    extraction_result = extractor.extract(pdf_path)
    if not extraction_result or not extraction_result.clean_tables:
        print(f"No se pudo extraer un horario útil de {os.path.basename(pdf_path)}")
        return None
    print(f"\n--- Extracción PDF: {os.path.basename(pdf_path)} ---")
    print(f"Titulación: {extraction_result.titulacion}")
    print(f"Tablas limpias: {len(extraction_result.clean_tables)}")
    parser = ScheduleParser()
    try:
        schedule = parser.parse(extraction_result)
        print(f"Sesiones parseadas: {len(schedule.sesiones)}")
        print(f"Warnings: {len(schedule.parse_metadata.warnings)}")
        print(f"Errores: {len(schedule.parse_metadata.errors)}")
        return schedule
    except Exception as e:
        print(f"Error en ScheduleParser: {e}")
        return None

def save_result(obj, outdir, pdf_path):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    # Guardar como texto plano (sesiones)
    outpath_txt = os.path.join(outdir, base + ".txt")
    with open(outpath_txt, "w", encoding="utf-8") as f:
        f.write(f"Titulación: {getattr(obj, 'titulacion', '')}\n")
        f.write("Día\tHora inicio\tHora fin\tAsignatura\tGrupo\tAula\tModalidad\n")
        for s in getattr(obj, "sesiones", []):
            f.write(f"{getattr(s, 'dia', '')}\t{getattr(s, 'hora_inicio', '')}\t{getattr(s, 'hora_fin', '')}\t"
                    f"{getattr(s, 'asignatura', '')}\t{getattr(s, 'grupo', '')}\t{getattr(s, 'aula', '')}\t"
                    f"{getattr(s, 'modalidad', '')}\n")
    print(f"Guardado resultado en: {outpath_txt}")
    # Guardar como JSON
    outpath_json = os.path.join(outdir, base + ".json")
    try:
        data = asdict(obj)
    except Exception:
        data = obj.__dict__
    with open(outpath_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Guardado resultado en: {outpath_json}")

def run_horario_parser(pdf_path):
    schedule = extract_and_parse_horario(pdf_path)
    if schedule:
        save_result(schedule, HORARIOS_OUTDIR, pdf_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parse_horario.py <ruta_horario.pdf>")
        sys.exit(1)
    horario_pdf = sys.argv[1]
    run_horario_parser(horario_pdf)