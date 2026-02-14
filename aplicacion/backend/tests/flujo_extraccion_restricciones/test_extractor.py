import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from core.extraccion.restricciones.extractor import get_restricciones_extractor

def test():
    extractor = get_restricciones_extractor()
    resultado = extractor.extract_from_excel("docs\\Ejemplo restricciones.xlsx")
    
    print(f"\nÉxito de extracción: {resultado.success}")
    print(f"Calidad: {resultado.metadata.quality.value}")
    print(f"Warnings generados: {len(resultado.metadata.warnings)}")
    
    for w in resultado.metadata.warnings:
        print(f" - [WARNING]: {w.message}")

    print("\n--- FILAS EXTRAÍDAS ---")
    for fila in resultado.filas_crudas:
        print(f"Fila {fila.fila_excel} | Prof: '{fila.profesor}' | Días: '{fila.dias}' | Franja: '{fila.franja}'")

if __name__ == "__main__":
    test()