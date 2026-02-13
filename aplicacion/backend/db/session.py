"""
Configuración de sesiones de SQLAlchemy para FastAPI.

Este módulo maneja:
- Conexión a la base de datos
- Pool de conexiones
- Session factory para dependency injection
- Gestión del ciclo de vida de sesiones (session-per-request)
"""

import sys
from typing import Generator
from pathlib import Path
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config.settings import get_settings

settings = get_settings()


def create_database_engine() -> Engine:
    """
    Crea y configura el engine de SQLAlchemy.
    
    Configuración diferenciada por tipo de base de datos:
    - SQLite: Configuración específica para desarrollo
    - PostgreSQL: Pool de conexiones para producción
    
    Returns:
        Engine: Motor de base de datos configurado
    """
    connect_args = {}
    engine_kwargs = {
        "echo": settings.database_echo,
    }
    
    database_url = settings.database_url
    if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:///:memory:"):
        relative_path = database_url.replace("sqlite:///", "")
        if not relative_path.startswith("/"):
            absolute_path = settings.base_dir / relative_path
            database_url = f"sqlite:///{absolute_path.resolve()}"
    
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in database_url or settings.testing:
            engine_kwargs["poolclass"] = StaticPool
            connect_args["check_same_thread"] = False
    
    elif database_url.startswith("postgresql"):
        engine_kwargs.update({
            "pool_size": settings.database_pool_size,
            "pool_timeout": settings.database_pool_timeout,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        })
    
    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


engine = create_database_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency provider para FastAPI que gestiona sesiones de base de datos.
    
    Implementa el patrón session-per-request:
    1. Crea una nueva sesión para cada request
    2. La yielda al endpoint
    3. La cierra automáticamente al finalizar
    4. Maneja rollback en caso de excepción
    
    Yields:
        Session: Sesión de SQLAlchemy lista para usar
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_readonly() -> Generator[Session, None, None]:
    """
    Dependency provider para operaciones de solo lectura.
    
    Actualmente usa la misma DB que escritura.
    Cuando se configure réplica de solo lectura, usar engine dedicado.
    
    Yields:
        Session: Sesión de SQLAlchemy para lectura
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _import_base():
    """Import helper para Base con fallback."""
    try:
        from database.models import Base
        return Base
    except ImportError:
        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root))
        from database.models import Base
        return Base


def create_tables():
    """
    Crea todas las tablas definidas en los modelos.
    
    Útil para setup inicial de desarrollo y tests.
    En producción, usar Alembic para migraciones.
    """
    Base = _import_base()
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Elimina todas las tablas de la base de datos.
    
    PELIGRO: Solo usar en desarrollo/testing.
    """
    Base = _import_base()
    Base.metadata.drop_all(bind=engine)


def get_db_info() -> dict:
    """
    Obtiene información sobre la configuración de la base de datos.
    
    Returns:
        dict: Información de la configuración de DB
    """
    db_url = settings.database_url
    if "@" in db_url:
        db_url = db_url.split("@")[-1]
    
    return {
        "database_url": db_url,
        "echo": settings.database_echo,
        "pool_size": getattr(settings, 'database_pool_size', 'N/A'),
        "pool_timeout": getattr(settings, 'database_pool_timeout', 'N/A'),
        "testing_mode": settings.testing,
        "engine_info": {
            "name": engine.name,
            "driver": engine.driver,
        }
    }


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Error de conexión a la base de datos: {e}")
        return False