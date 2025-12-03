"""
Tests para el módulo de Profesores.

Estructura:
1. Fixtures: Datos de prueba y helpers
2. Tests de Repository: Acceso a datos
3. Tests de Service: Lógica de negocio
4. Tests de API: Endpoints REST

Cobertura:
- CRUD completo (Create, Read, Update, Delete)
- Búsqueda por nombre
- Validaciones (email único)
- Filtros y paginación
- Casos edge y manejo de errores
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base, Profesor
from db.session import get_db
from main import app
from modules.recursos.schemas.profesor import (
    ProfesorCreate, ProfesorUpdate, ProfesorOut
)
from modules.recursos.repositories.profesor_repo import profesor_repository
from modules.recursos.services.profesor_service import profesor_service

# Configuración de base de datos de pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================
#  FIXTURES: Base de datos y cliente
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Crear todas las tablas al inicio de la sesión de tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Crear sesión de base de datos para cada test, con rollback al final."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """Cliente de test con sesión de base de datos aislada."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================
#  FIXTURES: Datos de prueba
# ============================================================

@pytest.fixture
def profesor_data_1():
    """Datos de prueba para profesor 1."""
    return {
        "nombre": "Juan",
        "apellidos": "García López",
        "email": "juan.garcia@uam.es",
        "telefono": "+34 912 345 678",
        "departamento": "Matemáticas",
        "activo": True
    }


@pytest.fixture
def profesor_data_2():
    """Datos de prueba para profesor 2."""
    return {
        "nombre": "María",
        "apellidos": "Martínez Fernández",
        "email": "maria.martinez@uam.es",
        "telefono": "+34 912 987 654",
        "departamento": "Ingeniería Informática",
        "activo": True
    }


@pytest.fixture
def profesor_data_3():
    """Datos de prueba para profesor 3 (sin email)."""
    return {
        "nombre": "Pedro",
        "apellidos": "Sánchez Gómez",
        "email": None,
        "telefono": None,
        "departamento": "Física Aplicada",
        "activo": True
    }


@pytest.fixture
def profesor_data_inactivo():
    """Datos de prueba para profesor inactivo."""
    return {
        "nombre": "Carlos",
        "apellidos": "Ruiz Díaz",
        "email": "carlos.ruiz@uam.es",
        "telefono": None,
        "departamento": "Matemáticas",
        "activo": False
    }


@pytest.fixture
def crear_profesor(db: Session):
    """Helper fixture para crear profesores en tests."""
    def _crear_profesor(**kwargs):
        profesor_data = ProfesorCreate(**kwargs)
        return profesor_repository.create(db, profesor_data)
    return _crear_profesor


# ============================================================
#  TESTS DE REPOSITORY: Acceso a datos
# ============================================================

