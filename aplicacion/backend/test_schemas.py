from schemas.grado import GradoCreate, GradoOut
from schemas.profesor import ProfesorCreate
import json

def test_grado():
    try:
        grado = GradoCreate(nombre="Grado en Ingeniería Informática")
        print("✅ Grado válido:", grado)
    except Exception as e:
        print("❌ Error en GradoCreate:", e)

def test_profesor():
    try:
        disponibilidad_json = {"lunes": ["10:00-12:00"], "martes": []}
        profesor = ProfesorCreate(nombre="María Pérez", disponibilidad=disponibilidad_json)
        print("✅ Profesor válido:", profesor)
    except Exception as e:
        print("❌ Error en ProfesorCreate:", e)

def test_profesor_error():
    try:
        profesor = ProfesorCreate(nombre="Juan", disponibilidad="no es un JSON")
    except Exception as e:
        print("✅ Error detectado correctamente:", e)

if __name__ == "__main__":
    test_grado()
    test_profesor()
    test_profesor_error()
