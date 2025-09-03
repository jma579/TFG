import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configuración de la aplicación
    APP_NAME: str = "TFG - Sistema de Detección de Conflictos en Horarios"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    
    # Configuración de base de datos
    DATABASE_URL: str | None = None
    
    # Configuración específica para SQLite
    SQLITE_DB_NAME: str = "dev.db"
    
    # Configuración para PostgreSQL (producción)
    POSTGRES_USER: str = "tfg_user"
    POSTGRES_PASSWORD: str = "tfg_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "tfg_db"
    
    # Configuración de archivos
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Configuración de OCR
    TESSERACT_PATH: str = ""  # Se configurará según el sistema
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = self._get_database_url()
    
    def _get_database_url(self) -> str:
        """Construye la URL de la base de datos según el entorno"""
        if self.DEBUG:
            # Desarrollo: SQLite con ruta absoluta
            # Subir dos niveles desde backend/ para llegar a TFG/
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "aplicacion" / "base_datos" / self.SQLITE_DB_NAME
            return f"sqlite:///{db_path.absolute()}"
        else:
            # Producción: PostgreSQL
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
    
    @property
    def is_sqlite(self) -> bool:
        """Verifica si se está usando SQLite"""
        return self.DATABASE_URL.startswith("sqlite")

settings = Settings()