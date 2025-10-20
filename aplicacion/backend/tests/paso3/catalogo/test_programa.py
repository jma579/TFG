"""
Tests completos para el módulo Programa.

Estructura:
- TestProgramaSchemas: Validaciones Pydantic
- TestProgramaRepository: Operaciones de base de datos
- TestProgramaService: Lógica de negocio
- TestProgramaRouter: Endpoints REST API

Fixtures:
- db_session: Sesión de base de datos para tests
- client: Cliente de test de FastAPI
- sample_programa: Programa de ejemplo
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import ValidationError

from backend.main import app
from backend.db.session import get_db
from database.models import Programa, Base
from backend.constants.enums import TipoPrograma
from backend.modules.catalogo.schemas.programa import (
    ProgramaCreate,
    ProgramaUpdate,
    ProgramaOut,
    ProgramaList
)
from backend.modules.catalogo.repositories.programa_repo import ProgramaRepository
from backend.modules.catalogo.services.programa_service import ProgramaService


# ============================================================
#  CONFIGURACIÓN DE BASE DE DATOS DE PRUEBA
# ============================================================

# Base de datos en memoria para tests (SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_catalogo.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================
#  FIXTURES
# ============================================================

@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesión de base de datos limpia para cada test.
    
    - Crea todas las tablas antes del test
    - Hace rollback después del test (aislamiento)
    - Limpia la base de datos
    """
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    # Crear sesión
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # Limpiar base de datos
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Cliente de test de FastAPI con DB de prueba.
    
    Sobrescribe la dependencia get_db para usar la DB de test.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_programa_data():
    """Datos de ejemplo para crear un programa."""
    return {
        "nombre": "Grado en Matemáticas",
        "tipo": TipoPrograma.GRADO,
        "activo": True
    }


@pytest.fixture
def sample_programa(db_session, sample_programa_data):
    """Crea un programa en la base de datos de test."""
    programa = Programa(**sample_programa_data)
    db_session.add(programa)
    db_session.commit()
    db_session.refresh(programa)
    return programa


# ============================================================
#  TEST SUITE 1: SCHEMAS (Pydantic Validations)
# ============================================================

class TestProgramaSchemas:
    """Tests para validaciones de schemas Pydantic."""
    
    def test_programa_create_valid(self):
        """Test: Crear schema válido debe funcionar."""
        data = {
            "nombre": "Grado en Física",
            "tipo": TipoPrograma.GRADO,
            "activo": True
        }
        programa = ProgramaCreate(**data)
        
        assert programa.nombre == "Grado en Física"
        assert programa.tipo == TipoPrograma.GRADO
        assert programa.activo is True
    
    
    def test_programa_create_default_activo(self):
        """Test: Campo activo debe tener default True."""
        data = {
            "nombre": "Máster en IA",
            "tipo": TipoPrograma.MASTER
        }
        programa = ProgramaCreate(**data)
        
        assert programa.activo is True
    
    
    def test_programa_create_nombre_empty(self):
        """Test: Nombre vacío debe fallar validación."""
        with pytest.raises(ValidationError) as exc_info:
            ProgramaCreate(
                nombre="",
                tipo=TipoPrograma.GRADO
            )
        
        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(e) for e in errors)
    
    
    def test_programa_create_nombre_too_long(self):
        """Test: Nombre > 200 caracteres debe fallar."""
        with pytest.raises(ValidationError) as exc_info:
            ProgramaCreate(
                nombre="A" * 201,
                tipo=TipoPrograma.GRADO
            )
        
        errors = exc_info.value.errors()
        assert any("at most 200 character" in str(e) for e in errors)
    
    
    def test_programa_create_tipo_invalid(self):
        """Test: Tipo inválido debe fallar validación."""
        with pytest.raises(ValidationError):
            ProgramaCreate(
                nombre="Test",
                tipo="INVALID_TYPE"  # No es un TipoPrograma válido
            )
    
    
    def test_normalize_nombre_strip(self):
        """Test: Normalización debe quitar espacios al inicio/fin."""
        programa = ProgramaCreate(
            nombre="  Grado en Física  ",
            tipo=TipoPrograma.GRADO
        )
        
        assert programa.nombre == "Grado en Física"
    
    
    def test_normalize_nombre_collapse_spaces(self):
        """Test: Normalización debe colapsar espacios múltiples."""
        programa = ProgramaCreate(
            nombre="Grado   en    Física",
            tipo=TipoPrograma.GRADO
        )
        
        assert programa.nombre == "Grado en Física"
    
    
    def test_programa_update_partial(self):
        """Test: Update debe permitir campos opcionales."""
        # Solo actualizar nombre
        update = ProgramaUpdate(nombre="Nuevo Nombre")
        assert update.nombre == "Nuevo Nombre"
        assert update.tipo is None
        assert update.activo is None
        
        # Solo actualizar activo
        update2 = ProgramaUpdate(activo=False)
        assert update2.nombre is None
        assert update2.activo is False
    
    
    def test_programa_out_from_orm(self, sample_programa):
        """Test: ProgramaOut debe poder crearse desde objeto ORM."""
        programa_out = ProgramaOut.model_validate(sample_programa)
        
        assert programa_out.id == sample_programa.id
        assert programa_out.nombre == sample_programa.nombre
        assert programa_out.tipo == sample_programa.tipo
        assert programa_out.activo == sample_programa.activo
    
    
    def test_programa_list_structure(self):
        """Test: ProgramaList debe validar estructura correcta."""
        programa_out = ProgramaOut(
            id=1,
            nombre="Test",
            tipo=TipoPrograma.GRADO,
            activo=True
        )
        
        lista = ProgramaList(
            total=1,
            items=[programa_out],
            page=1,
            size=10
        )
        
        assert lista.total == 1
        assert len(lista.items) == 1
        assert lista.page == 1
        assert lista.size == 10


