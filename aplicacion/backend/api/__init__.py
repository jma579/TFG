from .v0.grado import router as grado_router
from .v0.mencion import router as mencion_router
from .v0.asignatura import router as asignatura_router
from .v0.profesor import router as profesor_router
from .v0.aula import router as aula_router
from .v0.sesion import router as sesion_router
from .v0.restriccion import router as restriccion_router

__all__ = [
    "grado_router",
    "mencion_router", 
    "asignatura_router",
    "profesor_router",
    "aula_router",
    "sesion_router",
    "restriccion_router"
]
