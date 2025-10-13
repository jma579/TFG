from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api import (
    grado_router, mencion_router, asignatura_router,
    profesor_router, aula_router, sesion_router, restriccion_router
)

# Configuración de la aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API REST para el sistema de detección de conflictos en horarios académicos",
    debug=settings.DEBUG
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(grado_router)
app.include_router(mencion_router)
app.include_router(asignatura_router)
app.include_router(profesor_router)
app.include_router(aula_router)
app.include_router(sesion_router)
app.include_router(restriccion_router)

# Endpoint de health check
@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "database": "SQLite" if settings.is_sqlite else "PostgreSQL"
    }

