from database import SessionLocal
from models import Grado, Profesor, Asignatura  # importa desde __init__.py

def probar_modelos():
    try:
        db = SessionLocal()
        print("✅ Conexión abierta. Intentando contar registros...")

        n_grados = db.query(Grado).count()
        n_profesores = db.query(Profesor).count()
        n_asignaturas = db.query(Asignatura).count()

        print(f"Grados: {n_grados}, Profesores: {n_profesores}, Asignaturas: {n_asignaturas}")
    except Exception as e:
        print("❌ Error al consultar los modelos:", e)
    finally:
        db.close()

if __name__ == "__main__":
    probar_modelos()
