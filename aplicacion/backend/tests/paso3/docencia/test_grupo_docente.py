"""
Tests completos para la entidad GrupoDocente.

Estructura de tests:
1. TestGrupoDocenteRepository: Tests de capa de datos (19 tests)
   - CRUD básico
   - Búsquedas (por ID, por asignatura+codigo)
   - Filtros (asignatura_id, tipo, curso, turno)
   - Validaciones (exists_by_asignatura_codigo)
   - Delete físico

2. TestGrupoDocenteService: Tests de lógica de negocio (15 tests)
   - Validación de FK asignatura_id
   - Validación de unicidad compuesta (asignatura_id, codigo)
   - Casos de error (404, 409)
   - Delete con FK constraint

3. TestGrupoDocenteAPI: Tests de endpoints REST (17 tests)
   - GET /grupos-docentes (con filtros)
   - GET /grupos-docentes/{id}
   - GET /grupos-docentes/asignatura/{asignatura_id}/codigo/{codigo}
   - POST /grupos-docentes
   - PUT /grupos-docentes/{id}
   - DELETE /grupos-docentes/{id}

4. TestGrupoDocenteEdgeCases: Tests de casos límite (6 tests)
   - Normalización de código a mayúsculas
   - Normalización de espacios
   - Validaciones de campos opcionales
   - Múltiples grupos por asignatura

Total: 57 tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from database.models import Base, GrupoDocente, Asignatura, Programa, Aula, Profesor  # Import todos los modelos necesarios
from main import app
from db.session import get_db
from modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from modules.docencia.services.grupo_docente_service import grupo_docente_service
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate
)
from constants.enums import (
    TipoGrupoDocente, TipoPrograma, Periodo, ModalidadAsignatura, Idioma
)


# ============================================================
#  CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ============================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================
#  FIXTURES
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Crear todas las tablas al inicio de la sesión de tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Fixture que proporciona una sesión de BD para cada test.
    
    - Usa transacciones para aislar cada test
    - Hace rollback automático después del test
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """
    Fixture que proporciona un cliente de test de FastAPI.
    
    Sobrescribe la dependencia get_db para usar la BD de test.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def programa_data(db):
    """Fixture que crea un programa de prueba."""
    programa = Programa(
        nombre="Grado en Ingeniería Informática",
        tipo=TipoPrograma.GRADO,
        activo=True
    )
    db.add(programa)
    db.commit()
    db.refresh(programa)
    return programa


@pytest.fixture
def asignatura_data_1(db, programa_data):
    """Fixture que crea una asignatura de prueba."""
    asignatura = Asignatura(
        codigo_plan="PROG01",
        nombre="Programación",
        periodo=Periodo.PRIMER_CUATRIMESTRE,
        ects=6,
        modalidad=ModalidadAsignatura.PRESENCIAL,
        idioma=Idioma.ESPAÑOL,
        activo=True
    )
    db.add(asignatura)
    db.commit()
    db.refresh(asignatura)
    return asignatura


@pytest.fixture
def asignatura_data_2(db, programa_data):
    """Fixture que crea una segunda asignatura de prueba."""
    asignatura = Asignatura(
        codigo_plan="BD02",
        nombre="Bases de Datos",
        periodo=Periodo.SEGUNDO_CUATRIMESTRE,
        ects=6,
        modalidad=ModalidadAsignatura.PRESENCIAL,
        idioma=Idioma.ESPAÑOL,
        activo=True
    )
    db.add(asignatura)
    db.commit()
    db.refresh(asignatura)
    return asignatura


@pytest.fixture
def grupo_data_1(asignatura_data_1):
    """Fixture con datos de prueba para crear un grupo."""
    return GrupoDocenteCreate(
        asignatura_id=asignatura_data_1.id,
        codigo="T1",
        tipo=TipoGrupoDocente.TEORIA,
        curso=1,
        turno="mañana"
    )


@pytest.fixture
def grupo_data_2(asignatura_data_1):
    """Fixture con datos de prueba para crear un segundo grupo."""
    return GrupoDocenteCreate(
        asignatura_id=asignatura_data_1.id,
        codigo="P1",
        tipo=TipoGrupoDocente.PRACTICA,
        curso=1,
        turno="tarde"
    )


