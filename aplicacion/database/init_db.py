from database.models import Base
from db.session import engine
from database.inspect_db import inspect_database


def init_db() -> None:
    """
    Inicializa la base de datos de acuerdo al modelo SQLAlchemy:

    - Crea las tablas que no existan (no borra datos ni recrea el esquema).
    - Usa el mismo engine que el backend (backend.db.session.engine).
    - Está pensado para entornos donde no se ejecuta create_tables() en el startup.
    """
    Base.metadata.create_all(bind=engine)
    print(f"Base de datos inicializada en: {engine.url}")


def main() -> None:
    """
    Punto de entrada del script de inicialización en desarrollo.
    """
    init_db()
    # Generar el esquema de la base de datos para inspección manual
    inspect_database()


if __name__ == "__main__":
    main()