# ============================================================
#  TEST SUITE 2: REPOSITORY (Database Operations)
# ============================================================

class TestProgramaRepository:
    """Tests para operaciones del repositorio."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Configurar repository para cada test."""
        self.repo = ProgramaRepository()
    
    
    def test_get_by_id_exists(self, db_session, sample_programa):
        """Test: get_by_id debe devolver programa existente."""
        programa = self.repo.get_by_id(db_session, sample_programa.id)
        
        assert programa is not None
        assert programa.id == sample_programa.id
        assert programa.nombre == sample_programa.nombre
    
    
    def test_get_by_id_not_exists(self, db_session):
        """Test: get_by_id debe devolver None si no existe."""
        programa = self.repo.get_by_id(db_session, 9999)
        
        assert programa is None
    
    
    def test_get_multi_empty(self, db_session):
        """Test: get_multi sin registros debe devolver lista vacía."""
        items, total = self.repo.get_multi(db_session)
        
        assert items == []
        assert total == 0
    
    
    def test_get_multi_with_data(self, db_session):
        """Test: get_multi debe devolver todos los programas."""
        # Crear múltiples programas
        programas_data = [
            {"nombre": "Grado A", "tipo": TipoPrograma.GRADO, "activo": True},
            {"nombre": "Máster B", "tipo": TipoPrograma.MASTER, "activo": True},
            {"nombre": "Doctorado C", "tipo": TipoPrograma.DOCTORADO, "activo": False}
        ]
        
        for data in programas_data:
            programa = Programa(**data)
            db_session.add(programa)
        db_session.commit()
        
        items, total = self.repo.get_multi(db_session)
        
        assert total == 3
        assert len(items) == 3
    
    
    def test_get_multi_filter_activo(self, db_session):
        """Test: Filtrar por activo debe funcionar."""
        # Crear programas activos e inactivos
        db_session.add(Programa(nombre="Activo", tipo=TipoPrograma.GRADO, activo=True))
        db_session.add(Programa(nombre="Inactivo", tipo=TipoPrograma.GRADO, activo=False))
        db_session.commit()
        
        # Filtrar solo activos
        items, total = self.repo.get_multi(db_session, activo=True)
        
        assert total == 1
        assert items[0].activo is True
    
    
    def test_get_multi_filter_tipo(self, db_session):
        """Test: Filtrar por tipo debe funcionar."""
        db_session.add(Programa(nombre="Grado", tipo=TipoPrograma.GRADO, activo=True))
        db_session.add(Programa(nombre="Máster", tipo=TipoPrograma.MASTER, activo=True))
        db_session.commit()
        
        # Filtrar solo GRADO
        items, total = self.repo.get_multi(db_session, tipo=TipoPrograma.GRADO)
        
        assert total == 1
        assert items[0].tipo == TipoPrograma.GRADO
    
    
    def test_get_multi_pagination(self, db_session):
        """Test: Paginación debe funcionar correctamente."""
        # Crear 15 programas
        for i in range(15):
            db_session.add(Programa(
                nombre=f"Programa {i}",
                tipo=TipoPrograma.GRADO,
                activo=True
            ))
        db_session.commit()
        
        # Primera página (0-9)
        items_page1, total = self.repo.get_multi(db_session, skip=0, limit=10)
        assert len(items_page1) == 10
        assert total == 15
        
        # Segunda página (10-14)
        items_page2, total = self.repo.get_multi(db_session, skip=10, limit=10)
        assert len(items_page2) == 5
        assert total == 15
    
    
    def test_get_multi_ordered(self, db_session):
        """Test: Resultados deben estar ordenados alfabéticamente."""
        # Crear programas en orden aleatorio
        nombres = ["Zebra", "Alpha", "Beta"]
        for nombre in nombres:
            db_session.add(Programa(nombre=nombre, tipo=TipoPrograma.GRADO, activo=True))
        db_session.commit()
        
        items, _ = self.repo.get_multi(db_session)
        
        # Verificar orden alfabético
        nombres_obtenidos = [p.nombre for p in items]
        assert nombres_obtenidos == sorted(nombres)
    
    
    def test_create_success(self, db_session):
        """Test: Crear programa debe funcionar."""
        data = {
            "nombre": "Nuevo Grado",
            "tipo": TipoPrograma.GRADO,
            "activo": True
        }
        
        programa = self.repo.create(db_session, data)
        
        assert programa.id is not None  # ID autogenerado
        assert programa.nombre == "Nuevo Grado"
        assert programa.tipo == TipoPrograma.GRADO
    
    
    def test_update_success(self, db_session, sample_programa):
        """Test: Actualizar programa debe funcionar."""
        update_data = {
            "nombre": "Nombre Actualizado",
            "activo": False
        }
        
        updated = self.repo.update(db_session, sample_programa, update_data)
        
        assert updated.nombre == "Nombre Actualizado"
        assert updated.activo is False
        assert updated.tipo == sample_programa.tipo  # No se actualizó
    
    
    def test_update_partial(self, db_session, sample_programa):
        """Test: Update parcial debe actualizar solo campos enviados."""
        original_nombre = sample_programa.nombre
        
        update_data = {"activo": False}
        updated = self.repo.update(db_session, sample_programa, update_data)
        
        assert updated.activo is False
        assert updated.nombre == original_nombre  # No cambió
    
    
    def test_delete_success(self, db_session, sample_programa):
        """Test: Soft delete debe marcar como inactivo."""
        result = self.repo.delete(db_session, sample_programa.id)
        
        assert result is True
        
        # Verificar que está marcado como inactivo
        db_session.refresh(sample_programa)
        assert sample_programa.activo is False
    
    
    def test_delete_not_exists(self, db_session):
        """Test: Delete de programa inexistente debe devolver False."""
        result = self.repo.delete(db_session, 9999)
        
        assert result is False
    
    
    def test_exists_by_nombre_tipo_true(self, db_session, sample_programa):
        """Test: exists_by_nombre_tipo debe detectar existentes."""
        exists = self.repo.exists_by_nombre_tipo(
            db_session,
            sample_programa.nombre,
            sample_programa.tipo
        )
        
        assert exists is True
    
    
    def test_exists_by_nombre_tipo_false(self, db_session):
        """Test: exists_by_nombre_tipo debe devolver False si no existe."""
        exists = self.repo.exists_by_nombre_tipo(
            db_session,
            "Programa Inexistente",
            TipoPrograma.GRADO
        )
        
        assert exists is False
    
    
    def test_exists_by_nombre_tipo_exclude_id(self, db_session, sample_programa):
        """Test: exclude_id debe excluir el programa actual."""
        # Debe devolver False porque el único match es el excluido
        exists = self.repo.exists_by_nombre_tipo(
            db_session,
            sample_programa.nombre,
            sample_programa.tipo,
            exclude_id=sample_programa.id
        )
        
        assert exists is False