class TestProfesorRepository:
    """Tests para ProfesorRepository."""
    
    def test_create_profesor(self, db: Session, profesor_data_1):
        """Test crear profesor básico."""
        # Arrange
        profesor_in = ProfesorCreate(**profesor_data_1)
        
        # Act
        profesor = profesor_repository.create(db, profesor_in)
        
        # Assert
        assert profesor.id is not None
        assert profesor.nombre == "Juan"
        assert profesor.apellidos == "García López"
        assert profesor.email == "juan.garcia@uam.es"
        assert profesor.telefono == "+34 912 345 678"
        assert profesor.departamento == "Matemáticas"
        assert profesor.activo is True
    
    
    def test_create_profesor_sin_email(self, db: Session, profesor_data_3):
        """Test crear profesor sin email (campo opcional)."""
        # Arrange
        profesor_in = ProfesorCreate(**profesor_data_3)
        
        # Act
        profesor = profesor_repository.create(db, profesor_in)
        
        # Assert
        assert profesor.id is not None
        assert profesor.nombre == "Pedro"
        assert profesor.email is None
        assert profesor.telefono is None
    
    
    def test_get_by_id_existente(self, db: Session, crear_profesor, profesor_data_1):
        """Test obtener profesor por ID existente."""
        # Arrange
        profesor_creado = crear_profesor(**profesor_data_1)
        
        # Act
        profesor = profesor_repository.get_by_id(db, profesor_creado.id)
        
        # Assert
        assert profesor is not None
        assert profesor.id == profesor_creado.id
        assert profesor.nombre == "Juan"
    
    
    def test_get_by_id_no_existente(self, db: Session):
        """Test obtener profesor por ID no existente."""
        # Act
        profesor = profesor_repository.get_by_id(db, 99999)
        
        # Assert
        assert profesor is None
    
    
    def test_get_by_nombre_coincidencia_unica(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test buscar por nombre con coincidencia única."""
        # Arrange
        crear_profesor(**profesor_data_1)
        
        # Act
        profesores = profesor_repository.get_by_nombre(db, "Juan García")
        
        # Assert
        assert len(profesores) == 1
        assert profesores[0].nombre == "Juan"
        assert profesores[0].apellidos == "García López"
    
    
    def test_get_by_nombre_multiples_coincidencias(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_2
    ):
        """Test buscar por nombre con múltiples coincidencias."""
        # Arrange
        # Modificar ambos para que tengan apellido común
        data_1 = profesor_data_1.copy()
        data_1["apellidos"] = "Gómez López"
        data_1["email"] = "juan.gomez@uam.es"
        
        data_2 = profesor_data_2.copy()
        data_2["nombre"] = "Kike"
        data_2["apellidos"] = "Gómez Fernández"
        data_2["email"] = "kike.gomez@uam.es"
        
        crear_profesor(**data_1)
        crear_profesor(**data_2)
        
        # Act
        profesores = profesor_repository.get_by_nombre(db, "Gómez")
        
        # Assert
        assert len(profesores) == 2
        nombres = [p.nombre for p in profesores]
        assert "Juan" in nombres
        assert "Kike" in nombres
    
    
    def test_get_by_nombre_sin_coincidencias(self, db: Session):
        """Test buscar por nombre sin coincidencias."""
        # Act
        profesores = profesor_repository.get_by_nombre(db, "NoExiste")
        
        # Assert
        assert len(profesores) == 0
    
    
    def test_get_by_nombre_case_insensitive(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test búsqueda case-insensitive."""
        # Arrange
        crear_profesor(**profesor_data_1)
        
        # Act - buscar en minúsculas
        profesores = profesor_repository.get_by_nombre(db, "juan garcía")
        
        # Assert
        assert len(profesores) == 1
        assert profesores[0].nombre == "Juan"
    
    
    def test_get_by_nombre_orden_inverso(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test búsqueda con orden inverso (apellidos nombre)."""
        # Arrange
        crear_profesor(**profesor_data_1)
        
        # Act - buscar por "apellidos nombre"
        profesores = profesor_repository.get_by_nombre(db, "García Juan")
        
        # Assert
        assert len(profesores) == 1
        assert profesores[0].nombre == "Juan"
    
    
    def test_get_multi_sin_filtros(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_2
    ):
        """Test listar todos los profesores sin filtros."""
        # Arrange
        crear_profesor(**profesor_data_1)
        crear_profesor(**profesor_data_2)
        
        # Act
        profesores, total = profesor_repository.get_multi(db)
        
        # Assert
        assert total == 2
        assert len(profesores) == 2
    
    
    def test_get_multi_con_paginacion(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_2
    ):
        """Test paginación con skip y limit."""
        # Arrange
        crear_profesor(**profesor_data_1)
        crear_profesor(**profesor_data_2)
        
        # Act - obtener solo el primer registro
        profesores, total = profesor_repository.get_multi(db, skip=0, limit=1)
        
        # Assert
        assert total == 2  # Total sin paginar
        assert len(profesores) == 1  # Solo 1 en esta página
    
    
    def test_get_multi_filtro_departamento(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_2
    ):
        """Test filtrar por departamento."""
        # Arrange
        crear_profesor(**profesor_data_1)  # Matemáticas
        crear_profesor(**profesor_data_2)  # Ingeniería Informática
        
        # Act
        profesores, total = profesor_repository.get_multi(
            db, departamento="Matemáticas"
        )
        
        # Assert
        assert total == 1
        assert profesores[0].departamento == "Matemáticas"
    
    
    def test_get_multi_filtro_activo(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_inactivo
    ):
        """Test filtrar por estado activo."""
        # Arrange
        crear_profesor(**profesor_data_1)  # activo=True
        crear_profesor(**profesor_data_inactivo)  # activo=False
        
        # Act
        profesores, total = profesor_repository.get_multi(db, activo=True)
        
        # Assert
        assert total == 1
        assert profesores[0].activo is True
    
    
    def test_get_multi_ordenacion_apellidos(
        self, db: Session, crear_profesor
    ):
        """Test ordenación por apellidos + nombre."""
        # Arrange - crear en orden aleatorio
        crear_profesor(
            nombre="Carlos", apellidos="Zárate", 
            email="c@test.com", activo=True
        )
        crear_profesor(
            nombre="Ana", apellidos="Álvarez", 
            email="a@test.com", activo=True
        )
        crear_profesor(
            nombre="Beatriz", apellidos="Márquez", 
            email="b@test.com", activo=True
        )
        
        # Act
        profesores, total = profesor_repository.get_multi(db)
        
        # Assert - debe estar ordenado alfabéticamente por apellidos
        assert total == 3
        assert profesores[0].apellidos == "Álvarez"
        assert profesores[1].apellidos == "Márquez"
        assert profesores[2].apellidos == "Zárate"
    
    
    def test_update_profesor(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test actualizar profesor."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        update_data = ProfesorUpdate(
            email="nuevo.email@uam.es",
            departamento="Física"
        )
        
        # Act
        profesor_actualizado = profesor_repository.update(db, profesor, update_data)
        
        # Assert
        assert profesor_actualizado.id == profesor.id
        assert profesor_actualizado.email == "nuevo.email@uam.es"
        assert profesor_actualizado.departamento == "Física"
        assert profesor_actualizado.nombre == "Juan"  # No cambió
    
    
    def test_update_profesor_borrar_email(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test actualizar profesor borrando email (None)."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        update_data = ProfesorUpdate(email=None)
        
        # Act
        profesor_actualizado = profesor_repository.update(db, profesor, update_data)
        
        # Assert
        assert profesor_actualizado.email is None
    
    
    def test_delete_soft_delete(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test soft delete (cambiar activo a False)."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        assert profesor.activo is True
        
        # Act
        profesor_eliminado = profesor_repository.delete(db, profesor.id)
        
        # Assert
        assert profesor_eliminado is not None
        assert profesor_eliminado.activo is False
        assert profesor_eliminado.id == profesor.id
    
    
    def test_delete_no_existente(self, db: Session):
        """Test soft delete de profesor no existente."""
        # Act
        resultado = profesor_repository.delete(db, 99999)
        
        # Assert
        assert resultado is None


# ============================================================
#  TESTS DE SERVICE: Lógica de negocio
# ============================================================

class TestProfesorService:
    """Tests para ProfesorService."""
    
    def test_create_profesor_exitoso(self, db: Session, profesor_data_1):
        """Test crear profesor con datos válidos."""
        # Arrange
        profesor_in = ProfesorCreate(**profesor_data_1)
        
        # Act
        profesor = profesor_service.create(db, profesor_in)
        
        # Assert
        assert isinstance(profesor, ProfesorOut)
        assert profesor.id is not None
        assert profesor.nombre == "Juan"
        assert profesor.email == "juan.garcia@uam.es"
    
    
    def test_create_profesor_email_duplicado(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test crear profesor con email duplicado (debe fallar)."""
        # Arrange
        crear_profesor(**profesor_data_1)
        profesor_duplicado = ProfesorCreate(**profesor_data_1)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            profesor_service.create(db, profesor_duplicado)
        
        assert exc_info.value.status_code == 409
        assert "email" in str(exc_info.value.detail).lower()
    
    
    def test_create_profesor_sin_email_permitido(
        self, db: Session, profesor_data_3
    ):
        """Test crear múltiples profesores sin email (debe permitirse)."""
        # Arrange
        prof_1 = ProfesorCreate(**profesor_data_3)
        prof_2_data = profesor_data_3.copy()
        prof_2_data["nombre"] = "Luis"
        prof_2 = ProfesorCreate(**prof_2_data)
        
        # Act
        profesor_1 = profesor_service.create(db, prof_1)
        profesor_2 = profesor_service.create(db, prof_2)
        
        # Assert - ambos deben crearse sin problemas
        assert profesor_1.id is not None
        assert profesor_2.id is not None
        assert profesor_1.email is None
        assert profesor_2.email is None
    
    
    def test_get_by_id_existente(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test obtener profesor existente."""
        # Arrange
        profesor_creado = crear_profesor(**profesor_data_1)
        
        # Act
        profesor = profesor_service.get_by_id(db, profesor_creado.id)
        
        # Assert
        assert isinstance(profesor, ProfesorOut)
        assert profesor.id == profesor_creado.id
    
    
    def test_get_by_id_no_existente(self, db: Session):
        """Test obtener profesor no existente (debe lanzar 404)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            profesor_service.get_by_id(db, 99999)
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_by_nombre_retorna_lista(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test búsqueda por nombre retorna lista de ProfesorOut."""
        # Arrange
        crear_profesor(**profesor_data_1)
        
        # Act
        profesores = profesor_service.get_by_nombre(db, "Juan")
        
        # Assert
        assert isinstance(profesores, list)
        assert len(profesores) > 0
        assert all(isinstance(p, ProfesorOut) for p in profesores)
    
    
    def test_get_by_nombre_lista_vacia_no_error(self, db: Session):
        """Test búsqueda sin resultados retorna lista vacía (no 404)."""
        # Act
        profesores = profesor_service.get_by_nombre(db, "NoExiste")
        
        # Assert
        assert isinstance(profesores, list)
        assert len(profesores) == 0
    
    
    def test_get_multi_retorna_tupla(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test get_multi retorna tupla (items, total)."""
        # Arrange
        crear_profesor(**profesor_data_1)
        
        # Act
        items, total = profesor_service.get_multi(db)
        
        # Assert
        assert isinstance(items, list)
        assert isinstance(total, int)
        assert len(items) == total
        assert all(isinstance(p, ProfesorOut) for p in items)
    
    
    def test_update_profesor_exitoso(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test actualizar profesor con datos válidos."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        update_data = ProfesorUpdate(departamento="Física")
        
        # Act
        actualizado = profesor_service.update(db, profesor.id, update_data)
        
        # Assert
        assert isinstance(actualizado, ProfesorOut)
        assert actualizado.departamento == "Física"
        assert actualizado.nombre == "Juan"  # No cambió
    
    
    def test_update_profesor_no_existente(self, db: Session):
        """Test actualizar profesor no existente (debe lanzar 404)."""
        # Arrange
        update_data = ProfesorUpdate(departamento="Física")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            profesor_service.update(db, 99999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_profesor_email_duplicado(
        self, db: Session, crear_profesor, profesor_data_1, profesor_data_2
    ):
        """Test actualizar con email que ya existe en otro profesor."""
        # Arrange
        profesor_1 = crear_profesor(**profesor_data_1)
        profesor_2 = crear_profesor(**profesor_data_2)
        
        # Act - intentar actualizar profesor_2 con email de profesor_1
        update_data = ProfesorUpdate(email=profesor_1.email)
        
        # Assert
        with pytest.raises(HTTPException) as exc_info:
            profesor_service.update(db, profesor_2.id, update_data)
        
        assert exc_info.value.status_code == 409
    
    
    def test_update_profesor_mismo_email_permitido(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test actualizar profesor con su propio email (debe permitirse)."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        update_data = ProfesorUpdate(
            email=profesor.email,  # Mismo email
            departamento="Física"
        )
        
        # Act - NO debe lanzar error 409
        actualizado = profesor_service.update(db, profesor.id, update_data)
        
        # Assert
        assert actualizado.email == profesor.email
        assert actualizado.departamento == "Física"
    
    
    def test_update_borrar_email_con_none(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test borrar email actualizando a None."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        update_data = ProfesorUpdate(email=None)
        
        # Act
        actualizado = profesor_service.update(db, profesor.id, update_data)
        
        # Assert
        assert actualizado.email is None
    
    
    def test_delete_profesor_existente(
        self, db: Session, crear_profesor, profesor_data_1
    ):
        """Test eliminar profesor existente (soft delete)."""
        # Arrange
        profesor = crear_profesor(**profesor_data_1)
        
        # Act
        profesor_service.delete(db, profesor.id)
        
        # Assert - verificar que está inactivo
        profesor_db = profesor_repository.get_by_id(db, profesor.id)
        assert profesor_db is not None  # Sigue existiendo
        assert profesor_db.activo is False  # Pero inactivo
    
    
    def test_delete_profesor_no_existente(self, db: Session):
        """Test eliminar profesor no existente (debe lanzar 404)."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            profesor_service.delete(db, 99999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TESTS DE API: Endpoints REST
# ============================================================

class TestProfesorAPI:
    """Tests para endpoints REST de Profesor."""
    
    def test_crear_profesor_endpoint(self, client, profesor_data_1):
        """Test POST /recursos/profesores."""
        # Act
        response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Juan"
        assert data["email"] == "juan.garcia@uam.es"
        assert "id" in data
    
    
    def test_crear_profesor_email_duplicado_endpoint(
        self, client, profesor_data_1
    ):
        """Test POST con email duplicado debe retornar 409."""
        # Arrange
        client.post("/v0/recursos/profesores/", json=profesor_data_1)
        
        # Act - intentar crear de nuevo
        response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        
        # Assert
        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower()
    
    
    def test_crear_profesor_datos_invalidos_endpoint(self, client):
        """Test POST con datos inválidos debe retornar 422."""
        # Arrange - nombre vacío (viola min_length=1)
        datos_invalidos = {
            "nombre": "",
            "apellidos": "García",
            "activo": True
        }
        
        # Act
        response = client.post("/v0/recursos/profesores/", json=datos_invalidos)
        
        # Assert
        assert response.status_code == 422
    
    
    def test_obtener_profesor_endpoint(self, client, profesor_data_1):
        """Test GET /recursos/profesores/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        profesor_id = create_response.json()["id"]
        
        # Act
        response = client.get(f"/v0/recursos/profesores/{profesor_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == profesor_id
        assert data["nombre"] == "Juan"
    
    
    def test_obtener_profesor_no_existente_endpoint(self, client):
        """Test GET con ID no existente debe retornar 404."""
        # Act
        response = client.get("/v0/recursos/profesores/99999")
        
        # Assert
        assert response.status_code == 404
    
    
    def test_buscar_profesores_endpoint(self, client, profesor_data_1):
        """Test GET /recursos/profesores/buscar."""
        # Arrange
        client.post("/v0/recursos/profesores/", json=profesor_data_1)
        
        # Act
        response = client.get("/v0/recursos/profesores/buscar?busqueda=Juan")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["nombre"] == "Juan"
    
    
    def test_buscar_profesores_sin_resultados_endpoint(self, client):
        """Test búsqueda sin resultados retorna lista vacía."""
        # Act
        response = client.get("/v0/recursos/profesores/buscar?busqueda=NoExiste")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []
    
    
    def test_listar_profesores_endpoint(self, client, profesor_data_1, profesor_data_2):
        """Test GET /recursos/profesores (lista)."""
        # Arrange
        client.post("/v0/recursos/profesores/", json=profesor_data_1)
        client.post("/v0/recursos/profesores/", json=profesor_data_2)
        
        # Act
        response = client.get("/v0/recursos/profesores/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
    
    
    def test_listar_profesores_con_paginacion_endpoint(
        self, client, profesor_data_1, profesor_data_2
    ):
        """Test paginación con skip y limit."""
        # Arrange
        client.post("/v0/recursos/profesores/", json=profesor_data_1)
        client.post("/v0/recursos/profesores/", json=profesor_data_2)
        
        # Act
        response = client.get("/v0/recursos/profesores/?skip=0&limit=1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["items"]) == 1
        assert data["size"] == 1
    
    
    def test_listar_profesores_filtro_departamento_endpoint(
        self, client, profesor_data_1, profesor_data_2
    ):
        """Test filtrar por departamento."""
        # Arrange
        client.post("/v0/recursos/profesores/", json=profesor_data_1)
        client.post("/v0/recursos/profesores/", json=profesor_data_2)
        
        # Act
        response = client.get("/v0/recursos/profesores/?departamento=Matemáticas")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert all(p["departamento"] == "Matemáticas" for p in data["items"])
    
    
    def test_actualizar_profesor_endpoint(self, client, profesor_data_1):
        """Test PUT /recursos/profesores/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        profesor_id = create_response.json()["id"]
        
        update_data = {"departamento": "Física"}
        
        # Act
        response = client.put(
            f"/v0/recursos/profesores/{profesor_id}",
            json=update_data
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["departamento"] == "Física"
        assert data["nombre"] == "Juan"  # No cambió
    
    
    def test_actualizar_profesor_borrar_email_endpoint(
        self, client, profesor_data_1
    ):
        """Test actualizar profesor borrando email (null)."""
        # Arrange
        create_response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        profesor_id = create_response.json()["id"]
        
        # Act
        response = client.put(
            f"/v0/recursos/profesores/{profesor_id}",
            json={"email": None}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] is None
    
    
    def test_actualizar_profesor_no_existente_endpoint(self, client):
        """Test PUT con ID no existente debe retornar 404."""
        # Act
        response = client.put(
            "/v0/recursos/profesores/99999",
            json={"departamento": "Física"}
        )
        
        # Assert
        assert response.status_code == 404
    
    
    def test_eliminar_profesor_endpoint(self, client, profesor_data_1):
        """Test DELETE /recursos/profesores/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/profesores/", json=profesor_data_1)
        profesor_id = create_response.json()["id"]
        
        # Act
        response = client.delete(f"/v0/recursos/profesores/{profesor_id}")
        
        # Assert
        assert response.status_code == 204
        
        # Verificar que está inactivo
        get_response = client.get(f"/v0/recursos/profesores/{profesor_id}")
        assert get_response.status_code == 200
        assert get_response.json()["activo"] is False
    
    
    def test_eliminar_profesor_no_existente_endpoint(self, client):
        """Test DELETE con ID no existente debe retornar 404."""
        # Act
        response = client.delete("/v0/recursos/profesores/99999")
        
        # Assert
        assert response.status_code == 404


# ============================================================
#  TESTS DE EDGE CASES
# ============================================================

class TestProfesorEdgeCases:
    """Tests de casos límite y edge cases."""
    
    def test_normalizar_espacios_nombre(self, db: Session):
        """Test normalización de espacios en nombre."""
        # Arrange - nombre con múltiples espacios
        profesor_in = ProfesorCreate(
            nombre="  Juan   Carlos  ",
            apellidos="  García   López  ",
            activo=True
        )
        
        # Act
        profesor = profesor_service.create(db, profesor_in)
        
        # Assert - espacios normalizados
        assert profesor.nombre == "Juan Carlos"
        assert profesor.apellidos == "García López"
    
    
    def test_normalizar_email_lowercase(self, db: Session):
        """Test normalización de email a lowercase."""
        # Arrange
        profesor_in = ProfesorCreate(
            nombre="Juan",
            apellidos="García",
            email="  JUAN.GARCIA@UAM.ES  ",
            activo=True
        )
        
        # Act
        profesor = profesor_service.create(db, profesor_in)
        
        # Assert
        assert profesor.email == "juan.garcia@uam.es"
    
    
    def test_telefono_con_formato_internacional(self, db: Session):
        """Test teléfono con formato internacional."""
        # Arrange
        profesor_in = ProfesorCreate(
            nombre="Juan",
            apellidos="García",
            telefono="+1-555-1234-5678",
            activo=True
        )
        
        # Act
        profesor = profesor_service.create(db, profesor_in)
        
        # Assert - mantiene formato original
        assert profesor.telefono == "+1-555-1234-5678"
    
    
    def test_campos_max_length(self, db: Session):
        """Test validación de longitud máxima de campos."""
        # Arrange - nombre exactamente en el límite (120)
        profesor_in = ProfesorCreate(
            nombre="A" * 120,
            apellidos="B" * 200,
            email="test@example.com",
            activo=True
        )
        
        # Act
        profesor = profesor_service.create(db, profesor_in)
        
        # Assert
        assert len(profesor.nombre) == 120
        assert len(profesor.apellidos) == 200
    
    
    def test_buscar_con_caracteres_especiales(self, db: Session, crear_profesor):
        """Test búsqueda con caracteres especiales."""
        # Arrange
        crear_profesor(
            nombre="María José",
            apellidos="Ñoño Gómez",
            email="test@test.com",
            activo=True
        )
        
        # Act
        profesores = profesor_repository.get_by_nombre(db, "Ñoño")
        
        # Assert
        assert len(profesores) == 1
    
    
    def test_multiples_profesores_mismo_departamento(
        self, db: Session, crear_profesor
    ):
        """Test múltiples profesores en mismo departamento."""
        # Arrange
        for i in range(5):
            crear_profesor(
                nombre=f"Profesor{i}",
                apellidos=f"Apellido{i}",
                email=f"prof{i}@test.com",
                departamento="Matemáticas",
                activo=True
            )
        
        # Act
        profesores, total = profesor_repository.get_multi(
            db, departamento="Matemáticas"
        )
        
        # Assert
        assert total == 5