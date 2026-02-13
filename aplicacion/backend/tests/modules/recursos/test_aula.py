"""
Tests para el módulo de Aulas.

Estructura:
1. Fixtures: Datos de prueba y helpers
2. Tests de Repository: Acceso a datos
3. Tests de Service: Lógica de negocio
4. Tests de API: Endpoints REST

Cobertura:
- CRUD completo (Create, Read, Update, Delete físico)
- Búsqueda por nombre/código
- Validaciones (código único, nombre único)
- Filtros y paginación (tipo, capacidad_min/max, búsqueda)
- Casos edge y manejo de errores
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base, Aula
from db.session import get_db
from main import app
from modules.recursos.schemas.aula import (
    AulaCreate, AulaUpdate, AulaOut
)
from modules.recursos.repositories.aula_repo import aula_repository
from modules.recursos.services.aula_service import aula_service
from constants.enums import TipoAula

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
def aula_data_1():
    """Datos de prueba para aula 1."""
    return {
        "nombre": "Aula Magna",
        "codigo": "MAGNA",
        "tipo": TipoAula.TEORICA,
        "capacidad": 200
    }


@pytest.fixture
def aula_data_2():
    """Datos de prueba para aula 2."""
    return {
        "nombre": "Laboratorio de Física",
        "codigo": "LAB-FIS-1",
        "tipo": TipoAula.LABORATORIO,
        "capacidad": 30
    }


@pytest.fixture
def aula_data_3():
    """Datos de prueba para aula 3 (sin capacidad)."""
    return {
        "nombre": "Sala de Seminarios",
        "codigo": "SEM-1",
        "tipo": TipoAula.SEMINARIO,
        "capacidad": None
    }


@pytest.fixture
def aula_data_informatica():
    """Datos de prueba para aula de informática."""
    return {
        "nombre": "Aula de Informática 1",
        "codigo": "INF-1",
        "tipo": TipoAula.INFORMATICA,
        "capacidad": 40
    }


@pytest.fixture
def crear_aula(db: Session):
    """Helper fixture para crear aulas en tests."""
    def _crear_aula(**kwargs):
        aula_data = AulaCreate(**kwargs)
        return aula_repository.create(db, aula_data)
    return _crear_aula


# ============================================================
#  TESTS DE REPOSITORY: Acceso a datos
# ============================================================

class TestAulaRepository:
    """Tests para AulaRepository."""
    
    def test_create_aula(self, db: Session, aula_data_1):
        """Test crear aula básica."""
        # Arrange
        aula_data = AulaCreate(**aula_data_1)
        
        # Act
        aula = aula_repository.create(db, aula_data)
        db.commit()
        
        # Assert
        assert aula.id is not None
        assert aula.nombre == "Aula Magna"
        assert aula.codigo == "MAGNA"
        assert aula.tipo == TipoAula.TEORICA
        assert aula.capacidad == 200
    
    
    def test_create_aula_sin_capacidad(self, db: Session, aula_data_3):
        """Test crear aula sin capacidad (campo opcional)."""
        # Arrange
        aula_data = AulaCreate(**aula_data_3)
        
        # Act
        aula = aula_repository.create(db, aula_data)
        db.commit()
        
        # Assert
        assert aula.id is not None
        assert aula.nombre == "Sala de Seminarios"
        assert aula.capacidad is None
    
    
    def test_get_by_id_existente(self, db: Session, crear_aula, aula_data_1):
        """Test obtener aula por ID existente."""
        # Arrange
        aula_creada = crear_aula(**aula_data_1)
        db.commit()
        
        # Act
        aula = aula_repository.get_by_id(db, aula_creada.id)
        
        # Assert
        assert aula is not None
        assert aula.id == aula_creada.id
        assert aula.nombre == "Aula Magna"
    
    
    def test_get_by_id_no_existente(self, db: Session):
        """Test obtener aula con ID inexistente retorna None."""
        # Act
        aula = aula_repository.get_by_id(db, 999)
        
        # Assert
        assert aula is None
    
    
    def test_get_by_codigo_existente(self, db: Session, crear_aula, aula_data_1):
        """Test obtener aula por código existente."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act
        aula = aula_repository.get_by_codigo(db, "MAGNA")
        
        # Assert
        assert aula is not None
        assert aula.codigo == "MAGNA"
    
    
    def test_get_by_codigo_case_insensitive(self, db: Session, crear_aula, aula_data_1):
        """Test búsqueda por código es case-insensitive."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act - buscar con minúsculas
        aula = aula_repository.get_by_codigo(db, "magna")
        
        # Assert
        assert aula is not None
        assert aula.codigo == "MAGNA"
    
    
    def test_get_by_codigo_no_existente(self, db: Session):
        """Test obtener aula con código inexistente retorna None."""
        # Act
        aula = aula_repository.get_by_codigo(db, "NOEXISTE")
        
        # Assert
        assert aula is None
    
    
    def test_get_by_nombre_existente(self, db: Session, crear_aula, aula_data_1):
        """Test obtener aula por nombre existente."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act
        aula = aula_repository.get_by_nombre(db, "Aula Magna")
        
        # Assert
        assert aula is not None
        assert aula.nombre == "Aula Magna"
    
    
    def test_get_by_nombre_case_insensitive(self, db: Session, crear_aula, aula_data_1):
        """Test búsqueda por nombre es case-insensitive."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act - buscar con minúsculas
        aula = aula_repository.get_by_nombre(db, "aula magna")
        
        # Assert
        assert aula is not None
        assert aula.nombre == "Aula Magna"
    
    
    def test_get_multi_sin_filtros(self, db: Session, crear_aula):
        """Test listar todas las aulas sin filtros."""
        # Arrange
        crear_aula(nombre="Aula A", codigo="A", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Aula B", codigo="B", tipo=TipoAula.LABORATORIO, capacidad=30)
        db.commit()
        
        # Act
        aulas, total = aula_repository.get_multi(db)
        
        # Assert
        assert total == 2
        assert len(aulas) == 2
    
    
    def test_get_multi_con_paginacion(self, db: Session, crear_aula):
        """Test paginación funciona correctamente."""
        # Arrange - crear 3 aulas
        crear_aula(nombre="Aula A", codigo="A", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Aula B", codigo="B", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Aula C", codigo="C", tipo=TipoAula.TEORICA, capacidad=50)
        db.commit()
        
        # Act - pedir solo 2 aulas, saltando 1
        aulas, total = aula_repository.get_multi(db, skip=1, limit=2)
        
        # Assert
        assert total == 3  # Total sin paginar
        assert len(aulas) == 2  # Solo 2 en esta página
    
    
    def test_get_multi_filtro_tipo(self, db: Session, crear_aula):
        """Test filtrar por tipo de aula."""
        # Arrange
        crear_aula(nombre="Aula A", codigo="A", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Lab A", codigo="LA", tipo=TipoAula.LABORATORIO, capacidad=30)
        crear_aula(nombre="Lab B", codigo="LB", tipo=TipoAula.LABORATORIO, capacidad=25)
        db.commit()
        
        # Act
        aulas, total = aula_repository.get_multi(db, tipo=TipoAula.LABORATORIO)
        
        # Assert
        assert total == 2
        assert all(a.tipo == TipoAula.LABORATORIO for a in aulas)
    
    
    def test_get_multi_filtro_capacidad_min(self, db: Session, crear_aula):
        """Test filtrar por capacidad mínima."""
        # Arrange
        crear_aula(nombre="Aula Pequeña", codigo="P", tipo=TipoAula.TEORICA, capacidad=20)
        crear_aula(nombre="Aula Grande", codigo="G", tipo=TipoAula.TEORICA, capacidad=100)
        db.commit()
        
        # Act - solo aulas con capacidad >= 50
        aulas, total = aula_repository.get_multi(db, capacidad_min=50)
        
        # Assert
        assert total == 1
        assert aulas[0].nombre == "Aula Grande"
    
    
    def test_get_multi_filtro_capacidad_max(self, db: Session, crear_aula):
        """Test filtrar por capacidad máxima."""
        # Arrange
        crear_aula(nombre="Aula Pequeña", codigo="P", tipo=TipoAula.TEORICA, capacidad=20)
        crear_aula(nombre="Aula Grande", codigo="G", tipo=TipoAula.TEORICA, capacidad=100)
        db.commit()
        
        # Act - solo aulas con capacidad <= 50
        aulas, total = aula_repository.get_multi(db, capacidad_max=50)
        
        # Assert
        assert total == 1
        assert aulas[0].nombre == "Aula Pequeña"
    
    
    def test_get_multi_filtro_capacidad_rango(self, db: Session, crear_aula):
        """Test filtrar por rango de capacidad (min y max)."""
        # Arrange
        crear_aula(nombre="Pequeña", codigo="P", tipo=TipoAula.TEORICA, capacidad=10)
        crear_aula(nombre="Mediana", codigo="M", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Grande", codigo="G", tipo=TipoAula.TEORICA, capacidad=200)
        db.commit()
        
        # Act - aulas entre 20 y 100
        aulas, total = aula_repository.get_multi(db, capacidad_min=20, capacidad_max=100)
        
        # Assert
        assert total == 1
        assert aulas[0].nombre == "Mediana"
    
    
    def test_get_multi_busqueda_por_nombre(self, db: Session, crear_aula):
        """Test búsqueda parcial en nombre."""
        # Arrange
        crear_aula(nombre="Aula Magna", codigo="M", tipo=TipoAula.TEORICA, capacidad=200)
        crear_aula(nombre="Laboratorio", codigo="L", tipo=TipoAula.LABORATORIO, capacidad=30)
        db.commit()
        
        # Act
        aulas, total = aula_repository.get_multi(db, busqueda="Magna")
        
        # Assert
        assert total == 1
        assert aulas[0].nombre == "Aula Magna"
    
    
    def test_get_multi_busqueda_por_codigo(self, db: Session, crear_aula):
        """Test búsqueda parcial en código."""
        # Arrange
        crear_aula(nombre="Lab 1", codigo="LAB-FIS-1", tipo=TipoAula.LABORATORIO, capacidad=30)
        crear_aula(nombre="Lab 2", codigo="LAB-FIS-2", tipo=TipoAula.LABORATORIO, capacidad=30)
        crear_aula(nombre="Aula", codigo="A101", tipo=TipoAula.TEORICA, capacidad=50)
        db.commit()
        
        # Act - buscar "LAB"
        aulas, total = aula_repository.get_multi(db, busqueda="LAB")
        
        # Assert
        assert total == 2
        assert all("LAB" in a.codigo for a in aulas)
    
    
    def test_get_multi_ordenacion_por_codigo(self, db: Session, crear_aula):
        """Test ordenación por código (alfabético)."""
        # Arrange - crear en orden aleatorio
        crear_aula(nombre="Aula C", codigo="C", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Aula A", codigo="A", tipo=TipoAula.TEORICA, capacidad=50)
        crear_aula(nombre="Aula B", codigo="B", tipo=TipoAula.TEORICA, capacidad=50)
        db.commit()
        
        # Act
        aulas, total = aula_repository.get_multi(db)
        
        # Assert - debe estar ordenado por código
        assert total == 3
        assert aulas[0].codigo == "A"
        assert aulas[1].codigo == "B"
        assert aulas[2].codigo == "C"
    
    
    def test_update_aula(self, db: Session, crear_aula, aula_data_1):
        """Test actualizar aula."""
        # Arrange
        aula = crear_aula(**aula_data_1)
        db.commit()
        
        # Act - actualizar capacidad y tipo
        update_data = AulaUpdate(capacidad=150, tipo=TipoAula.SEMINARIO)
        aula_actualizada = aula_repository.update(db, aula, update_data)
        db.commit()
        
        # Assert
        assert aula_actualizada.id == aula.id
        assert aula_actualizada.capacidad == 150
        assert aula_actualizada.tipo == TipoAula.SEMINARIO
        assert aula_actualizada.nombre == "Aula Magna"  # No cambió
    
    
    def test_update_aula_borrar_capacidad(self, db: Session, crear_aula, aula_data_1):
        """Test borrar capacidad poniendo a None."""
        # Arrange
        aula = crear_aula(**aula_data_1)
        db.commit()
        
        # Act - poner capacidad a None
        update_data = AulaUpdate(capacidad=None)
        aula_actualizada = aula_repository.update(db, aula, update_data)
        db.commit()
        
        # Assert
        assert aula_actualizada.capacidad is None
    
    
    def test_delete_fisico(self, db: Session, crear_aula, aula_data_1):
        """Test eliminación física (no soft delete)."""
        # Arrange
        aula = crear_aula(**aula_data_1)
        db.commit()
        aula_id = aula.id
        
        # Act
        aula_eliminada = aula_repository.delete(db, aula_id)
        db.commit()
        
        # Assert
        assert aula_eliminada is not None
        assert aula_eliminada.id == aula_id
        
        # Verificar que ya no existe en BD
        aula_buscada = aula_repository.get_by_id(db, aula_id)
        assert aula_buscada is None
    
    
    def test_delete_no_existente(self, db: Session):
        """Test eliminar aula inexistente retorna None."""
        # Act
        aula = aula_repository.delete(db, 999)
        
        # Assert
        assert aula is None
    
    
    def test_exists_by_codigo_true(self, db: Session, crear_aula, aula_data_1):
        """Test verificar existencia de código (existe)."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act
        existe = aula_repository.exists_by_codigo(db, "MAGNA")
        
        # Assert
        assert existe is True
    
    
    def test_exists_by_codigo_false(self, db: Session):
        """Test verificar existencia de código (no existe)."""
        # Act
        existe = aula_repository.exists_by_codigo(db, "NOEXISTE")
        
        # Assert
        assert existe is False
    
    
    def test_exists_by_codigo_con_exclude_id(self, db: Session, crear_aula, aula_data_1, aula_data_2):
        """Test verificar código excluyendo un ID (para updates)."""
        # Arrange
        aula1 = crear_aula(**aula_data_1)
        aula2 = crear_aula(**aula_data_2)
        db.commit()
        
        # Act - verificar código de aula1, pero excluyendo su ID
        existe = aula_repository.exists_by_codigo(db, "MAGNA", exclude_id=aula1.id)
        
        # Assert
        assert existe is False  # No existe en otra aula
    
    
    def test_exists_by_nombre_true(self, db: Session, crear_aula, aula_data_1):
        """Test verificar existencia de nombre (existe)."""
        # Arrange
        crear_aula(**aula_data_1)
        db.commit()
        
        # Act
        existe = aula_repository.exists_by_nombre(db, "Aula Magna")
        
        # Assert
        assert existe is True
    
    
    def test_exists_by_nombre_false(self, db: Session):
        """Test verificar existencia de nombre (no existe)."""
        # Act
        existe = aula_repository.exists_by_nombre(db, "No Existe")
        
        # Assert
        assert existe is False


