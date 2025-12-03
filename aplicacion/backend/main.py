"""
Punto de entrada principal de la aplicación FastAPI.

Sistema de Detección de Conflictos Académicos - Backend API.
Configura la aplicación, middlewares, exception handlers y health checks.
"""

from datetime import datetime, timezone
from typing import Dict, Any
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from backend.config.settings import get_settings
from backend.db.session import engine, create_tables

from backend.modules.catalogo.api.routers import router as catalogo_router
from backend.modules.recursos.api.routers import router as recursos_router
from backend.modules.docencia.api.routers import router as docencia_router
from backend.modules.conflictos.api.routers import router as conflictos_router

# Obtener configuración
settings = get_settings()

# Configurar logging dinámicamente
log_level_mapping = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
logging.basicConfig(
    level=log_level_mapping.get(settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Se ejecuta al inicio y al cierre de la aplicación.
    """
    # Startup
    logger.info("🚀 Iniciando Sistema de Detección de Conflictos Académicos")
    
    try:
        # Verificar conexión a base de datos (sin mostrar credenciales)
        logger.info(f"📊 Conectando a base de datos: {engine.name} ({engine.driver})")
        
        # Crear directorios necesarios
        upload_path = settings.upload_path
        upload_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Directorio de uploads verificado: {upload_path}")
        
        # Inicializar esquema de base de datos (solo en desarrollo).
        # create_tables() usa Base.metadata.create_all(), que es idempotente:
        # crea tablas que no existan y nunca borra datos ni recrea tablas.
        if settings.debug:
            create_tables()
            logger.info("✅ Tablas de base de datos verificadas/creadas (entorno debug)")
        else:
            logger.info(
                "ℹ️ Entorno no debug: se asume que la base de datos ya está "
                "inicializada y no se ejecuta create_tables() automáticamente"
            )
            
    except Exception as e:
        logger.error(f"❌ Error en startup: {e}")
        raise
    
    yield  # Aquí la aplicación está corriendo
    
    # Shutdown
    logger.info("🔄 Cerrando aplicación...")


# Crear instancia de FastAPI
app = FastAPI(
    title="Sistema de Detección de Conflictos Académicos",
    description=(
        "API REST para la gestión académica y detección automatizada "
        "de conflictos en horarios universitarios. "
        "\n\nIncluye módulos para catálogo de programas, gestión de recursos, "
        "docencia y sistema inteligente de detección de conflictos."
    ),
    version="1.0.0",
    contact={
        "name": "TFG - Universidad",
        "email": "soporte@universidad.edu"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    # Solo mostrar docs en desarrollo
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# ============================
# Middlewares
# ============================

# CORS - Configuración desde settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# ============================
# Exception Handlers
# ============================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler personalizado para excepciones HTTP."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para errores de validación de Pydantic con serialización segura.
    
    Convierte todos los errores a tipos serializables a JSON,
    manejando correctamente objetos ValueError en ctx['error'].
    """
    # Serializar errores de forma segura
    serializable_errors = []
    for error in exc.errors():
        serialized_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": str(error.get("input")) if error.get("input") is not None else None,
        }
        
        # Serializar el contexto si existe
        if "ctx" in error and error["ctx"]:
            serialized_ctx = {}
            for key, value in error["ctx"].items():
                # Si es un ValueError u otro objeto no serializable, convertir a string
                if isinstance(value, Exception):
                    serialized_ctx[key] = str(value)
                elif isinstance(value, (str, int, float, bool, type(None))):
                    serialized_ctx[key] = value
                else:
                    serialized_ctx[key] = str(value)
            serialized_error["ctx"] = serialized_ctx
        
        serializable_errors.append(serialized_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": serializable_errors,
            "status_code": 422,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler general para excepciones no capturadas."""
    logger.error(f"Excepción no manejada: {exc}", exc_info=True)
    
    # En producción, no mostrar detalles del error
    detail = str(exc) if settings.debug else "Error interno del servidor"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ============================
# Health Check & Info
# ============================

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health Check",
    description="Endpoint para verificar el estado de la API y sus dependencias"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check básico del sistema.
    Verifica el estado de la aplicación y sus componentes principales.
    """
    overall_status = "healthy"
    components = {}
    
    try:
        # Verificar conexión a base de datos
        with engine.connect() as conn:
            # Query simple para verificar conectividad (SQLAlchemy 2.0)
            conn.execute(text("SELECT 1"))
        components["database"] = "connected"
        
    except Exception as e:
        logger.error(f"Error en health check - DB: {e}")
        components["database"] = f"error: {str(e)}"
        overall_status = "degraded"
    
    components["api"] = "online"
    
    # Si hay errores críticos, devolver status HTTP 503
    status_code = 200 if overall_status == "healthy" else 503
    
    response_data = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": "development" if settings.debug else "production",
        "components": components
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


@app.get(
    "/",
    tags=["Sistema"],
    summary="Información de la API",
    description="Información básica sobre la API y enlaces útiles"
)
async def root() -> Dict[str, Any]:
    """Información básica de la API."""
    return {
        "message": "Sistema de Detección de Conflictos Académicos - API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "documentation": "/docs" if settings.debug else "No disponible en producción",
        "health_check": "/health"
    }

# ============================
# Inclusión de Routers (Preparado para futuras fases)
# ============================

# NOTA: Los siguientes routers se incluirán en fases posteriores:
# Usar el prefijo configurado en settings: settings.api_v0_prefix

# Fase 3: Módulos de Dominio
app.include_router(catalogo_router, prefix=f"{settings.api_v0_prefix}/catalogo", tags=["Catálogo"])
app.include_router(recursos_router, prefix=f"{settings.api_v0_prefix}/recursos", tags=["Recursos"])
app.include_router(docencia_router, prefix=f"{settings.api_v0_prefix}/docencia", tags=["Docencia"])

# from recursos.router import router as recursos_router  
# app.include_router(recursos_router, prefix=f"{settings.api_v0_prefix}/recursos", tags=["Recursos"])

# from docencia.router import router as docencia_router
# app.include_router(docencia_router, prefix=f"{settings.api_v0_prefix}/docencia", tags=["Docencia"])

# Fase 3: Sistema de Conflictos
# from conflictos.router import router as conflictos_router
app.include_router(conflictos_router, prefix=f"{settings.api_v0_prefix}/conflictos", tags=["Conflictos"])

# Fase 4: Ingesta y Procesamiento
# from ingesta.router import router as ingesta_router
# app.include_router(ingesta_router, prefix=f"{settings.api_v0_prefix}/ingesta", tags=["Ingesta"])

# ============================
# Configuración para desarrollo
# ============================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando servidor de desarrollo...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
