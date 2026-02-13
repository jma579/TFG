from functools import lru_cache
from pathlib import Path
from typing import Optional, List

from pydantic import field_validator
from pydantic_settings import BaseSettings

from constants.defaults import (
    DEFAULT_API_TITLE, DEFAULT_API_DESCRIPTION, DEFAULT_API_VERSION, DEFAULT_API_PREFIX,
    DEFAULT_HOST, DEFAULT_PORT, DEFAULT_CORS_ORIGINS, DEFAULT_CORS_METHODS, 
    DEFAULT_CORS_HEADERS, DEFAULT_LOG_LEVEL, DEFAULT_DATABASE_URL,
    DEFAULT_DB_POOL_SIZE, DEFAULT_DB_POOL_TIMEOUT, DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_UPLOAD_DIRECTORY, DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_SPACY_MODEL,
    DEFAULT_CONFLICT_CACHE_TTL, DEFAULT_MAX_CONFLICTS_PER_SESSION,
    DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, DEFAULT_DEBUG_MODE, DEFAULT_TESTING_MODE,
    DEFAULT_RELOAD_MODE, DEFAULT_CONFLICT_DETECTION_ENABLED
)


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando pydantic-settings.
    
    Prioridad: Environment Variables > .env file > Default values
    """
    
    # Base de datos
    database_url: str = DEFAULT_DATABASE_URL
    database_echo: bool = False 
    database_pool_size: int = DEFAULT_DB_POOL_SIZE
    database_pool_timeout: int = DEFAULT_DB_POOL_TIMEOUT
    database_url_readonly: Optional[str] = None 
    
    # API
    api_title: str = DEFAULT_API_TITLE
    api_description: str = DEFAULT_API_DESCRIPTION
    api_version: str = DEFAULT_API_VERSION
    api_v0_prefix: str = DEFAULT_API_PREFIX
    
    # CORS
    cors_origins: List[str] = DEFAULT_CORS_ORIGINS
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = DEFAULT_CORS_METHODS
    cors_allow_headers: List[str] = DEFAULT_CORS_HEADERS
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """Permite definir CORS_ORIGINS como string separado por comas."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
    
    # Configuración de Aplicación
    debug: bool = DEFAULT_DEBUG_MODE
    testing: bool = DEFAULT_TESTING_MODE
    log_level: str = DEFAULT_LOG_LEVEL 
    app_host: str = DEFAULT_HOST
    app_port: int = DEFAULT_PORT
    reload: bool = DEFAULT_RELOAD_MODE 
    
    # OCR y procesamiento de documentos
    tesseract_cmd: Optional[str] = None
    spacy_model: str = DEFAULT_SPACY_MODEL
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    allowed_file_extensions: List[str] = DEFAULT_ALLOWED_EXTENSIONS
    upload_directory: str = DEFAULT_UPLOAD_DIRECTORY
    
    @field_validator("allowed_file_extensions", mode="after")
    @classmethod
    def _normalize_file_extensions(cls, exts: List[str]) -> List[str]:
        """Normaliza extensiones: asegura que empiecen con '.' y sean minúsculas"""
        normalized = []
        for ext in exts:
            ext_clean = ext.lower().strip()
            if not ext_clean.startswith("."):
                ext_clean = f".{ext_clean}"
            normalized.append(ext_clean)
        return normalized
    
    # Detección de Conflictos
    conflict_detection_enabled: bool = DEFAULT_CONFLICT_DETECTION_ENABLED
    conflict_cache_ttl_seconds: int = DEFAULT_CONFLICT_CACHE_TTL  
    max_conflicts_per_session: int = DEFAULT_MAX_CONFLICTS_PER_SESSION  
    
    # Paginación
    default_page_size: int = DEFAULT_PAGE_SIZE
    max_page_size: int = MAX_PAGE_SIZE
    
    @property
    def base_dir(self) -> Path:
        """Directorio base del proyecto (aplicacion/backend/)."""
        return Path(__file__).resolve().parent.parent
    
    @property
    def upload_path(self) -> Path:
        """Path completo del directorio de uploads."""
        return self.base_dir / self.upload_directory
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False, 
        "extra": "ignore"  
    }


@lru_cache
def get_settings() -> Settings:
    """
    Factory function con cache para obtener configuración.
    
    Returns:
        Settings: Instancia única de configuración
    """
    return Settings()


settings = get_settings()