from fastapi import FastAPI
from api import (
    grado_router, mencion_router, asignatura_router,
    profesor_router, aula_router, sesion_router, restriccion_router
)

app = FastAPI()

app.include_router(grado_router)
app.include_router(mencion_router)
app.include_router(asignatura_router)
app.include_router(profesor_router)
app.include_router(aula_router)
app.include_router(sesion_router)
app.include_router(restriccion_router)

