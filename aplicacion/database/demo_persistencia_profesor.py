from backend.db.session import SessionLocal
from database.models import Profesor


TEST_EMAIL = "persistencia@test.local"


def run_demo_persistencia() -> None:
    """Demostración manual de persistencia de datos en la BD de desarrollo.

    - Si no existe un profesor con TEST_EMAIL, lo crea.
    - Si ya existe, muestra sus datos.
    """
    db = SessionLocal()
    try:
        profesor = db.query(Profesor).filter_by(email=TEST_EMAIL).first()

        if profesor:
            print("✅ Profesor ya existente en BD:")
            print(f"   id={profesor.id}")
            print(f"   nombre={profesor.nombre} {profesor.apellidos}")
            print(f"   email={profesor.email}")
        else:
            profesor = Profesor(
                nombre="DEMO",
                apellidos="Persistencia",
                email=TEST_EMAIL,
                telefono="000000000",
                departamento="DEMO",
            )
            db.add(profesor)
            db.commit()
            db.refresh(profesor)
            print("🆕 Profesor creado en BD de desarrollo:")
            print(f"   id={profesor.id}")
            print(f"   nombre={profesor.nombre} {profesor.apellidos}")
            print(f"   email={profesor.email}")
    finally:
        db.close()


if __name__ == "__main__":
    run_demo_persistencia()
