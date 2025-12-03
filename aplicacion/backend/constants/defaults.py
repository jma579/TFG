"""
Constantes y valores por defecto para la aplicación.
Centraliza valores hardcodeados para facilitar mantenimiento.
"""

# ============================
# API Configuration Defaults
# ============================
DEFAULT_API_TITLE = "Sistema de Detección de Conflictos en Horarios Académicos"
DEFAULT_API_DESCRIPTION = (
    "Backend para gestión de catálogo académico y detección automática de conflictos"
)
DEFAULT_API_VERSION = "1.0.0"
DEFAULT_API_PREFIX = "/v0"

# ============================
# Network Configuration
# ============================
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# CORS - Development origins
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server  
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]

DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
DEFAULT_CORS_HEADERS = ["*"]

# ============================
# Logging
# ============================
DEFAULT_LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================
# Database Configuration
# ============================
# BD de desarrollo (por defecto):
# - La URL es relativa al directorio base_dir (= backend/)
# - "../database/database.db" hace que la ruta física sea:
#   D:\TFG\aplicacion\database\database.db
# - En producción se debe usar DATABASE_URL en .env / variables de entorno
DEFAULT_DATABASE_URL = "sqlite:///../database/database.db"
DEFAULT_DB_POOL_SIZE = 10
DEFAULT_DB_POOL_TIMEOUT = 30

# ============================
# File Processing
# ============================
DEFAULT_MAX_FILE_SIZE_MB = 50
DEFAULT_UPLOAD_DIRECTORY = "uploads"
DEFAULT_ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]

# ============================
# OCR/NLP Configuration
# ============================
DEFAULT_SPACY_MODEL = "es_core_news_sm"

# ============================
# Conflict Detection
# ============================
DEFAULT_CONFLICT_CACHE_TTL = 300  # 5 minutes in seconds
DEFAULT_MAX_CONFLICTS_PER_SESSION = 100

# ============================
# Pagination
# ============================
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ============================
# Application Behavior
# ============================
DEFAULT_DEBUG_MODE = True
DEFAULT_TESTING_MODE = False
DEFAULT_RELOAD_MODE = True
DEFAULT_CONFLICT_DETECTION_ENABLED = True