@pytest.fixture
def grupo_data_3(asignatura_data_2):
    """Fixture con datos de prueba para crear un tercer grupo (otra asignatura)."""
    return GrupoDocenteCreate(
        asignatura_id=asignatura_data_2.id,
        codigo="T1",  # Mismo código pero diferente asignatura
        tipo=TipoGrupoDocente.TEORIA,
        curso=2,
        turno="mañana"
    )


# ============================================================
#  FUNCIONES HELPER
# ============================================================

def crear_grupo(db, grupo_data: GrupoDocenteCreate) -> GrupoDocente:
    """Helper para crear un grupo en la BD."""
    grupo = GrupoDocente(**grupo_data.model_dump())
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


# ============================================================
#  TESTS DE REPOSITORY
# ============================================================

class TestGrupoDocenteRepository:
    """Tests de la capa de datos (repository)."""
    
    def test_create_grupo(self, db, grupo_data_1):
        """Test crear grupo básico."""
        grupo = grupo_docente_repository.create(db, grupo_data_1)
        
        assert grupo.id is not None
        assert grupo.asignatura_id == grupo_data_1.asignatura_id
        assert grupo.codigo == grupo_data_1.codigo
        assert grupo.tipo == grupo_data_1.tipo
        assert grupo.curso == grupo_data_1.curso
        assert grupo.turno == grupo_data_1.turno
    
    
    def test_create_grupo_sin_curso_turno(self, db, asignatura_data_1):
        """Test crear grupo solo con campos obligatorios."""
        grupo_data = GrupoDocenteCreate(
            asignatura_id=asignatura_data_1.id,
            codigo="LAB1",
            tipo=TipoGrupoDocente.LABORATORIO
        )
        
        grupo = grupo_docente_repository.create(db, grupo_data)
        
        assert grupo.id is not None
        assert grupo.curso is None
        assert grupo.turno is None
    
    
    def test_get_by_id_existente(self, db, grupo_data_1):
        """Test obtener grupo por ID existente."""
        grupo_creado = crear_grupo(db, grupo_data_1)
        
        grupo = grupo_docente_repository.get_by_id(db, grupo_creado.id)
        
        assert grupo is not None
        assert grupo.id == grupo_creado.id
        assert grupo.codigo == grupo_data_1.codigo
    
    
    def test_get_by_id_no_existente(self, db):
        """Test obtener grupo por ID que no existe."""
        grupo = grupo_docente_repository.get_by_id(db, 9999)
        
        assert grupo is None
    
    
    def test_get_by_asignatura_codigo_existente(self, db, grupo_data_1):
        """Test obtener grupo por constraint único (asignatura_id, codigo)."""
        crear_grupo(db, grupo_data_1)
        
        grupo = grupo_docente_repository.get_by_asignatura_codigo(
            db,
            asignatura_id=grupo_data_1.asignatura_id,
            codigo=grupo_data_1.codigo
        )
        
        assert grupo is not None
        assert grupo.asignatura_id == grupo_data_1.asignatura_id
        assert grupo.codigo == grupo_data_1.codigo
    
    
    def test_get_by_asignatura_codigo_case_insensitive(self, db, grupo_data_1):
        """Test búsqueda por código case-insensitive."""
        crear_grupo(db, grupo_data_1)
        
        # Buscar con código en minúsculas
        grupo = grupo_docente_repository.get_by_asignatura_codigo(
            db,
            asignatura_id=grupo_data_1.asignatura_id,
            codigo="t1"  # minúsculas
        )
        
        assert grupo is not None
        assert grupo.codigo == "T1"  # En DB está en mayúsculas
    
    
    def test_get_by_asignatura_codigo_no_existente(self, db, asignatura_data_1):
        """Test buscar grupo que no existe."""
        grupo = grupo_docente_repository.get_by_asignatura_codigo(
            db,
            asignatura_id=asignatura_data_1.id,
            codigo="NOEXISTE"
        )
        
        assert grupo is None
    
    
    def test_get_multi_sin_filtros(self, db, grupo_data_1, grupo_data_2):
        """Test listar todos los grupos sin filtros."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        
        items, total = grupo_docente_repository.get_multi(db)
        
        assert total == 2
        assert len(items) == 2
    
    
    def test_get_multi_con_paginacion(self, db, grupo_data_1, grupo_data_2, grupo_data_3):
        """Test paginación en listar grupos."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        crear_grupo(db, grupo_data_3)
        
        # Primera página
        items, total = grupo_docente_repository.get_multi(db, skip=0, limit=2)
        assert total == 3
        assert len(items) == 2
        
        # Segunda página
        items, total = grupo_docente_repository.get_multi(db, skip=2, limit=2)
        assert total == 3
        assert len(items) == 1
    
    
    def test_get_multi_filtro_asignatura_id(self, db, grupo_data_1, grupo_data_2, grupo_data_3):
        """Test filtrar grupos por asignatura."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        crear_grupo(db, grupo_data_3)  # Diferente asignatura
        
        items, total = grupo_docente_repository.get_multi(
            db,
            asignatura_id=grupo_data_1.asignatura_id
        )
        
        assert total == 2  # Solo los de la primera asignatura
        assert all(g.asignatura_id == grupo_data_1.asignatura_id for g in items)
    
    
    def test_get_multi_filtro_tipo(self, db, grupo_data_1, grupo_data_2):
        """Test filtrar grupos por tipo."""
        crear_grupo(db, grupo_data_1)  # TEORIA
        crear_grupo(db, grupo_data_2)  # PRACTICA
        
        items, total = grupo_docente_repository.get_multi(
            db,
            tipo=TipoGrupoDocente.TEORIA
        )
        
        assert total == 1
        assert items[0].tipo == TipoGrupoDocente.TEORIA
    
    
    def test_get_multi_filtro_curso(self, db, grupo_data_1, grupo_data_3):
        """Test filtrar grupos por curso."""
        crear_grupo(db, grupo_data_1)  # curso=1
        crear_grupo(db, grupo_data_3)  # curso=2
        
        items, total = grupo_docente_repository.get_multi(db, curso=1)
        
        assert total == 1
        assert items[0].curso == 1
    
    
    def test_get_multi_filtro_turno(self, db, grupo_data_1, grupo_data_2):
        """Test filtrar grupos por turno (búsqueda parcial)."""
        crear_grupo(db, grupo_data_1)  # turno="mañana"
        crear_grupo(db, grupo_data_2)  # turno="tarde"
        
        items, total = grupo_docente_repository.get_multi(db, turno="maña")
        
        assert total == 1
        assert "mañana" in items[0].turno.lower()
    
    
    def test_get_multi_ordenacion_por_asignatura_codigo(self, db, grupo_data_1, grupo_data_2):
        """Test que los grupos se ordenan por asignatura_id y luego por codigo."""
        crear_grupo(db, grupo_data_2)  # P1
        crear_grupo(db, grupo_data_1)  # T1
        
        items, total = grupo_docente_repository.get_multi(db)
        
        # Deben estar ordenados por codigo: P1, T1
        assert items[0].codigo == "P1"
        assert items[1].codigo == "T1"
    
    
    def test_update_grupo(self, db, grupo_data_1):
        """Test actualizar grupo."""
        grupo = crear_grupo(db, grupo_data_1)
        
        update_data = GrupoDocenteUpdate(
            turno="tarde",
            tipo=TipoGrupoDocente.LABORATORIO
        )
        
        grupo_actualizado = grupo_docente_repository.update(db, grupo, update_data)
        
        assert grupo_actualizado.turno == "tarde"
        assert grupo_actualizado.tipo == TipoGrupoDocente.LABORATORIO
        assert grupo_actualizado.codigo == grupo_data_1.codigo  # No cambió
    
    
    def test_update_grupo_borrar_campo_opcional(self, db, grupo_data_1):
        """Test borrar campo opcional poniendo None."""
        grupo = crear_grupo(db, grupo_data_1)
        
        update_data = GrupoDocenteUpdate(curso=None, turno=None)
        
        grupo_actualizado = grupo_docente_repository.update(db, grupo, update_data)
        
        assert grupo_actualizado.curso is None
        assert grupo_actualizado.turno is None
    
    
    def test_delete_fisico(self, db, grupo_data_1):
        """Test eliminar grupo (DELETE físico)."""
        grupo = crear_grupo(db, grupo_data_1)
        grupo_id = grupo.id
        
        grupo_docente_repository.delete(db, grupo_id)
        db.commit()
        
        # Verificar que ya no existe
        grupo = grupo_docente_repository.get_by_id(db, grupo_id)
        assert grupo is None
    
    
    def test_delete_no_existente(self, db):
        """Test eliminar grupo que no existe."""
        resultado = grupo_docente_repository.delete(db, 9999)
        
        assert resultado is None
    
    
    def test_exists_by_asignatura_codigo_true(self, db, grupo_data_1):
        """Test verificar existencia de grupo (existe)."""
        crear_grupo(db, grupo_data_1)
        
        existe = grupo_docente_repository.exists_by_asignatura_codigo(
            db,
            asignatura_id=grupo_data_1.asignatura_id,
            codigo=grupo_data_1.codigo
        )
        
        assert existe is True
    
    
    def test_exists_by_asignatura_codigo_false(self, db, asignatura_data_1):
        """Test verificar existencia de grupo (no existe)."""
        existe = grupo_docente_repository.exists_by_asignatura_codigo(
            db,
            asignatura_id=asignatura_data_1.id,
            codigo="NOEXISTE"
        )
        
        assert existe is False
    
    
    def test_exists_by_asignatura_codigo_con_exclude_id(self, db, grupo_data_1, grupo_data_2):
        """Test verificar existencia excluyendo un ID (para updates)."""
        grupo1 = crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        
        # Mismo código que grupo1 pero excluyendo su ID
        existe = grupo_docente_repository.exists_by_asignatura_codigo(
            db,
            asignatura_id=grupo_data_1.asignatura_id,
            codigo=grupo_data_1.codigo,
            exclude_id=grupo1.id
        )
        
        assert existe is False  # No existe otro con ese código


# ============================================================
#  TESTS DE SERVICE
# ============================================================

class TestGrupoDocenteService:
    """Tests de lógica de negocio (service)."""
    
    def test_create_grupo_exitoso(self, db, grupo_data_1):
        """Test crear grupo exitosamente."""
        grupo = grupo_docente_service.create(db, grupo_data_1)
        
        assert grupo.id is not None
        assert grupo.asignatura_id == grupo_data_1.asignatura_id
        assert grupo.codigo == grupo_data_1.codigo
    
    
    def test_create_grupo_asignatura_no_existe(self, db):
        """Test crear grupo con asignatura que no existe (FK)."""
        grupo_data = GrupoDocenteCreate(
            asignatura_id=9999,  # No existe
            codigo="T1",
            tipo=TipoGrupoDocente.TEORIA
        )
        
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.create(db, grupo_data)
        
        assert exc_info.value.status_code == 404
        assert "Asignatura con id 9999 no encontrada" in str(exc_info.value.detail)
    
    
    def test_create_grupo_codigo_duplicado_misma_asignatura(self, db, grupo_data_1):
        """Test crear grupo con código duplicado para la misma asignatura."""
        # Crear primer grupo
        grupo_docente_service.create(db, grupo_data_1)
        
        # Intentar crear otro con el mismo código en la misma asignatura
        grupo_duplicado = GrupoDocenteCreate(
            asignatura_id=grupo_data_1.asignatura_id,
            codigo=grupo_data_1.codigo,
            tipo=TipoGrupoDocente.PRACTICA
        )
        
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.create(db, grupo_duplicado)
        
        assert exc_info.value.status_code == 409
        assert "Ya existe un grupo con código" in str(exc_info.value.detail)
    
    
    def test_create_grupo_mismo_codigo_diferente_asignatura(self, db, grupo_data_1, grupo_data_3):
        """Test crear grupos con mismo código pero diferente asignatura (OK)."""
        # Crear primer grupo en asignatura 1
        grupo1 = grupo_docente_service.create(db, grupo_data_1)
        
        # Crear segundo grupo con mismo código pero asignatura 2
        grupo2 = grupo_docente_service.create(db, grupo_data_3)
        
        assert grupo1.codigo == grupo2.codigo  # Mismo código
        assert grupo1.asignatura_id != grupo2.asignatura_id  # Diferente asignatura
    
    
    def test_get_by_id_existente(self, db, grupo_data_1):
        """Test obtener grupo por ID."""
        grupo_creado = grupo_docente_service.create(db, grupo_data_1)
        
        grupo = grupo_docente_service.get_by_id(db, grupo_creado.id)
        
        assert grupo.id == grupo_creado.id
        assert grupo.codigo == grupo_data_1.codigo
    
    
    def test_get_by_id_no_existente(self, db):
        """Test obtener grupo que no existe."""
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.get_by_id(db, 9999)
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_by_asignatura_codigo_existente(self, db, grupo_data_1):
        """Test obtener grupo por asignatura y código."""
        grupo_docente_service.create(db, grupo_data_1)
        
        grupo = grupo_docente_service.get_by_asignatura_codigo(
            db,
            asignatura_id=grupo_data_1.asignatura_id,
            codigo=grupo_data_1.codigo
        )
        
        assert grupo.asignatura_id == grupo_data_1.asignatura_id
        assert grupo.codigo == grupo_data_1.codigo
    
    
    def test_get_by_asignatura_codigo_no_existente(self, db, asignatura_data_1):
        """Test obtener grupo que no existe por asignatura+código."""
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.get_by_asignatura_codigo(
                db,
                asignatura_id=asignatura_data_1.id,
                codigo="NOEXISTE"
            )
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_multi_retorna_tupla(self, db, grupo_data_1):
        """Test que get_multi retorna (items, total)."""
        grupo_docente_service.create(db, grupo_data_1)
        
        items, total = grupo_docente_service.get_multi(db)
        
        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total > 0
    
    
    def test_update_grupo_exitoso(self, db, grupo_data_1):
        """Test actualizar grupo exitosamente."""
        grupo = grupo_docente_service.create(db, grupo_data_1)
        
        update_data = GrupoDocenteUpdate(turno="noche", curso=2)
        
        grupo_actualizado = grupo_docente_service.update(db, grupo.id, update_data)
        
        assert grupo_actualizado.turno == "noche"
        assert grupo_actualizado.curso == 2
    
    
    def test_update_grupo_no_existente(self, db):
        """Test actualizar grupo que no existe."""
        update_data = GrupoDocenteUpdate(turno="tarde")
        
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.update(db, 9999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_grupo_codigo_duplicado(self, db, grupo_data_1, grupo_data_2):
        """Test actualizar grupo con código que ya existe en esa asignatura."""
        grupo1 = grupo_docente_service.create(db, grupo_data_1)  # T1
        grupo2 = grupo_docente_service.create(db, grupo_data_2)  # P1
        
        # Intentar cambiar P1 a T1 (duplicado)
        update_data = GrupoDocenteUpdate(codigo="T1")
        
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.update(db, grupo2.id, update_data)
        
        assert exc_info.value.status_code == 409
    
    
    def test_update_grupo_mismo_codigo_permitido(self, db, grupo_data_1):
        """Test actualizar grupo manteniendo su propio código (OK)."""
        grupo = grupo_docente_service.create(db, grupo_data_1)
        
        # Actualizar con el mismo código (no debe dar error)
        update_data = GrupoDocenteUpdate(codigo="T1", turno="tarde")
        
        grupo_actualizado = grupo_docente_service.update(db, grupo.id, update_data)
        
        assert grupo_actualizado.codigo == "T1"
        assert grupo_actualizado.turno == "tarde"
    
    
    def test_delete_grupo_existente(self, db, grupo_data_1):
        """Test eliminar grupo existente."""
        grupo = grupo_docente_service.create(db, grupo_data_1)
        
        grupo_docente_service.delete(db, grupo.id)
        
        # Verificar que ya no existe
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.get_by_id(db, grupo.id)
        
        assert exc_info.value.status_code == 404
    
    
    def test_delete_grupo_no_existente(self, db):
        """Test eliminar grupo que no existe."""
        with pytest.raises(Exception) as exc_info:
            grupo_docente_service.delete(db, 9999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TESTS DE API
# ============================================================

class TestGrupoDocenteAPI:
    """Tests de endpoints REST."""
    
    def test_crear_grupo_endpoint(self, client, db, asignatura_data_1):
        """Test POST /grupos-docentes."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "T1",
                "tipo": "teoria",
                "curso": 1,
                "turno": "mañana"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "T1"
        assert data["tipo"] == "teoria"
        assert "id" in data
    
    
    def test_crear_grupo_codigo_duplicado_endpoint(self, client, db, grupo_data_1):
        """Test POST con código duplicado."""
        # Crear primer grupo
        client.post(
            "/v0/docencia/grupos-docentes",
            json=grupo_data_1.model_dump()
        )
        
        # Intentar crear duplicado
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json=grupo_data_1.model_dump()
        )
        
        assert response.status_code == 409
        assert "Ya existe un grupo con código" in response.json()["detail"]
    
    
    def test_crear_grupo_datos_invalidos_endpoint(self, client):
        """Test POST con datos inválidos."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": -1,  # Inválido
                "codigo": "",  # Vacío
                "tipo": "invalido"  # No existe en enum
            }
        )
        
        assert response.status_code == 422
    
    
    def test_obtener_grupo_endpoint(self, client, db, grupo_data_1):
        """Test GET /grupos-docentes/{id}."""
        grupo = crear_grupo(db, grupo_data_1)
        
        response = client.get(f"/v0/docencia/grupos-docentes/{grupo.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == grupo.id
        assert data["codigo"] == grupo_data_1.codigo
    
    
    def test_obtener_grupo_no_existente_endpoint(self, client):
        """Test GET con ID que no existe."""
        response = client.get("/v0/docencia/grupos-docentes/9999")
        
        assert response.status_code == 404
    
    
    def test_obtener_grupo_por_asignatura_codigo_endpoint(self, client, db, grupo_data_1):
        """Test GET /grupos-docentes/asignatura/{asignatura_id}/codigo/{codigo}."""
        crear_grupo(db, grupo_data_1)
        
        response = client.get(
            f"/v0/docencia/grupos-docentes/asignatura/{grupo_data_1.asignatura_id}/codigo/{grupo_data_1.codigo}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["asignatura_id"] == grupo_data_1.asignatura_id
        assert data["codigo"] == grupo_data_1.codigo
    
    
    def test_listar_grupos_endpoint(self, client, db, grupo_data_1, grupo_data_2):
        """Test GET /grupos-docentes."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        
        response = client.get("/v0/docencia/grupos-docentes")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2
    
    
    def test_listar_grupos_con_paginacion_endpoint(self, client, db, grupo_data_1, grupo_data_2, grupo_data_3):
        """Test GET con paginación."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        crear_grupo(db, grupo_data_3)
        
        response = client.get("/v0/docencia/grupos-docentes?skip=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2
    
    
    def test_listar_grupos_filtro_asignatura_endpoint(self, client, db, grupo_data_1, grupo_data_2, grupo_data_3):
        """Test GET con filtro por asignatura."""
        crear_grupo(db, grupo_data_1)
        crear_grupo(db, grupo_data_2)
        crear_grupo(db, grupo_data_3)  # Diferente asignatura
        
        response = client.get(
            f"/v0/docencia/grupos-docentes?asignatura_id={grupo_data_1.asignatura_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Solo los de esa asignatura
    
    
    def test_listar_grupos_filtro_tipo_endpoint(self, client, db, grupo_data_1, grupo_data_2):
        """Test GET con filtro por tipo."""
        crear_grupo(db, grupo_data_1)  # TEORIA
        crear_grupo(db, grupo_data_2)  # PRACTICA
        
        response = client.get("/v0/docencia/grupos-docentes?tipo=teoria")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["tipo"] == "teoria"
    
    
    def test_listar_grupos_filtro_curso_endpoint(self, client, db, grupo_data_1, grupo_data_3):
        """Test GET con filtro por curso."""
        crear_grupo(db, grupo_data_1)  # curso=1
        crear_grupo(db, grupo_data_3)  # curso=2
        
        response = client.get("/v0/docencia/grupos-docentes?curso=1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["curso"] == 1
    
    
    def test_listar_grupos_filtro_turno_endpoint(self, client, db, grupo_data_1, grupo_data_2):
        """Test GET con filtro por turno."""
        crear_grupo(db, grupo_data_1)  # turno="mañana"
        crear_grupo(db, grupo_data_2)  # turno="tarde"
        
        response = client.get("/v0/docencia/grupos-docentes?turno=maña")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "mañana" in data["items"][0]["turno"].lower()
    
    
    def test_actualizar_grupo_endpoint(self, client, db, grupo_data_1):
        """Test PUT /grupos-docentes/{id}."""
        grupo = crear_grupo(db, grupo_data_1)
        
        response = client.put(
            f"/v0/docencia/grupos-docentes/{grupo.id}",
            json={"turno": "noche", "curso": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["turno"] == "noche"
        assert data["curso"] == 3
    
    
    def test_actualizar_grupo_no_existente_endpoint(self, client):
        """Test PUT con ID que no existe."""
        response = client.put(
            "/v0/docencia/grupos-docentes/9999",
            json={"turno": "tarde"}
        )
        
        assert response.status_code == 404
    
    
    def test_eliminar_grupo_endpoint(self, client, db, grupo_data_1):
        """Test DELETE /grupos-docentes/{id}."""
        grupo = crear_grupo(db, grupo_data_1)
        
        response = client.delete(f"/v0/docencia/grupos-docentes/{grupo.id}")
        
        assert response.status_code == 204
        
        # Verificar que ya no existe
        response = client.get(f"/v0/docencia/grupos-docentes/{grupo.id}")
        assert response.status_code == 404
    
    
    def test_eliminar_grupo_no_existente_endpoint(self, client):
        """Test DELETE con ID que no existe."""
        response = client.delete("/v0/docencia/grupos-docentes/9999")
        
        assert response.status_code == 404


# ============================================================
#  TESTS DE CASOS LÍMITE
# ============================================================

class TestGrupoDocenteEdgeCases:
    """Tests de casos límite y validaciones especiales."""
    
    def test_normalizar_espacios_turno(self, client, db, asignatura_data_1):
        """Test normalización de espacios en turno."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "T1",
                "tipo": "teoria",
                "turno": "  mañana   temprano  "  # Múltiples espacios
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["turno"] == "mañana temprano"  # Normalizado
    
    
    def test_normalizar_codigo_mayusculas(self, client, db, asignatura_data_1):
        """Test que el código se normaliza a mayúsculas."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "t1",  # Minúsculas
                "tipo": "teoria"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "T1"  # Mayúsculas
    
    
    def test_codigo_solo_espacios_invalido(self, client, db, asignatura_data_1):
        """Test que código de solo espacios es inválido."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "   ",  # Solo espacios
                "tipo": "teoria"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_campos_max_length(self, client, db, asignatura_data_1):
        """Test límites de longitud de campos."""
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "A" * 50,  # Max 50
                "tipo": "teoria",
                "turno": "X" * 30  # Max 30
            }
        )
        
        assert response.status_code == 201
        
        # Probar exceder límite
        response = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "A" * 51,  # Excede 50
                "tipo": "teoria"
            }
        )
        
        assert response.status_code == 422
    
    
    def test_todos_los_tipos_grupo_validos(self, client, db, asignatura_data_1):
        """Test que todos los valores del enum TipoGrupoDocente son válidos."""
        tipos = ["teoria", "practica", "laboratorio", "seminario", "taller", "tutoria", "examen"]
        
        for idx, tipo in enumerate(tipos):
            response = client.post(
                "/v0/docencia/grupos-docentes",
                json={
                    "asignatura_id": asignatura_data_1.id,
                    "codigo": f"G{idx}",
                    "tipo": tipo
                }
            )
            
            assert response.status_code == 201, f"Tipo {tipo} debería ser válido"
            assert response.json()["tipo"] == tipo
    
    
    def test_multiples_grupos_mismo_tipo(self, client, db, asignatura_data_1):
        """Test que se pueden crear múltiples grupos del mismo tipo."""
        response1 = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "T1",
                "tipo": "teoria"
            }
        )
        
        response2 = client.post(
            "/v0/docencia/grupos-docentes",
            json={
                "asignatura_id": asignatura_data_1.id,
                "codigo": "T2",
                "tipo": "teoria"  # Mismo tipo
            }
        )
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response1.json()["tipo"] == response2.json()["tipo"]
