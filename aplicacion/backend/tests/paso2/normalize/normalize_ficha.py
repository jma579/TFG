"""
Script de testing para normalización de fichas académicas.

Flujo completo:
1. Extraer texto del PDF (FichaExtractor)
2. Parsear a SubjectSheet (FichaParser)
3. Normalizar datos (DataNormalizer - SIN BD)

Salidas:
- fichas_normalizadas/<nombre>.txt (representación legible)
- fichas_normalizadas/<nombre>.json (JSON estructurado)

Uso:
    # Indicar PDF en línea de comandos
    python normalize_ficha.py <ruta_ficha.pdf>
    
    # O usar PDF por defecto en código
    python normalize_ficha.py

Ejemplo:
    python normalize_ficha.py "D:/PDFs/calculo1.pdf"
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ajustar path para imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core.extraccion.fichas.extractor import FichaExtractor
from core.extraccion.fichas.parser import FichaParser
from core.extraccion.fichas.normalize import DataNormalizer
from core.extraccion.fichas.entities import NormalizedFichaData

# ============================================================
#  CONFIGURACIÓN
# ============================================================

# Directorio de salida
FICHAS_OUTDIR = os.path.join(os.path.dirname(__file__), "fichas_normalizadas")

# PDF por defecto (si no se pasa por terminal)
DEFAULT_PDF = r"D:\TFG\Fichas\GRADO\G49.pdf"  


# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================

def extract_pdf_text(pdf_path: str):
    """
    Extraer texto del PDF usando FichaExtractor.
    
    Returns:
        Tupla (text, metadata) o None si falla
    """
    extractor = FichaExtractor()
    result = extractor.extract_from_pdf(pdf_path)
    
    if not result.success:
        print(f"❌ Error en extracción: {result.error_message}")
        return None
    
    if not result.is_usable:
        print(f"❌ Calidad insuficiente: {result.metadata.quality.value}")
        return None
    
    print(f"✅ Extracción exitosa")
    print(f"   Calidad: {result.metadata.quality.value}")
    print(f"   Confianza: {result.metadata.confidence:.2f}")
    print(f"   Páginas: {result.metadata.pages_processed}")
    
    return result.text, result.metadata


def parse_text(text: str, extraction_metadata):
    """
    Parsear texto a SubjectSheet usando FichaParser.
    
    Returns:
        SubjectSheet o None si falla
    """
    parser = FichaParser()
    
    try:
        ficha = parser.parse_text(text, extraction_metadata=extraction_metadata)
        
        print(f"✅ Parseo exitoso")
        print(f"   Código: {ficha.codigo_plan}")
        print(f"   Nombre: {ficha.nombre}")
        print(f"   ECTS: {ficha.ects}")
        print(f"   Titulaciones: {len(ficha.titulaciones)}")
        print(f"   Profesores: {len(ficha.profesores)}")
        
        return ficha
        
    except Exception as e:
        print(f"❌ Error en parseo: {e}")
        return None


def normalize_ficha(ficha):
    """
    Normalizar SubjectSheet usando DataNormalizer (SIN BD).
    
    Returns:
        NormalizedFichaData o None si falla
    """
    normalizer = DataNormalizer()
    
    try:
        normalized = normalizer.normalize_ficha_without_db(ficha)
        
        print(f"✅ Normalización exitosa")
        print(f"   Código normalizado: {normalized.asignatura.codigo_plan}")
        print(f"   Nombre normalizado: {normalized.asignatura.nombre}")
        print(f"   Periodo: {normalized.asignatura.periodo.value}")
        print(f"   Modalidad: {normalized.asignatura.modalidad.value}")
        print(f"   Idioma: {normalized.asignatura.idioma.value}")
        print(f"   Titulaciones normalizadas: {len(normalized.titulaciones)}")
        print(f"   Profesores normalizados: {len(normalized.profesores)}")
        
        # Verificar que no se detectaron duplicados (sin BD)
        assert normalized.asignatura.is_duplicate == False, "is_duplicate debería ser False (sin BD)"
        assert normalized.asignatura.existing_id is None, "existing_id debería ser None (sin BD)"
        
        return normalized
        
    except Exception as e:
        print(f"❌ Error en normalización: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_result_txt(normalized: NormalizedFichaData, outdir: str, pdf_path: str):
    """Guardar resultado como texto legible."""
    os.makedirs(outdir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    outpath = os.path.join(outdir, base + ".txt")
    
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("FICHA ACADÉMICA NORMALIZADA\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Archivo: {os.path.basename(pdf_path)}\n")
        f.write("=" * 80 + "\n\n")
        
        # ASIGNATURA
        f.write("ASIGNATURA\n")
        f.write("-" * 80 + "\n")
        f.write(f"Código Plan:       {normalized.asignatura.codigo_plan}\n")
        f.write(f"Nombre:            {normalized.asignatura.nombre}\n")
        f.write(f"Periodo:           {normalized.asignatura.periodo.value}\n")
        f.write(f"ECTS:              {normalized.asignatura.ects}\n")
        f.write(f"Modalidad:         {normalized.asignatura.modalidad.value}\n")
        f.write(f"Idioma:            {normalized.asignatura.idioma.value}\n")
        f.write(f"English Friendly:  {normalized.asignatura.english_friendly}\n")
        f.write(f"Es duplicado:      {normalized.asignatura.is_duplicate}\n")
        f.write(f"ID existente:      {normalized.asignatura.existing_id}\n")
        f.write("\n")
        
        # TITULACIONES
        f.write("TITULACIONES\n")
        f.write("-" * 80 + "\n")
        for i, tit in enumerate(normalized.titulaciones, 1):
            f.write(f"\n{i}. {tit.programa_nombre}\n")
            f.write(f"   Tipo:        {tit.tipo_asignatura.value}\n")
            f.write(f"   Curso:       {tit.curso}\n")
            f.write(f"   Programa ID: {tit.programa_id}\n")
        f.write("\n")
        
        # PROFESORES
        f.write("PROFESORES\n")
        f.write("-" * 80 + "\n")
        for i, prof in enumerate(normalized.profesores, 1):
            f.write(f"\n{i}. {prof.nombre} {prof.apellidos}\n")
            f.write(f"   Departamento:  {prof.departamento}\n")
            f.write(f"   Es duplicado:  {prof.is_duplicate}\n")
            f.write(f"   ID existente:  {prof.existing_id}\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
    
    print(f"📄 Guardado TXT: {outpath}")


def save_result_json(normalized: NormalizedFichaData, outdir: str, pdf_path: str):
    """Guardar resultado como JSON estructurado."""
    os.makedirs(outdir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    outpath = os.path.join(outdir, base + ".json")
    
    # Convertir a dict (Pydantic tiene .dict())
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_pdf": os.path.basename(pdf_path)
        },
        "asignatura": {
            "codigo_plan": normalized.asignatura.codigo_plan,
            "nombre": normalized.asignatura.nombre,
            "periodo": normalized.asignatura.periodo.value,
            "ects": normalized.asignatura.ects,
            "modalidad": normalized.asignatura.modalidad.value,
            "idioma": normalized.asignatura.idioma.value,
            "english_friendly": normalized.asignatura.english_friendly,
            "is_duplicate": normalized.asignatura.is_duplicate,
            "existing_id": normalized.asignatura.existing_id
        },
        "titulaciones": [
            {
                "programa_nombre": tit.programa_nombre,
                "tipo_asignatura": tit.tipo_asignatura.value,
                "curso": tit.curso,
                "programa_id": tit.programa_id
            }
            for tit in normalized.titulaciones
        ],
        "profesores": [
            {
                "nombre": prof.nombre,
                "apellidos": prof.apellidos,
                "departamento": prof.departamento,
                "is_duplicate": prof.is_duplicate,
                "existing_id": prof.existing_id
            }
            for prof in normalized.profesores
        ]
    }
    
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Guardado JSON: {outpath}")


# ============================================================
#  FLUJO PRINCIPAL
# ============================================================

def run_normalization(pdf_path: str):
    """
    Ejecutar flujo completo: Extraer → Parsear → Normalizar.
    
    Args:
        pdf_path: Ruta al PDF de la ficha
    """
    print("\n" + "=" * 80)
    print(f"PROCESANDO: {os.path.basename(pdf_path)}")
    print("=" * 80 + "\n")
    
    # 1. EXTRACCIÓN
    print("📄 [1/3] Extrayendo texto del PDF...")
    extraction_result = extract_pdf_text(pdf_path)
    if not extraction_result:
        print("\n❌ Flujo interrumpido: Fallo en extracción\n")
        return False
    
    text, extraction_metadata = extraction_result
    print()
    
    # 2. PARSEO
    print("🔍 [2/3] Parseando texto a estructura...")
    ficha = parse_text(text, extraction_metadata)
    if not ficha:
        print("\n❌ Flujo interrumpido: Fallo en parseo\n")
        return False
    print()
    
    # 3. NORMALIZACIÓN
    print("⚙️  [3/3] Normalizando datos (SIN BD)...")
    normalized = normalize_ficha(ficha)
    if not normalized:
        print("\n❌ Flujo interrumpido: Fallo en normalización\n")
        return False
    print()
    
    # GUARDAR RESULTADOS
    print("💾 Guardando resultados...")
    save_result_txt(normalized, FICHAS_OUTDIR, pdf_path)
    save_result_json(normalized, FICHAS_OUTDIR, pdf_path)
    
    print("\n" + "=" * 80)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("=" * 80 + "\n")
    
    return True


# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    # Determinar PDF a procesar
    if len(sys.argv) >= 2:
        pdf_path = sys.argv[1]
    else:
        print(f"ℹ️  No se especificó PDF, usando por defecto: {DEFAULT_PDF}")
        pdf_path = DEFAULT_PDF
    
    # Validar que existe
    if not os.path.exists(pdf_path):
        print(f"❌ ERROR: No se encuentra el archivo: {pdf_path}")
        sys.exit(1)
    
    # Ejecutar normalización
    success = run_normalization(pdf_path)
    
    sys.exit(0 if success else 1)