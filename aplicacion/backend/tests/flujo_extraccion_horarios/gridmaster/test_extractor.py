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
    from core.extraccion.horarios.extractor import HorarioExtractor
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
logger = logging.getLogger("BatchTest")

# =============================================================================
# 4. UTILS SERIALIZACIÓN JSON
# =============================================================================
def json_serial(obj):
    if isinstance(obj, (datetime, time)):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

# =============================================================================
# 5. FUNCIÓN DE EXTRACCIÓN INDIVIDUAL
# =============================================================================
def process_file(pdf_path: Path, output_base_dir: Path, extractor: HorarioExtractor):
    print(f"\n{'='*60}")
    print(f"📄 PROCESANDO: {pdf_path.name}")
    print(f"{'='*60}")

    start_time = datetime.now()
    try:
        # Ejecutar Extracción
        result = extractor.extract(str(pdf_path))
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Resumen en consola
        print(f"✅ Extracción completada en {duration:.2f}s")
        print(f"   - Título: {result.titulo}")
        print(f"   - Tablas: {len(result.tablas)}")
        print(f"   - Calidad: {result.metadata.quality}")
        
        # Guardar JSON
        json_filename = f"{pdf_path.stem}_output.json"
        output_path = output_base_dir / json_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            data_dict = asdict(result)
            json.dump(data_dict, f, indent=4, ensure_ascii=False, default=json_serial)
            
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
    INPUT_DIR = Path(r"C:\Users\usuario\TFG\Horarios\Grado")
    OUTPUT_DIR = current_file.parent / "extraction_result"
    
    # Crear directorio de salida si no existe
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_DIR.exists():
        print(f"❌ El directorio de entrada no existe: {INPUT_DIR}")
        sys.exit(1)

    # Buscar todos los PDFs
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No se encontraron archivos .pdf en {INPUT_DIR}")
        sys.exit(0)

    print(f"\n🚀 INICIANDO PROCESO BATCH - GRIDMASTER")
    print(f"📂 Directorio Entrada: {INPUT_DIR}")
    print(f"📂 Directorio Salida:  {OUTPUT_DIR}")
    print(f"📦 Archivos a procesar: {len(pdf_files)}")

    # Instanciar extractor una sola vez (más eficiente)
    extractor = HorarioExtractor()
    
    success_count = 0
    errors = []

    for pdf_file in pdf_files:
        if process_file(pdf_file, OUTPUT_DIR, extractor):
            success_count += 1
        else:
            errors.append(pdf_file.name)

    # --- RESUMEN FINAL ---
    print(f"\n{'#'*60}")
    print(f"🏁 RESUMEN FINAL DEL PROCESO")
    print(f"{'#'*60}")
    print(f"Total Archivos: {len(pdf_files)}")
    print(f"✅ Éxitos:       {success_count}")
    print(f"❌ Fallos:       {len(errors)}")
    
    if errors:
        print("\nArchivos con errores:")
        for err in errors:
            print(f" - {err}")
    
    print(f"\nLos resultados JSON están en:\n-> {OUTPUT_DIR}")