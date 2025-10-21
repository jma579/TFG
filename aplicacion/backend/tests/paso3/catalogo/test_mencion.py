"""
Tests completos para el módulo Mencion.

Estructura:
- TestMencionSchemas: Validaciones Pydantic
- TestMencionRepository: Operaciones de base de datos
- TestMencionService: Lógica de negocio
- TestMencionRouter: Endpoints REST API

Fixtures:
- db_session: Sesión de base de datos para tests
- client: Cliente de test de FastAPI
- sample_programa: Programa de ejemplo
- sample_mencion: Mención de ejemplo
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base
from backend.db.session import get_db
from backend.main import app
from backend.modules.catalogo.schemas.mencion import (
    MencionCreate, MencionUpdate, MencionOut
)
from backend.modules.catalogo.repositories.mencion_repo import mencion_repository
from backend.modules.catalogo.services.mencion_service import mencion_service
from backend.constants.enums import TipoPrograma

# Configuración de base de datos de pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_catalogo_mencion.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db_session():
    """Crear sesión de base de datos para cada test, con rollback al final."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture()
def client(db_session):
    """Cliente de test con sesión de base de datos aislada."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture()
def sample_programa(db_session):
    from backend.modules.catalogo.repositories.programa_repo import programa_repository
    data = {
        "nombre": "Grado en Informática",
        "tipo": TipoPrograma.GRADO,
        "activo": True
    }
    programa = programa_repository.create(db_session, data)
    return programa

@pytest.fixture()
def sample_mencion(db_session, sample_programa):
    data = {
        "programa_id": sample_programa.id,
        "nombre": "Ingeniería del Software",
        "activo": True
    }
    mencion = mencion_repository.create(db_session, data)
    return mencion

# =========================
# TestMencionSchemas
# =========================

class TestMencionSchemas:
    def test_create_schema_valid(self):
        data = {
            "programa_id": 1,
            "nombre": "Inteligencia Artificial",
            "activo": True
        }
        schema = MencionCreate(**data)
        assert schema.programa_id == 1
        assert schema.nombre == "Inteligencia Artificial"
        assert schema.activo is True

    def test_nombre_normalization(self):
        data = {
            "programa_id": 1,
            "nombre": "  IA   y   Robótica  ",
            "activo": True
        }
        schema = MencionCreate(**data)
        assert schema.nombre == "IA y Robótica"

    def test_nombre_length(self):
        with pytest.raises(ValueError):
            MencionCreate(programa_id=1, nombre="", activo=True)
        with pytest.raises(ValueError):
            MencionCreate(programa_id=1, nombre="A"*201, activo=True)

    def test_programa_id_gt_0(self):
        with pytest.raises(ValueError):
            MencionCreate(programa_id=0, nombre="IA", activo=True)

    def test_update_schema_partial(self):
        schema = MencionUpdate(nombre="Computación")
        assert schema.nombre == "Computación"
        assert schema.programa_id is None

    def test_update_schema_normalization(self):
        schema = MencionUpdate(nombre="  Sistemas  Inteligentes  ")
        assert schema.nombre == "Sistemas Inteligentes"

    def test_out_schema_from_orm(self, sample_mencion):
        out = MencionOut.model_validate(sample_mencion)
        assert out.id == sample_mencion.id
        assert out.nombre == sample_mencion.nombre

# =========================
# TestMencionRepository
# =========================

class TestMencionRepository:
    def test_create_and_get_by_id(self, db_session, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "Robótica",
            "activo": True
        }
        mencion = mencion_repository.create(db_session, data)
        fetched = mencion_repository.get_by_id(db_session, mencion.id)
        assert fetched is not None
        assert fetched.nombre == "Robótica"

    def test_get_by_programa_nombre(self, db_session, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        mencion = mencion_repository.create(db_session, data)
        fetched = mencion_repository.get_by_programa_nombre(db_session, sample_programa.id, "IA")
        assert fetched is not None
        assert fetched.id == mencion.id

    def test_get_multi_filters(self, db_session, sample_programa):
        mencion_repository.create(db_session, {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        })
        mencion_repository.create(db_session, {
            "programa_id": sample_programa.id,
            "nombre": "Robótica",
            "activo": False
        })
        menciones, total = mencion_repository.get_multi(db_session, programa_id=sample_programa.id, activo=True)
        assert total >= 1
        for m in menciones:
            assert m.activo is True

    def test_update(self, db_session, sample_mencion):
        update_data = {"nombre": "Software Avanzado"}
        updated = mencion_repository.update(db_session, sample_mencion.id, update_data)
        assert updated.nombre == "Software Avanzado"

    def test_delete_soft(self, db_session, sample_mencion):
        result = mencion_repository.delete(db_session, sample_mencion.id)
        assert result is True
        mencion = mencion_repository.get_by_id(db_session, sample_mencion.id)
        assert mencion.activo is False

    def test_exists_by_programa_nombre(self, db_session, sample_programa):
        mencion_repository.create(db_session, {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        })
        exists = mencion_repository.exists_by_programa_nombre(db_session, sample_programa.id, "IA")
        assert exists is True

    def test_exists_by_programa_nombre_exclude_id(self, db_session, sample_programa):
        mencion = mencion_repository.create(db_session, {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        })
        exists = mencion_repository.exists_by_programa_nombre(db_session, sample_programa.id, "IA", exclude_id=mencion.id)
        assert exists is False

# =========================
# TestMencionService
# =========================

class TestMencionService:
    def test_create_mencion_success(self, db_session, sample_programa):
        data = MencionCreate(programa_id=sample_programa.id, nombre="IA", activo=True)
        out = mencion_service.create_mencion(db_session, data)
        assert out.nombre == "IA"
        assert out.programa_id == sample_programa.id

    def test_create_mencion_programa_not_found(self, db_session):
        data = MencionCreate(programa_id=999, nombre="IA", activo=True)
        with pytest.raises(Exception) as exc:
            mencion_service.create_mencion(db_session, data)
        assert "Programa con ID 999 no encontrado" in str(exc.value)

    def test_create_mencion_duplicate(self, db_session, sample_programa):
        data = MencionCreate(programa_id=sample_programa.id, nombre="IA", activo=True)
        mencion_service.create_mencion(db_session, data)
        with pytest.raises(Exception) as exc:
            mencion_service.create_mencion(db_session, data)
        assert "Ya existe una mención" in str(exc.value)

    def test_update_mencion_success(self, db_session, sample_mencion):
        update = MencionUpdate(nombre="Software Avanzado")
        out = mencion_service.update_mencion(db_session, sample_mencion.id, update)
        assert out.nombre == "Software Avanzado"

    def test_update_mencion_not_found(self, db_session):
        update = MencionUpdate(nombre="Software Avanzado")
        with pytest.raises(Exception) as exc:
            mencion_service.update_mencion(db_session, 999, update)
        assert "Mención con ID 999 no encontrada" in str(exc.value)

    def test_update_mencion_duplicate(self, db_session, sample_programa, sample_mencion):
        data = MencionCreate(programa_id=sample_programa.id, nombre="IA", activo=True)
        mencion_service.create_mencion(db_session, data)
        update = MencionUpdate(nombre="IA")
        with pytest.raises(Exception) as exc:
            mencion_service.update_mencion(db_session, sample_mencion.id, update)
        assert "Ya existe una mención" in str(exc.value)

    def test_delete_mencion_success(self, db_session, sample_mencion):
        result = mencion_service.delete_mencion(db_session, sample_mencion.id)
        assert "desactivada correctamente" in result["message"]

    def test_delete_mencion_not_found(self, db_session):
        with pytest.raises(Exception) as exc:
            mencion_service.delete_mencion(db_session, 999)
        assert "Mención con ID 999 no encontrada" in str(exc.value)

# =========================
# TestMencionRouter
# =========================

class TestMencionRouter:
    def test_post_mencion_success(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        response = client.post("/v0/catalogo/menciones", json=data)
        assert response.status_code == 201
        assert response.json()["nombre"] == "IA"

    def test_post_mencion_programa_not_found(self, client):
        data = {
            "programa_id": 999,
            "nombre": "IA",
            "activo": True
        }
        response = client.post("/v0/catalogo/menciones", json=data)
        assert response.status_code == 404

    def test_post_mencion_duplicate(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        client.post("/v0/catalogo/menciones", json=data)
        response = client.post("/v0/catalogo/menciones", json=data)
        assert response.status_code == 409

    def test_get_menciones_list(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        client.post("/v0/catalogo/menciones", json=data)
        response = client.get(f"/v0/catalogo/menciones?programa_id={sample_programa.id}")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_mencion_by_id(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        post = client.post("/v0/catalogo/menciones", json=data)
        mencion_id = post.json()["id"]
        response = client.get(f"/v0/catalogo/menciones/{mencion_id}")
        assert response.status_code == 200
        assert response.json()["nombre"] == "IA"

    def test_get_mencion_not_found(self, client):
        response = client.get("/v0/catalogo/menciones/999")
        assert response.status_code == 404

    def test_put_mencion_success(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        post = client.post("/v0/catalogo/menciones", json=data)
        mencion_id = post.json()["id"]
        update = {"nombre": "Software Avanzado"}
        response = client.put(f"/v0/catalogo/menciones/{mencion_id}", json=update)
        assert response.status_code == 200
        assert response.json()["nombre"] == "Software Avanzado"

    def test_put_mencion_duplicate(self, client, sample_programa):
        data1 = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        data2 = {
            "programa_id": sample_programa.id,
            "nombre": "Robótica",
            "activo": True
        }
        post1 = client.post("/v0/catalogo/menciones", json=data1)
        post2 = client.post("/v0/catalogo/menciones", json=data2)
        update = {"nombre": "IA"}
        response = client.put(f"/v0/catalogo/menciones/{post2.json()['id']}", json=update)
        assert response.status_code == 409

    def test_delete_mencion_success(self, client, sample_programa):
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        post = client.post("/v0/catalogo/menciones", json=data)
        mencion_id = post.json()["id"]
        response = client.delete(f"/v0/catalogo/menciones/{mencion_id}")
        assert response.status_code == 200
        assert "desactivada correctamente" in response.json()["message"]

    def test_delete_mencion_not_found(self, client):
        response = client.delete("/v0/catalogo/menciones/999")
        assert response.status_code == 404

# =========================
# TestIntegracion
# =========================

class TestIntegracion:
    def test_crud_flow(self, client, sample_programa):
        # Crear
        data = {
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        }
        post = client.post("/v0/catalogo/menciones", json=data)
        mencion_id = post.json()["id"]

        # Leer
        get = client.get(f"/v0/catalogo/menciones/{mencion_id}")
        assert get.status_code == 200

        # Actualizar
        update = {"nombre": "Software Avanzado"}
        put = client.put(f"/v0/catalogo/menciones/{mencion_id}", json=update)
        assert put.status_code == 200
        assert put.json()["nombre"] == "Software Avanzado"

        # Eliminar
        delete = client.delete(f"/v0/catalogo/menciones/{mencion_id}")
        assert delete.status_code == 200

        # Leer inactivo
        get2 = client.get(f"/v0/catalogo/menciones/{mencion_id}")
        assert get2.status_code == 200
        assert get2.json()["activo"] is False

    def test_filtros_combinados(self, client, sample_programa):
        # Crear varias menciones
        client.post("/v0/catalogo/menciones", json={
            "programa_id": sample_programa.id,
            "nombre": "IA",
            "activo": True
        })
        client.post("/v0/catalogo/menciones", json={
            "programa_id": sample_programa.id,
            "nombre": "Robótica",
            "activo": False
        })
        # Filtrar por activo
        resp = client.get(f"/v0/catalogo/menciones?programa_id={sample_programa.id}&activo=true")
        assert resp.status_code == 200
        for m in resp.json()["items"]:
            assert m["activo"] is True