# ============================================================
#  TESTS DE SERVICE: Lógica de negocio
# ============================================================

class TestAulaService:
    """Tests para AulaService."""
    
    def test_create_aula_exitoso(self, db: Session, aula_data_1):
        """Test crear aula exitosamente."""
        # Arrange
        aula_data = AulaCreate(**aula_data_1)
        
        # Act
        aula = aula_service.create(db, aula_data)
        
        # Assert
        assert aula.id is not None
        assert aula.nombre == "Aula Magna"
        assert aula.codigo == "MAGNA"
    
    
    def test_create_aula_codigo_duplicado(self, db: Session, aula_data_1):
        """Test crear aula con código duplicado lanza 409."""
        # Arrange
        aula_data = AulaCreate(**aula_data_1)
        aula_service.create(db, aula_data)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.create(db, aula_data)
        
        assert exc_info.value.status_code == 409
        assert "código" in str(exc_info.value.detail).lower()
    
    
    def test_create_aula_nombre_duplicado(self, db: Session, aula_data_1):
        """Test crear aula con nombre duplicado lanza 409."""
        # Arrange
        aula_data = AulaCreate(**aula_data_1)
        aula_service.create(db, aula_data)
        
        # Act - intentar crear con mismo nombre pero distinto código
        aula_data_duplicada = AulaCreate(
            nombre="Aula Magna",  # mismo nombre
            codigo="OTRO-CODIGO",  # distinto código
            tipo=TipoAula.TEORICA,
            capacidad=100
        )
        
        # Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.create(db, aula_data_duplicada)
        
        assert exc_info.value.status_code == 409
        assert "nombre" in str(exc_info.value.detail).lower()
    
    
    def test_create_aula_sin_capacidad_permitido(self, db: Session, aula_data_3):
        """Test crear aula sin capacidad es válido."""
        # Arrange
        aula_data = AulaCreate(**aula_data_3)
        
        # Act
        aula = aula_service.create(db, aula_data)
        
        # Assert
        assert aula.id is not None
        assert aula.capacidad is None
    
    
    def test_get_by_id_existente(self, db: Session, aula_data_1):
        """Test obtener aula por ID existente."""
        # Arrange
        aula_creada = aula_service.create(db, AulaCreate(**aula_data_1))
        
        # Act
        aula = aula_service.get_by_id(db, aula_creada.id)
        
        # Assert
        assert aula.id == aula_creada.id
        assert aula.nombre == "Aula Magna"
    
    
    def test_get_by_id_no_existente(self, db: Session):
        """Test obtener aula inexistente lanza 404."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.get_by_id(db, 999)
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_by_codigo_existente(self, db: Session, aula_data_1):
        """Test obtener aula por código existente."""
        # Arrange
        aula_service.create(db, AulaCreate(**aula_data_1))
        
        # Act
        aula = aula_service.get_by_codigo(db, "MAGNA")
        
        # Assert
        assert aula.codigo == "MAGNA"
    
    
    def test_get_by_codigo_no_existente(self, db: Session):
        """Test obtener aula por código inexistente lanza 404."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.get_by_codigo(db, "NOEXISTE")
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_multi_retorna_tupla(self, db: Session, aula_data_1, aula_data_2):
        """Test get_multi retorna tupla (items, total)."""
        # Arrange
        aula_service.create(db, AulaCreate(**aula_data_1))
        aula_service.create(db, AulaCreate(**aula_data_2))
        
        # Act
        resultado = aula_service.get_multi(db)
        
        # Assert
        assert isinstance(resultado, tuple)
        items, total = resultado
        assert len(items) == 2
        assert total == 2
    
    
    def test_update_aula_exitoso(self, db: Session, aula_data_1):
        """Test actualizar aula exitosamente."""
        # Arrange
        aula = aula_service.create(db, AulaCreate(**aula_data_1))
        
        # Act
        update_data = AulaUpdate(capacidad=150)
        aula_actualizada = aula_service.update(db, aula.id, update_data)
        
        # Assert
        assert aula_actualizada.id == aula.id
        assert aula_actualizada.capacidad == 150
        assert aula_actualizada.nombre == "Aula Magna"  # No cambió
    
    
    def test_update_aula_no_existente(self, db: Session):
        """Test actualizar aula inexistente lanza 404."""
        # Arrange
        update_data = AulaUpdate(capacidad=100)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.update(db, 999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_aula_codigo_duplicado(
        self, db: Session, aula_data_1, aula_data_2
    ):
        """Test actualizar aula con código de otra aula lanza 409."""
        # Arrange
        aula1 = aula_service.create(db, AulaCreate(**aula_data_1))
        aula2 = aula_service.create(db, AulaCreate(**aula_data_2))
        
        # Act - intentar cambiar código de aula2 al de aula1
        update_data = AulaUpdate(codigo="MAGNA")
        
        # Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.update(db, aula2.id, update_data)
        
        assert exc_info.value.status_code == 409
        assert "código" in str(exc_info.value.detail).lower()
    
    
    def test_update_aula_mismo_codigo_permitido(
        self, db: Session, aula_data_1
    ):
        """Test actualizar aula con su propio código es válido."""
        # Arrange
        aula = aula_service.create(db, AulaCreate(**aula_data_1))
        
        # Act - actualizar con el mismo código
        update_data = AulaUpdate(codigo="MAGNA", capacidad=150)
        aula_actualizada = aula_service.update(db, aula.id, update_data)
        
        # Assert - no debe lanzar excepción
        assert aula_actualizada.codigo == "MAGNA"
        assert aula_actualizada.capacidad == 150
    
    
    def test_update_aula_nombre_duplicado(
        self, db: Session, aula_data_1, aula_data_2
    ):
        """Test actualizar aula con nombre de otra aula lanza 409."""
        # Arrange
        aula1 = aula_service.create(db, AulaCreate(**aula_data_1))
        aula2 = aula_service.create(db, AulaCreate(**aula_data_2))
        
        # Act - intentar cambiar nombre de aula2 al de aula1
        update_data = AulaUpdate(nombre="Aula Magna")
        
        # Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.update(db, aula2.id, update_data)
        
        assert exc_info.value.status_code == 409
        assert "nombre" in str(exc_info.value.detail).lower()
    
    
    def test_update_borrar_capacidad_con_none(
        self, db: Session, aula_data_1
    ):
        """Test borrar capacidad poniendo None."""
        # Arrange
        aula = aula_service.create(db, AulaCreate(**aula_data_1))
        
        # Act - borrar capacidad
        update_data = AulaUpdate(capacidad=None)
        aula_actualizada = aula_service.update(db, aula.id, update_data)
        
        # Assert
        assert aula_actualizada.capacidad is None
    
    
    def test_delete_aula_existente(self, db: Session, aula_data_1):
        """Test eliminar aula existente (DELETE físico)."""
        # Arrange
        aula = aula_service.create(db, AulaCreate(**aula_data_1))
        aula_id = aula.id
        
        # Act
        aula_service.delete(db, aula_id)
        
        # Assert - verificar que ya no existe
        with pytest.raises(HTTPException) as exc_info:
            aula_service.get_by_id(db, aula_id)
        
        assert exc_info.value.status_code == 404
    
    
    def test_delete_aula_no_existente(self, db: Session):
        """Test eliminar aula inexistente lanza 404."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            aula_service.delete(db, 999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TESTS DE API: Endpoints REST
# ============================================================

class TestAulaAPI:
    """Tests para endpoints REST de Aula."""
    
    def test_crear_aula_endpoint(self, client, aula_data_1):
        """Test POST /recursos/aulas."""
        # Act
        response = client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,  # Convertir enum a string
            "capacidad": aula_data_1["capacidad"]
        })
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Aula Magna"
        assert data["codigo"] == "MAGNA"
        assert "id" in data
    
    
    def test_crear_aula_codigo_duplicado_endpoint(self, client, aula_data_1):
        """Test POST con código duplicado debe retornar 409."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        
        # Act - intentar crear de nuevo con mismo código
        response = client.post("/v0/recursos/aulas", json={
            "nombre": "Otro Nombre",
            "codigo": "MAGNA",  # mismo código
            "tipo": "seminario",
            "capacidad": 50
        })
        
        # Assert
        assert response.status_code == 409
    
    
    def test_crear_aula_datos_invalidos_endpoint(self, client):
        """Test POST con datos inválidos debe retornar 422."""
        # Arrange - nombre vacío (viola min_length=1)
        datos_invalidos = {
            "nombre": "",
            "codigo": "TEST",
            "tipo": "teorica"
        }
        
        # Act
        response = client.post("/v0/recursos/aulas", json=datos_invalidos)
        
        # Assert
        assert response.status_code == 422
    
    
    def test_obtener_aula_endpoint(self, client, aula_data_1):
        """Test GET /recursos/aulas/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        aula_id = create_response.json()["id"]
        
        # Act
        response = client.get(f"/v0/recursos/aulas/{aula_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == aula_id
        assert data["nombre"] == "Aula Magna"
    
    
    def test_obtener_aula_no_existente_endpoint(self, client):
        """Test GET con ID inexistente debe retornar 404."""
        # Act
        response = client.get("/v0/recursos/aulas/999")
        
        # Assert
        assert response.status_code == 404
    
    
    def test_obtener_aula_por_codigo_endpoint(self, client, aula_data_1):
        """Test GET /recursos/aulas/codigo/{codigo}."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        
        # Act
        response = client.get("/v0/recursos/aulas/codigo/MAGNA")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["codigo"] == "MAGNA"
    
    
    def test_buscar_aulas_endpoint(self, client, aula_data_1):
        """Test GET /recursos/aulas/buscar."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        
        # Act
        response = client.get("/v0/recursos/aulas/buscar?busqueda=Magna")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["nombre"] == "Aula Magna"
    
    
    def test_buscar_aulas_sin_resultados_endpoint(self, client):
        """Test búsqueda sin resultados retorna lista vacía."""
        # Act
        response = client.get("/v0/recursos/aulas/buscar?busqueda=NoExiste")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    
    def test_listar_aulas_endpoint(self, client, aula_data_1, aula_data_2):
        """Test GET /recursos/aulas (lista)."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_2["nombre"],
            "codigo": aula_data_2["codigo"],
            "tipo": aula_data_2["tipo"].value,
            "capacidad": aula_data_2["capacidad"]
        })
        
        # Act
        response = client.get("/v0/recursos/aulas")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["page"] == 1
    
    
    def test_listar_aulas_con_paginacion_endpoint(
        self, client, aula_data_1, aula_data_2
    ):
        """Test paginación con skip y limit."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_2["nombre"],
            "codigo": aula_data_2["codigo"],
            "tipo": aula_data_2["tipo"].value,
            "capacidad": aula_data_2["capacidad"]
        })
        
        # Act
        response = client.get("/v0/recursos/aulas?skip=0&limit=1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["size"] == 1
    
    
    def test_listar_aulas_filtro_tipo_endpoint(self, client):
        """Test filtrar por tipo."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": "Aula Teórica",
            "codigo": "T1",
            "tipo": "teorica",
            "capacidad": 50
        })
        client.post("/v0/recursos/aulas", json={
            "nombre": "Laboratorio",
            "codigo": "L1",
            "tipo": "laboratorio",
            "capacidad": 30
        })
        
        # Act
        response = client.get("/v0/recursos/aulas?tipo=laboratorio")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["tipo"] == "laboratorio"
    
    
    def test_listar_aulas_filtro_capacidad_endpoint(self, client):
        """Test filtrar por rango de capacidad."""
        # Arrange
        client.post("/v0/recursos/aulas", json={
            "nombre": "Pequeña",
            "codigo": "P",
            "tipo": "teorica",
            "capacidad": 20
        })
        client.post("/v0/recursos/aulas", json={
            "nombre": "Grande",
            "codigo": "G",
            "tipo": "teorica",
            "capacidad": 200
        })
        
        # Act
        response = client.get("/v0/recursos/aulas?capacidad_min=50")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["nombre"] == "Grande"
    
    
    def test_actualizar_aula_endpoint(self, client, aula_data_1):
        """Test PUT /recursos/aulas/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        aula_id = create_response.json()["id"]
        
        # Act
        update_data = {"capacidad": 150}
        response = client.put(f"/v0/recursos/aulas/{aula_id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["capacidad"] == 150
        assert data["nombre"] == "Aula Magna"  # No cambió
    
    
    def test_actualizar_aula_borrar_capacidad_endpoint(self, client, aula_data_1):
        """Test actualizar aula borrando capacidad (null)."""
        # Arrange
        create_response = client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        aula_id = create_response.json()["id"]
        
        # Act - poner capacidad a null
        update_data = {"capacidad": None}
        response = client.put(f"/v0/recursos/aulas/{aula_id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["capacidad"] is None
    
    
    def test_actualizar_aula_no_existente_endpoint(self, client):
        """Test PUT con ID inexistente debe retornar 404."""
        # Arrange
        update_data = {"capacidad": 100}
        
        # Act
        response = client.put("/v0/recursos/aulas/999", json=update_data)
        
        # Assert
        assert response.status_code == 404
    
    
    def test_eliminar_aula_endpoint(self, client, aula_data_1):
        """Test DELETE /recursos/aulas/{id}."""
        # Arrange
        create_response = client.post("/v0/recursos/aulas", json={
            "nombre": aula_data_1["nombre"],
            "codigo": aula_data_1["codigo"],
            "tipo": aula_data_1["tipo"].value,
            "capacidad": aula_data_1["capacidad"]
        })
        aula_id = create_response.json()["id"]
        
        # Act
        response = client.delete(f"/v0/recursos/aulas/{aula_id}")
        
        # Assert
        assert response.status_code == 204
        
        # Verificar que ya no existe
        get_response = client.get(f"/v0/recursos/aulas/{aula_id}")
        assert get_response.status_code == 404
    
    
    def test_eliminar_aula_no_existente_endpoint(self, client):
        """Test DELETE con ID inexistente debe retornar 404."""
        # Act
        response = client.delete("/v0/recursos/aulas/999")
        
        # Assert
        assert response.status_code == 404


# ============================================================
#  TESTS DE EDGE CASES
# ============================================================

class TestAulaEdgeCases:
    """Tests para casos especiales y edge cases."""
    
    def test_normalizar_espacios_nombre(self, db: Session):
        """Test normalización de espacios en nombre."""
        # Arrange
        aula_data = AulaCreate(
            nombre="  Aula   con   espacios  ",
            codigo="ESPACIOS",
            tipo=TipoAula.TEORICA,
            capacidad=50
        )
        
        # Act
        aula = aula_service.create(db, aula_data)
        
        # Assert
        assert aula.nombre == "Aula con espacios"
    
    
    def test_normalizar_codigo_mayusculas(self, db: Session):
        """Test normalización de código a mayúsculas."""
        # Arrange
        aula_data = AulaCreate(
            nombre="Aula Test",
            codigo="test-123",  # minúsculas
            tipo=TipoAula.TEORICA,
            capacidad=50
        )
        
        # Act
        aula = aula_service.create(db, aula_data)
        
        # Assert
        assert aula.codigo == "TEST-123"
    
    
    def test_capacidad_cero_invalida(self, db: Session):
        """Test capacidad 0 es inválida (debe ser > 0)."""
        # Arrange
        aula_data = {
            "nombre": "Aula Test",
            "codigo": "TEST",
            "tipo": "teorica",
            "capacidad": 0  # inválido
        }
        
        # Act & Assert
        with pytest.raises(Exception):  # Validación Pydantic
            AulaCreate(**aula_data)
    
    
    def test_capacidad_negativa_invalida(self, db: Session):
        """Test capacidad negativa es inválida."""
        # Arrange
        aula_data = {
            "nombre": "Aula Test",
            "codigo": "TEST",
            "tipo": "teorica",
            "capacidad": -10  # inválido
        }
        
        # Act & Assert
        with pytest.raises(Exception):  # Validación Pydantic
            AulaCreate(**aula_data)
    
    
    def test_codigo_solo_espacios_invalido(self, db: Session):
        """Test código solo con espacios es inválido."""
        # Arrange
        aula_data = {
            "nombre": "Aula Test",
            "codigo": "   ",  # solo espacios
            "tipo": "teorica",
            "capacidad": 50
        }
        
        # Act & Assert
        with pytest.raises(Exception):  # Validación Pydantic
            AulaCreate(**aula_data)
    
    
    def test_campos_max_length(self, db: Session):
        """Test límites de longitud de campos."""
        # Arrange - nombre de 200 caracteres (límite)
        nombre_largo = "A" * 200
        aula_data = AulaCreate(
            nombre=nombre_largo,
            codigo="TEST",
            tipo=TipoAula.TEORICA,
            capacidad=50
        )
        
        # Act
        aula = aula_service.create(db, aula_data)
        
        # Assert
        assert len(aula.nombre) == 200
    
    
    def test_todos_los_tipos_aula_validos(self, db: Session):
        """Test todos los tipos de aula del enum son válidos."""
        # Arrange
        tipos = [
            TipoAula.TEORICA,
            TipoAula.LABORATORIO,
            TipoAula.INFORMATICA,
            TipoAula.SEMINARIO,
            TipoAula.TALLER,
            TipoAula.AUDITORIO,
            TipoAula.BIBLIOTECA,
            TipoAula.GIMNASIO,
            TipoAula.VIRTUAL
        ]
        
        # Act & Assert - crear un aula de cada tipo
        for i, tipo in enumerate(tipos):
            aula_data = AulaCreate(
                nombre=f"Aula {tipo.value}",
                codigo=f"TIPO-{i}",
                tipo=tipo,
                capacidad=50
            )
            aula = aula_service.create(db, aula_data)
            assert aula.tipo == tipo
    
    
    def test_multiples_aulas_mismo_tipo(self, db: Session, crear_aula):
        """Test múltiples aulas pueden tener el mismo tipo."""
        # Arrange & Act
        aula1 = crear_aula(
            nombre="Lab 1",
            codigo="L1",
            tipo=TipoAula.LABORATORIO,
            capacidad=30
        )
        aula2 = crear_aula(
            nombre="Lab 2",
            codigo="L2",
            tipo=TipoAula.LABORATORIO,
            capacidad=25
        )
        db.commit()
        
        # Assert
        assert aula1.tipo == aula2.tipo == TipoAula.LABORATORIO
