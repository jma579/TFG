from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import Engine
import sqlite3
import logging
from config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración específica para SQLite
def _sqlite_configure(dbapi_connection, connection_record):
    """Configuración específica para SQLite"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Habilitar claves foráneas en SQLite
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Configurar argumentos de conexión según el tipo de BD
connect_args = {}
if settings.is_sqlite:
    connect_args = {"check_same_thread": False}
    logger.info(f"Configurando SQLite: {settings.DATABASE_URL}")
else:
    logger.info(f"Configurando PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")

# Crear el motor
try:
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args=connect_args,
        echo=settings.DEBUG,  # Mostrar queries SQL en desarrollo
        pool_pre_ping=True,   # Verificar conexiones antes de usar
    )
    
    # Configurar SQLite si es necesario
    if settings.is_sqlite:
        event.listen(engine, "connect", _sqlite_configure)
    
    logger.info("Motor de base de datos creado exitosamente")
    
except Exception as e:
    logger.error(f"Error al crear el motor de base de datos: {e}")
    raise

# Crear la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos ORM
Base = declarative_base()

# Función para obtener una sesión de base de datos
def get_db():
    """Dependencia para obtener una sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en la sesión de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()