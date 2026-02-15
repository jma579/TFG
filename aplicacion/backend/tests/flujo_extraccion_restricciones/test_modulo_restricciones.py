"""
Tests integrales para el módulo de Restricciones.

Cubre:
1. CRUD manual de restricciones.
2. Ingesta masiva desde Excel (Drop & Load).
3. Transacciones atómicas (rollback automático en caso de errores en el Excel).
"""

import pytest
import pandas as pd
import io
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import time

# IMPORTANTE: Importamos el módulo de modelos al completo para que SQLAlchemy 
# registre TODAS las tablas (incluyendo restricciones) antes de crear la BD en memoria.
import database.models
from database.models import Base, Profesor, Restriccion

from db.session import get_db
from main import app
from constants.enums import DiaSemana

# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS EN MEMORIA (Aislada)
# ============================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="function")
def db():
    """Crea una base de datos nueva y limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Cliente de pruebas con la dependencia de BD inyectada."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def seed_profesores(db: Session):
    """Puebla la base de datos con profesores conocidos para el test."""
    profesores = [
        Profesor(nombre="Juan", apellidos="Pérez Gómez", email="juan@test.com", activo=True),
        Profesor(nombre="Ana", apellidos="García", email="ana@test.com", activo=True)
    ]
    db.add_all(profesores)
    db.commit()
    for p in profesores:
        db.refresh(p)
    return profesores

def crear_excel_en_memoria(datos: list) -> bytes:
    """Genera un archivo Excel en bytes a partir de un diccionario de datos."""
    df = pd.DataFrame(datos)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Restricciones')
    return output.getvalue()

# ============================================================
# TESTS DE CRUD MANUAL
# ============================================================

def test_crear_restriccion_manual(client: TestClient, seed_profesores):
    profesor_id = seed_profesores[0].id
    payload = {
        "dia_semana": "lunes",
        "hora_inicio": "08:00:00",
        "hora_fin": "10:00:00"
    }
    
    response = client.post(f"/v0/recursos/profesores/{profesor_id}/restricciones", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["dia_semana"] == "lunes"
    assert data["profesor_id"] == profesor_id

def test_crear_restriccion_manual_horas_invalidas(client: TestClient, seed_profesores):
    profesor_id = seed_profesores[0].id
    payload = {
        "dia_semana": "martes",
        "hora_inicio": "15:00:00",
        "hora_fin": "10:00:00" # Fin antes que inicio
    }
    
    response = client.post(f"/v0/recursos/profesores/{profesor_id}/restricciones", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

# ============================================================
# TESTS DE IMPORTACIÓN EXCEL
# ============================================================

def test_importacion_excel_exitosa(client: TestClient, seed_profesores, db: Session):
    """Prueba el Drop & Load con un Excel perfecto."""
    # 1. Creamos una restricción antigua (debe ser borrada por el Drop & Load)
    client.post(f"/v0/recursos/profesores/{seed_profesores[0].id}/restricciones", json={
        "dia_semana": "sabado", "hora_inicio": "08:00:00", "hora_fin": "14:00:00"
    })

    # 2. Generamos el Excel con datos nuevos
    datos_excel = [
        {"Profesor": "Juan Pérez Gómez", "Días": "L, M", "Franja": "09:00-11:00"},
        {"Profesor": "Ana García", "Días": "X", "Franja": "15:00-20:00"}
    ]
    excel_bytes = crear_excel_en_memoria(datos_excel)

    # 3. Enviamos el archivo
    files = {"file": ("restricciones.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = client.post("/v0/recursos/restricciones/importar", files=files)
    
    # 4. Validar respuesta
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["registros_creados"] == 3 # Juan L, Juan M, Ana X
    assert data["registros_eliminados"] == 1 # La del sábado que creamos arriba

def test_importacion_excel_falla_atomicamente(client: TestClient, seed_profesores, db: Session):
    """
    Prueba que si un profesor no existe, la base de datos aborta y NO borra los datos antiguos.
    """
    # 1. Creamos una restricción válida existente
    client.post(f"/v0/recursos/profesores/{seed_profesores[0].id}/restricciones", json={
        "dia_semana": "jueves", "hora_inicio": "10:00:00", "hora_fin": "12:00:00"
    })

    # 2. Generamos el Excel con un profesor INVENTADO (no está en BD)
    datos_excel = [
        {"Profesor": "Juan Pérez Gómez", "Días": "L", "Franja": "09:00-11:00"}, # Existe
        {"Profesor": "Profesor Fantasma", "Días": "X", "Franja": "15:00-20:00"} # NO EXISTE
    ]
    excel_bytes = crear_excel_en_memoria(datos_excel)

    # 3. Enviamos el archivo
    files = {"file": ("restricciones_fail.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = client.post("/v0/recursos/restricciones/importar", files=files)
    
    # 4. Validar que la API rechazó el archivo
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_detail = response.json()["detail"]
    assert "errores" in error_detail
    assert any("Profesor Fantasma" in error for error in error_detail["errores"])

    # 5. VALIDACIÓN CRÍTICA DE NEGOCIO: 
    # Asegurarnos de que el `delete_all()` NO se ejecutó y la restricción del Jueves sigue ahí.
    res_get = client.get(f"/v0/recursos/profesores/{seed_profesores[0].id}/restricciones")
    assert res_get.status_code == 200
    assert len(res_get.json()) == 1
    assert res_get.json()[0]["dia_semana"] == "jueves"