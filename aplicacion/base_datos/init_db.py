from sqlalchemy import create_engine
from models import Base
import os
from inspect_db import inspect_database

# Obtiene el directorio actual del script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construye la ruta completa para la base de datos
db_path = os.path.join(current_dir, 'dev.db')
# Crea la conexión con la ruta absoluta
engine = create_engine(f'sqlite:///{db_path}', echo=True)

# Crea las tablas si no existen
Base.metadata.create_all(engine)

print(f"Base de datos creada correctamente en: {db_path}")

# Generar el esquema automáticamente
inspect_database()