# ============================================================
#  TEST SUITE 3: SERVICE (Business Logic)
# ============================================================

class TestProgramaService:
    """Tests para lógica de negocio del service."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Configurar service para cada test."""
        self.service = ProgramaService()
    
    
    def test_get_programa_success(self, db_session, sample_programa):
        """Test: get_programa debe devolver programa existente."""
        resultado = self.service.get_programa(db_session, sample_programa.id)
        
        assert isinstance(resultado, ProgramaOut)
        assert resultado.id == sample_programa.id
        assert resultado.nombre == sample_programa.nombre
    
    
    def test_get_programa_not_found(self, db_session):
        """Test: get_programa debe lanzar 404 si no existe."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_programa(db_session, 9999)
        
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()
    
    
    def test_get_programas_empty(self, db_session):
        """Test: get_programas sin datos debe devolver lista vacía."""
        resultado = self.service.get_programas(db_session)
        
        assert isinstance(resultado, ProgramaList)
        assert resultado.total == 0
        assert resultado.items == []
    
    
    def test_get_programas_with_data(self, db_session):
        """Test: get_programas debe devolver lista correcta."""
        # Crear programas
        for i in range(5):
            db_session.add(Programa(
                nombre=f"Programa {i}",
                tipo=TipoPrograma.GRADO,
                activo=True
            ))
        db_session.commit()
        
        resultado = self.service.get_programas(db_session)
        
        assert resultado.total == 5
        assert len(resultado.items) == 5
        assert all(isinstance(p, ProgramaOut) for p in resultado.items)
    
    
    def test_get_programas_pagination(self, db_session):
        """Test: Paginación debe calcularse correctamente."""
        # Crear 25 programas
        for i in range(25):
            db_session.add(Programa(
                nombre=f"Programa {i:02d}",
                tipo=TipoPrograma.GRADO,
                activo=True
            ))
        db_session.commit()
        
        # Página 2 (items 10-19)
        resultado = self.service.get_programas(db_session, skip=10, limit=10)
        
        assert resultado.total == 25
        assert len(resultado.items) == 10
        assert resultado.page == 2  # (skip=10 / limit=10) + 1
        assert resultado.size == 10
    
    
    def test_create_programa_success(self, db_session):
        """Test: Crear programa válido debe funcionar."""
        programa_in = ProgramaCreate(
            nombre="Nuevo Programa",
            tipo=TipoPrograma.GRADO,
            activo=True
        )
        
        resultado = self.service.create_programa(db_session, programa_in)
        
        assert isinstance(resultado, ProgramaOut)
        assert resultado.id is not None
        assert resultado.nombre == "Nuevo Programa"
    
    
    def test_create_programa_duplicate(self, db_session, sample_programa):
        """Test: Crear programa duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        programa_in = ProgramaCreate(
            nombre=sample_programa.nombre,
            tipo=sample_programa.tipo,
            activo=True
        )
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.create_programa(db_session, programa_in)
        
        assert exc_info.value.status_code == 409
        assert "ya existe" in exc_info.value.detail.lower()
    
    
    def test_update_programa_success(self, db_session, sample_programa):
        """Test: Actualizar programa debe funcionar."""
        update_data = ProgramaUpdate(nombre="Nombre Actualizado")
        
        resultado = self.service.update_programa(
            db_session,
            sample_programa.id,
            update_data
        )
        
        assert resultado.nombre == "Nombre Actualizado"
        assert resultado.id == sample_programa.id
    
    
    def test_update_programa_not_found(self, db_session):
        """Test: Actualizar programa inexistente debe lanzar 404."""
        from fastapi import HTTPException
        
        update_data = ProgramaUpdate(nombre="Test")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_programa(db_session, 9999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_programa_duplicate(self, db_session):
        """Test: Actualizar a nombre duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        # Crear dos programas
        prog1 = Programa(nombre="Programa 1", tipo=TipoPrograma.GRADO, activo=True)
        prog2 = Programa(nombre="Programa 2", tipo=TipoPrograma.GRADO, activo=True)
        db_session.add_all([prog1, prog2])
        db_session.commit()
        
        # Intentar actualizar prog2 con el nombre de prog1
        update_data = ProgramaUpdate(nombre="Programa 1")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_programa(db_session, prog2.id, update_data)
        
        assert exc_info.value.status_code == 409
    
    
    def test_delete_programa_success(self, db_session, sample_programa):
        """Test: Delete debe devolver mensaje de éxito."""
        resultado = self.service.delete_programa(db_session, sample_programa.id)
        
        assert "message" in resultado
        assert "desactivado" in resultado["message"].lower()
    
    
    def test_delete_programa_not_found(self, db_session):
        """Test: Delete de programa inexistente debe lanzar 404."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.delete_programa(db_session, 9999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TEST SUITE 4: ROUTER (API Endpoints)
# ============================================================

class TestProgramaRouter:
    """Tests para endpoints REST API."""
    
    def test_listar_programas_empty(self, client):
        """Test: GET /programas sin datos debe devolver lista vacía."""
        response = client.get("/v0/catalogo/programas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["size"] == 100
    
    
    def test_listar_programas_with_data(self, client, db_session):
        """Test: GET /programas debe devolver programas existentes."""
        # Crear programas
        db_session.add(Programa(nombre="Programa A", tipo=TipoPrograma.GRADO, activo=True))
        db_session.add(Programa(nombre="Programa B", tipo=TipoPrograma.MASTER, activo=True))
        db_session.commit()
        
        response = client.get("/v0/catalogo/programas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["items"]) == 2
    
    
    def test_listar_programas_filters(self, client, db_session):
        """Test: Filtros de query params deben funcionar."""
        # Crear programas de diferentes tipos
        db_session.add(Programa(nombre="Grado 1", tipo=TipoPrograma.GRADO, activo=True))
        db_session.add(Programa(nombre="Máster 1", tipo=TipoPrograma.MASTER, activo=True))
        db_session.add(Programa(nombre="Grado 2", tipo=TipoPrograma.GRADO, activo=False))
        db_session.commit()
        
        # Filtrar por tipo=grado y activo=true
        response = client.get("/v0/catalogo/programas?tipo=grado&activo=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1  # Solo "Grado 1"
        assert data["items"][0]["tipo"] == "grado"
        assert data["items"][0]["activo"] is True
    
    
    def test_listar_programas_pagination(self, client, db_session):
        """Test: Paginación debe funcionar correctamente."""
        # Crear 15 programas
        for i in range(15):
            db_session.add(Programa(
                nombre=f"Programa {i:02d}",
                tipo=TipoPrograma.GRADO,
                activo=True
            ))
        db_session.commit()
        
        # Página 2 (skip=10, limit=5)
        response = client.get("/v0/catalogo/programas?skip=10&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 15
        assert len(data["items"]) == 5
        assert data["page"] == 3  # (10 / 5) + 1
    
    
    def test_obtener_programa_success(self, client, db_session, sample_programa):
        """Test: GET /programas/{id} debe devolver programa."""
        response = client.get(f"/v0/catalogo/programas/{sample_programa.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == sample_programa.id
        assert data["nombre"] == sample_programa.nombre
    
    
    def test_obtener_programa_not_found(self, client):
        """Test: GET /programas/{id} inexistente debe devolver 404."""
        response = client.get("/v0/catalogo/programas/9999")
        
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()
    
    
    def test_obtener_programa_invalid_id(self, client):
        """Test: ID inválido debe devolver 422."""
        response = client.get("/v0/catalogo/programas/abc")
        
        assert response.status_code == 422
    
    
    def test_crear_programa_success(self, client):
        """Test: POST /programas debe crear programa."""
        data = {
            "nombre": "Nuevo Programa",
            "tipo": "grado",
            "activo": True
        }
        
        response = client.post("/v0/catalogo/programas", json=data)
        
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["id"] is not None
        assert response_data["nombre"] == "Nuevo Programa"
        assert response_data["tipo"] == "grado"
    
    
    def test_crear_programa_invalid_data(self, client):
        """Test: Datos inválidos deben devolver 422."""
        data = {
            "nombre": "",  # Vacío (inválido)
            "tipo": "grado"
        }
        
        response = client.post("/v0/catalogo/programas", json=data)
        
        assert response.status_code == 422
    
    
    def test_crear_programa_duplicate(self, client, db_session, sample_programa):
        """Test: Crear duplicado debe devolver 409."""
        data = {
            "nombre": sample_programa.nombre,
            "tipo": sample_programa.tipo.value,
            "activo": True
        }
        
        response = client.post("/v0/catalogo/programas", json=data)
        
        assert response.status_code == 409
        assert "ya existe" in response.json()["detail"].lower()
    
    
    def test_actualizar_programa_success(self, client, db_session, sample_programa):
        """Test: PUT /programas/{id} debe actualizar."""
        data = {"nombre": "Nombre Actualizado"}
        
        response = client.put(
            f"/v0/catalogo/programas/{sample_programa.id}",
            json=data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["nombre"] == "Nombre Actualizado"
        assert response_data["id"] == sample_programa.id
    
    
    def test_actualizar_programa_not_found(self, client):
        """Test: PUT programa inexistente debe devolver 404."""
        data = {"nombre": "Test"}
        
        response = client.put("/v0/catalogo/programas/9999", json=data)
        
        assert response.status_code == 404
    
    
    def test_eliminar_programa_success(self, client, db_session, sample_programa):
        """Test: DELETE /programas/{id} debe desactivar."""
        response = client.delete(f"/v0/catalogo/programas/{sample_programa.id}")
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verificar que está inactivo
        db_session.refresh(sample_programa)
        assert sample_programa.activo is False
    
    
    def test_eliminar_programa_not_found(self, client):
        """Test: DELETE programa inexistente debe devolver 404."""
        response = client.delete("/v0/catalogo/programas/9999")
        
        assert response.status_code == 404


# ============================================================
#  TESTS DE INTEGRACIÓN
# ============================================================

class TestIntegracion:
    """Tests de flujo completo end-to-end."""
    
    def test_flujo_crud_completo(self, client, db_session):
        """Test: Flujo completo CREATE → READ → UPDATE → DELETE."""
        
        # 1. CREATE
        create_data = {
            "nombre": "Grado en Física",
            "tipo": "grado",
            "activo": True
        }
        response = client.post("/v0/catalogo/programas", json=create_data)
        assert response.status_code == 201
        programa_id = response.json()["id"]
        
        # 2. READ (GET by ID)
        response = client.get(f"/v0/catalogo/programas/{programa_id}")
        assert response.status_code == 200
        assert response.json()["nombre"] == "Grado en Física"
        
        # 3. READ (GET list)
        response = client.get("/v0/catalogo/programas")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        
        # 4. UPDATE
        update_data = {"nombre": "Grado en Física Aplicada"}
        response = client.put(
            f"/v0/catalogo/programas/{programa_id}",
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Grado en Física Aplicada"
        
        # 5. DELETE (soft delete)
        response = client.delete(f"/v0/catalogo/programas/{programa_id}")
        assert response.status_code == 200
        
        # 6. Verificar que está inactivo
        response = client.get(f"/v0/catalogo/programas/{programa_id}")
        assert response.status_code == 200
        assert response.json()["activo"] is False