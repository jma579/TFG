import sys
import os
from pathlib import Path
import logging
import json
from datetime import datetime, time
from dataclasses import asdict
import traceback

# =============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO (PATH)
# =============================================================================
current_file = Path(__file__).resolve()
backend_root = current_file.parents[3] 

if str(backend_root) not in sys.path:
    sys.path.append(str(backend_root))
    print(f"✅ Root añadido al PATH: {backend_root}")

# =============================================================================
# 2. IMPORTS DEL SISTEMA
# =============================================================================
try:
    from core.extraccion.horarios.extractor.extractor import HorarioExtractor
    from core.extraccion.horarios.parser.parser import HorarioParser
except ImportError as e:
    print(f"\n❌ CRITICAL ERROR: No se pudieron importar los módulos del Core.")
    print(f"Detalle: {e}")
    sys.exit(1)

# =============================================================================
# 3. CONFIGURACIÓN DE LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BatchPipelineTest")

# =============================================================================
# 4. UTILS SERIALIZACIÓN JSON
# =============================================================================
def json_serial(obj):
    if isinstance(obj, (datetime, time)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

# =============================================================================
# 5. FUNCIÓN DE PROCESAMIENTO INDIVIDUAL
# =============================================================================
def process_file(pdf_path: Path, output_base_dir: Path, extractor: HorarioExtractor, parser: HorarioParser):
    print(f"\n{'='*60}")
    print(f"📄 PROCESANDO: {pdf_path.name}")
    print(f"{'='*60}")

    try:
        # --- FASE 1: EXTRACCIÓN ---
        start_ext = datetime.now()
        extraction_result = extractor.extract(str(pdf_path))
        duration_ext = (datetime.now() - start_ext).total_seconds()
        
        logger.info(f"✅ Extracción: {duration_ext:.2f}s | Tablas: {len(extraction_result.tablas)}")

        if not extraction_result.tablas:
            logger.warning("⚠️ Sin tablas detectadas. Saltando parseo.")
            return False

        # --- FASE 2: PARSEO ---
        start_parse = datetime.now()
        parsing_result = parser.parse(extraction_result)
        duration_parse = (datetime.now() - start_parse).total_seconds()
        
        # Estadísticas
        total_horarios = len(parsing_result.get("horarios", []))
        total_sesiones = sum(len(h.get("sesiones", [])) for h in parsing_result.get("horarios", []))
        
        logger.info(f"✅ Parseo:     {duration_parse:.2f}s | Sesiones: {total_sesiones}")
        print(f"   - Título: {parsing_result.get('titulo')}")

        # --- GUARDADO ---
        json_filename = f"{pdf_path.stem}_parsed.json"
        output_path = output_base_dir / json_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsing_result, f, indent=4, ensure_ascii=False, default=json_serial)
            
        print(f"💾 JSON guardado: {json_filename}")
        return True

    except Exception as e:
        logger.error(f"❌ Error procesando {pdf_path.name}: {str(e)}")
        traceback.print_exc()
        return False

# =============================================================================
# 6. MOTOR PRINCIPAL (BATCH)
# =============================================================================
if __name__ == "__main__":
    # --- CONFIGURACIÓN DE RUTAS ---
    INPUT_DIR = Path(r"D:\TFG\Horarios\Grado")
    OUTPUT_DIR = current_file.parent / "parsing_result"
    
    # Crear directorio si no existe
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_DIR.exists():
        print(f"❌ El directorio de entrada no existe: {INPUT_DIR}")
        sys.exit(1)

    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No se encontraron archivos .pdf en {INPUT_DIR}")
        sys.exit(0)

    print(f"\n🚀 INICIANDO PIPELINE COMPLETO (BATCH)")
    print(f"📂 Entrada: {INPUT_DIR}")
    print(f"📂 Salida:  {OUTPUT_DIR}")
    print(f"📦 Archivos: {len(pdf_files)}")

    # Instanciar componentes una sola vez
    extractor = HorarioExtractor()
    parser = HorarioParser()
    
    success_count = 0
    errors = []

    for pdf_file in pdf_files:
        if process_file(pdf_file, OUTPUT_DIR, extractor, parser):
            success_count += 1
        else:
            errors.append(pdf_file.name)

    # --- RESUMEN FINAL ---
    print(f"\n{'#'*60}")
    print(f"🏁 RESUMEN FINAL")
    print(f"{'#'*60}")
    print(f"Total Archivos: {len(pdf_files)}")
    print(f"✅ Éxitos:       {success_count}")
    print(f"❌ Fallos:       {len(errors)}")
    
    if errors:
        print("\nArchivos con errores:")
        for err in errors:
            print(f" - {err}")
    
    print(f"\nResultados en: {OUTPUT_DIR}")