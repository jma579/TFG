"""
Tests completos para el módulo Asignatura.

Estructura:
- TestAsignaturaSchemas: Validaciones Pydantic
- TestAsignaturaRepository: Operaciones de base de datos
- TestAsignaturaService: Lógica de negocio
- TestAsignaturaRouter: Endpoints REST API

Fixtures:
- db_session: Sesión de base de datos para tests
- client: Cliente de test de FastAPI
- sample_asignatura: Asignatura de ejemplo
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import ValidationError

from main import app
from db.session import get_db
from database.models import Asignatura, Base
from constants.enums import Periodo, ModalidadAsignatura, Idioma
from modules.catalogo.schemas.asignatura import (
    AsignaturaCreate,
    AsignaturaUpdate,
    AsignaturaOut,
    AsignaturaList
)
from modules.catalogo.repositories.asignatura_repo import AsignaturaRepository
from modules.catalogo.services.asignatura_service import AsignaturaService


# ============================================================
#  CONFIGURACIÓN DE BASE DE DATOS DE PRUEBA
# ============================================================

# Base de datos en memoria para tests (SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_catalogo_asignatura.db"

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
def sample_asignatura_data():
    """Datos de ejemplo para crear una asignatura."""
    return {
        "codigo_plan": "MAT101",
        "nombre": "Matemáticas I",
        "periodo": Periodo.PRIMER_CUATRIMESTRE,
        "ects": 6,
        "modalidad": ModalidadAsignatura.PRESENCIAL,
        "idioma": Idioma.ESPAÑOL,
        "english_friendly": False,
        "activo": True
    }


@pytest.fixture
def sample_asignatura(db_session, sample_asignatura_data):
    """Crea una asignatura en la base de datos de test."""
    asignatura = Asignatura(**sample_asignatura_data)
    db_session.add(asignatura)
    db_session.commit()
    db_session.refresh(asignatura)
    return asignatura


# ============================================================
#  TEST SUITE 1: SCHEMAS (Pydantic Validations)
# ============================================================

class TestAsignaturaSchemas:
    """Tests para validaciones de schemas Pydantic."""
    
    def test_asignatura_create_valid(self):
        """Test: Crear schema válido debe funcionar."""
        data = {
            "codigo_plan": "FIS201",
            "nombre": "Física II",
            "periodo": Periodo.SEGUNDO_CUATRIMESTRE,
            "ects": 6,
            "modalidad": ModalidadAsignatura.PRESENCIAL,
            "idioma": Idioma.ESPAÑOL,
            "english_friendly": False,
            "activo": True
        }
        asignatura = AsignaturaCreate(**data)
        
        assert asignatura.codigo_plan == "FIS201"
        assert asignatura.nombre == "Física II"
        assert asignatura.periodo == Periodo.SEGUNDO_CUATRIMESTRE
        assert asignatura.ects == 6
    
    
    def test_asignatura_create_default_activo(self):
        """Test: Campo activo debe tener default True."""
        data = {
            "codigo_plan": "IA301",
            "nombre": "Inteligencia Artificial",
            "periodo": Periodo.ANUAL,
            "ects": 9,
            "modalidad": ModalidadAsignatura.ONLINE,
            "idioma": Idioma.INGLES
        }
        asignatura = AsignaturaCreate(**data)
        
        assert asignatura.activo is True
    
    
    def test_asignatura_create_default_english_friendly(self):
        """Test: Campo english_friendly debe tener default False."""
        data = {
            "codigo_plan": "BIO101",
            "nombre": "Biología",
            "periodo": Periodo.PRIMER_CUATRIMESTRE,
            "ects": 6,
            "modalidad": ModalidadAsignatura.PRESENCIAL,
            "idioma": Idioma.ESPAÑOL
        }
        asignatura = AsignaturaCreate(**data)
        
        assert asignatura.english_friendly is False
    
    
    def test_asignatura_create_codigo_empty(self):
        """Test: Código vacío debe fallar validación."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="",
                nombre="Test",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(e) for e in errors)
    
    
    def test_asignatura_create_codigo_too_long(self):
        """Test: Código > 6 caracteres debe fallar."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="ABCDEFG",  # 7 caracteres
                nombre="Test",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("at most 6 character" in str(e) for e in errors)
    
    
    def test_asignatura_create_nombre_empty(self):
        """Test: Nombre vacío debe fallar validación."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="MAT101",
                nombre="",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(e) for e in errors)
    
    
    def test_asignatura_create_nombre_too_long(self):
        """Test: Nombre > 250 caracteres debe fallar."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="MAT101",
                nombre="A" * 251,
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("at most 250 character" in str(e) for e in errors)
    
    
    def test_asignatura_create_ects_zero(self):
        """Test: ECTS = 0 debe fallar validación."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="MAT101",
                nombre="Test",
                periodo=Periodo.ANUAL,
                ects=0,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(e) for e in errors)
    
    
    def test_asignatura_create_ects_too_high(self):
        """Test: ECTS > 12 debe fallar validación."""
        with pytest.raises(ValidationError) as exc_info:
            AsignaturaCreate(
                codigo_plan="MAT101",
                nombre="Test",
                periodo=Periodo.ANUAL,
                ects=13,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL
            )
        
        errors = exc_info.value.errors()
        assert any("less than or equal to 12" in str(e) for e in errors)
    
    
    def test_normalize_codigo_uppercase(self):
        """Test: Normalización debe convertir código a mayúsculas."""
        asignatura = AsignaturaCreate(
            codigo_plan="mat101",
            nombre="Matemáticas",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL
        )
        
        assert asignatura.codigo_plan == "MAT101"
    
    
    def test_normalize_codigo_strip(self):
        """Test: Normalización debe quitar espacios del código."""
        asignatura = AsignaturaCreate(
            codigo_plan="  MAT101  ",
            nombre="Matemáticas",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL
        )
        
        assert asignatura.codigo_plan == "MAT101"
    
    
    def test_normalize_nombre_strip(self):
        """Test: Normalización debe quitar espacios al inicio/fin del nombre."""
        asignatura = AsignaturaCreate(
            codigo_plan="FIS201",
            nombre="  Física II  ",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL
        )
        
        assert asignatura.nombre == "Física II"
    
    
    def test_normalize_nombre_collapse_spaces(self):
        """Test: Normalización debe colapsar espacios múltiples en nombre."""
        asignatura = AsignaturaCreate(
            codigo_plan="FIS201",
            nombre="Física   II",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL
        )
        
        assert asignatura.nombre == "Física II"
    
    
    def test_asignatura_update_partial(self):
        """Test: Update debe permitir campos opcionales."""
        # Solo actualizar nombre
        update = AsignaturaUpdate(nombre="Nuevo Nombre")
        assert update.nombre == "Nuevo Nombre"
        assert update.codigo_plan is None
        assert update.ects is None
        assert update.activo is None
        
        # Solo actualizar ECTS
        update2 = AsignaturaUpdate(ects=9)
        assert update2.nombre is None
        assert update2.ects == 9
    
    
    def test_asignatura_out_from_orm(self, sample_asignatura):
        """Test: AsignaturaOut debe poder crearse desde objeto ORM."""
        asignatura_out = AsignaturaOut.model_validate(sample_asignatura)
        
        assert asignatura_out.id == sample_asignatura.id
        assert asignatura_out.codigo_plan == sample_asignatura.codigo_plan
        assert asignatura_out.nombre == sample_asignatura.nombre
        assert asignatura_out.ects == sample_asignatura.ects
        assert asignatura_out.activo == sample_asignatura.activo
    
    
    def test_asignatura_list_structure(self):
        """Test: AsignaturaList debe validar estructura correcta."""
        asignatura_out = AsignaturaOut(
            id=1,
            codigo_plan="MAT101",
            nombre="Matemáticas I",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            english_friendly=False,
            activo=True
        )
        
        lista = AsignaturaList(
            total=1,
            items=[asignatura_out],
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

class TestAsignaturaRepository:
    """Tests para operaciones del repositorio."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.repo = AsignaturaRepository()
    
    
    def test_get_by_id_exists(self, db_session, sample_asignatura):
        """Test: get_by_id debe devolver asignatura existente."""
        asignatura = self.repo.get_by_id(db_session, sample_asignatura.id)
        
        assert asignatura is not None
        assert asignatura.id == sample_asignatura.id
        assert asignatura.codigo_plan == sample_asignatura.codigo_plan
    
    
    def test_get_by_id_not_exists(self, db_session):
        """Test: get_by_id debe devolver None si no existe."""
        asignatura = self.repo.get_by_id(db_session, 9999)
        
        assert asignatura is None
    
    
    def test_get_by_codigo_exists(self, db_session, sample_asignatura):
        """Test: get_by_codigo debe devolver asignatura existente."""
        asignatura = self.repo.get_by_codigo(db_session, sample_asignatura.codigo_plan)
        
        assert asignatura is not None
        assert asignatura.codigo_plan == sample_asignatura.codigo_plan
        assert asignatura.nombre == sample_asignatura.nombre
    
    
    def test_get_by_codigo_not_exists(self, db_session):
        """Test: get_by_codigo debe devolver None si no existe."""
        asignatura = self.repo.get_by_codigo(db_session, "NOEXIST")
        
        assert asignatura is None
    
    
    def test_get_multi_empty(self, db_session):
        """Test: get_multi sin registros debe devolver lista vacía."""
        items, total = self.repo.get_multi(db_session)
        
        assert items == []
        assert total == 0
    
    
    def test_get_multi_with_data(self, db_session):
        """Test: get_multi debe devolver todas las asignaturas."""
        # Crear múltiples asignaturas
        asignaturas_data = [
            {
                "codigo_plan": "MAT101",
                "nombre": "Matemáticas I",
                "periodo": Periodo.PRIMER_CUATRIMESTRE,
                "ects": 6,
                "modalidad": ModalidadAsignatura.PRESENCIAL,
                "idioma": Idioma.ESPAÑOL,
                "activo": True
            },
            {
                "codigo_plan": "FIS201",
                "nombre": "Física II",
                "periodo": Periodo.SEGUNDO_CUATRIMESTRE,
                "ects": 6,
                "modalidad": ModalidadAsignatura.ONLINE,
                "idioma": Idioma.INGLES,
                "activo": True
            },
            {
                "codigo_plan": "QUIM301",
                "nombre": "Química III",
                "periodo": Periodo.ANUAL,
                "ects": 9,
                "modalidad": ModalidadAsignatura.SEMIPRESENCIAL,
                "idioma": Idioma.CATALAN,
                "activo": False
            }
        ]
        
        for data in asignaturas_data:
            db_session.add(Asignatura(**data))
        db_session.commit()
        
        items, total = self.repo.get_multi(db_session)
        
        assert total == 3
        assert len(items) == 3
    
    
    def test_get_multi_filter_activo(self, db_session):
        """Test: Filtrar por activo debe funcionar."""
        # Crear asignaturas activas e inactivas
        db_session.add(Asignatura(
            codigo_plan="ACT001",
            nombre="Activa",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="INA001",
            nombre="Inactiva",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=False
        ))
        db_session.commit()
        
        # Filtrar solo activas
        items, total = self.repo.get_multi(db_session, activo=True)
        
        assert total == 1
        assert items[0].activo is True
    
    
    def test_get_multi_filter_periodo(self, db_session):
        """Test: Filtrar por periodo debe funcionar."""
        db_session.add(Asignatura(
            codigo_plan="C1A",
            nombre="Cuatrimestral 1",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="C2A",
            nombre="Cuatrimestral 2",
            periodo=Periodo.SEGUNDO_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar solo cuatrimestral_1
        items, total = self.repo.get_multi(db_session, periodo=Periodo.PRIMER_CUATRIMESTRE)
        
        assert total == 1
        assert items[0].periodo == Periodo.PRIMER_CUATRIMESTRE
    
    
    def test_get_multi_filter_modalidad(self, db_session):
        """Test: Filtrar por modalidad debe funcionar."""
        db_session.add(Asignatura(
            codigo_plan="PRES1",
            nombre="Presencial",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="ONL1",
            nombre="Online",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.ONLINE,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar solo online
        items, total = self.repo.get_multi(db_session, modalidad=ModalidadAsignatura.ONLINE)
        
        assert total == 1
        assert items[0].modalidad == ModalidadAsignatura.ONLINE
    
    
    def test_get_multi_filter_idioma(self, db_session):
        """Test: Filtrar por idioma debe funcionar."""
        db_session.add(Asignatura(
            codigo_plan="ESP1",
            nombre="Español",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="ENG1",
            nombre="English",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.INGLES,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar solo inglés
        items, total = self.repo.get_multi(db_session, idioma=Idioma.INGLES)
        
        assert total == 1
        assert items[0].idioma == Idioma.INGLES
    
    
    def test_get_multi_pagination(self, db_session):
        """Test: Paginación debe funcionar correctamente."""
        # Crear 15 asignaturas
        for i in range(15):
            db_session.add(Asignatura(
                codigo_plan=f"ASG{i:03d}",
                nombre=f"Asignatura {i}",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL,
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
        """Test: Resultados deben estar ordenados por codigo_plan."""
        # Crear asignaturas en orden aleatorio
        codigos = ["ZZZ999", "AAA001", "MMM500"]
        for codigo in codigos:
            db_session.add(Asignatura(
                codigo_plan=codigo,
                nombre=f"Asignatura {codigo}",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL,
                activo=True
            ))
        db_session.commit()
        
        items, _ = self.repo.get_multi(db_session)
        
        # Verificar orden por codigo_plan
        codigos_obtenidos = [a.codigo_plan for a in items]
        assert codigos_obtenidos == sorted(codigos)
    
    
    def test_create_success(self, db_session):
        """Test: Crear asignatura debe funcionar."""
        data = {
            "codigo_plan": "NEW001",
            "nombre": "Nueva Asignatura",
            "periodo": Periodo.PRIMER_CUATRIMESTRE,
            "ects": 6,
            "modalidad": ModalidadAsignatura.PRESENCIAL,
            "idioma": Idioma.ESPAÑOL,
            "activo": True
        }
        
        asignatura = self.repo.create(db_session, data)
        
        assert asignatura.id is not None  # ID autogenerado
        assert asignatura.codigo_plan == "NEW001"
        assert asignatura.nombre == "Nueva Asignatura"
    
    
    def test_update_success(self, db_session, sample_asignatura):
        """Test: Actualizar asignatura debe funcionar."""
        update_data = {
            "nombre": "Nombre Actualizado",
            "ects": 9,
            "activo": False
        }
        
        updated = self.repo.update(db_session, sample_asignatura.id, update_data)
        
        assert updated.nombre == "Nombre Actualizado"
        assert updated.ects == 9
        assert updated.activo is False
        assert updated.codigo_plan == sample_asignatura.codigo_plan  # No se actualizó
    
    
    def test_update_partial(self, db_session, sample_asignatura):
        """Test: Update parcial debe actualizar solo campos enviados."""
        original_nombre = sample_asignatura.nombre
        
        update_data = {"ects": 9}
        updated = self.repo.update(db_session, sample_asignatura.id, update_data)
        
        assert updated.ects == 9
        assert updated.nombre == original_nombre  # No cambió
    
    
    def test_delete_success(self, db_session, sample_asignatura):
        """Test: Soft delete debe marcar como inactivo."""
        result = self.repo.delete(db_session, sample_asignatura.id)
        
        assert result is True
        
        # Verificar que está marcado como inactivo
        db_session.refresh(sample_asignatura)
        assert sample_asignatura.activo is False
    
    
    def test_delete_not_exists(self, db_session):
        """Test: Delete de asignatura inexistente debe devolver False."""
        result = self.repo.delete(db_session, 9999)
        
        assert result is False
    
    
    def test_exists_by_codigo_true(self, db_session, sample_asignatura):
        """Test: exists_by_codigo debe detectar existentes."""
        exists = self.repo.exists_by_codigo(
            db_session,
            sample_asignatura.codigo_plan
        )
        
        assert exists is True
    
    
    def test_exists_by_codigo_false(self, db_session):
        """Test: exists_by_codigo debe devolver False si no existe."""
        exists = self.repo.exists_by_codigo(
            db_session,
            "NOEXIST"
        )
        
        assert exists is False
    
    
    def test_exists_by_codigo_exclude_id(self, db_session, sample_asignatura):
        """Test: exclude_id debe excluir la asignatura actual."""
        # Debe devolver False porque el único match es el excluido
        exists = self.repo.exists_by_codigo(
            db_session,
            sample_asignatura.codigo_plan,
            exclude_id=sample_asignatura.id
        )
        
        assert exists is False
    
    
    def test_exists_by_nombre_true(self, db_session, sample_asignatura):
        """Test: exists_by_nombre debe detectar existentes."""
        exists = self.repo.exists_by_nombre(
            db_session,
            sample_asignatura.nombre
        )
        
        assert exists is True
    
    
    def test_exists_by_nombre_false(self, db_session):
        """Test: exists_by_nombre debe devolver False si no existe."""
        exists = self.repo.exists_by_nombre(
            db_session,
            "Asignatura Inexistente"
        )
        
        assert exists is False
    
    
    def test_exists_by_nombre_exclude_id(self, db_session, sample_asignatura):
        """Test: exclude_id debe excluir la asignatura actual en exists_by_nombre."""
        # Debe devolver False porque el único match es el excluido
        exists = self.repo.exists_by_nombre(
            db_session,
            sample_asignatura.nombre,
            exclude_id=sample_asignatura.id
        )
        
        assert exists is False


# ============================================================
#  TEST SUITE 3: SERVICE (Business Logic)
# ============================================================

class TestAsignaturaService:
    """Tests para lógica de negocio del service."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = AsignaturaService()
    
    
    def test_get_asignatura_success(self, db_session, sample_asignatura):
        """Test: get_asignatura debe devolver asignatura existente."""
        resultado = self.service.get_asignatura(db_session, sample_asignatura.id)
        
        assert isinstance(resultado, AsignaturaOut)
        assert resultado.id == sample_asignatura.id
        assert resultado.codigo_plan == sample_asignatura.codigo_plan
    
    
    def test_get_asignatura_not_found(self, db_session):
        """Test: get_asignatura debe lanzar 404 si no existe."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_asignatura(db_session, 9999)
        
        assert exc_info.value.status_code == 404
        assert "no encontrada" in exc_info.value.detail.lower()
    
    
    def test_get_asignatura_by_codigo_success(self, db_session, sample_asignatura):
        """Test: get_asignatura_by_codigo debe devolver asignatura existente."""
        resultado = self.service.get_asignatura_by_codigo(
            db_session, 
            sample_asignatura.codigo_plan
        )
        
        assert isinstance(resultado, AsignaturaOut)
        assert resultado.codigo_plan == sample_asignatura.codigo_plan
        assert resultado.nombre == sample_asignatura.nombre
    
    
    def test_get_asignatura_by_codigo_not_found(self, db_session):
        """Test: get_asignatura_by_codigo debe lanzar 404 si no existe."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_asignatura_by_codigo(db_session, "NOEXIST")
        
        assert exc_info.value.status_code == 404
        assert "no encontrada" in exc_info.value.detail.lower()
    
    
    def test_get_asignaturas_empty(self, db_session):
        """Test: get_asignaturas sin datos debe devolver lista vacía."""
        resultado = self.service.get_asignaturas(db_session)
        
        assert isinstance(resultado, AsignaturaList)
        assert resultado.total == 0
        assert resultado.items == []
    
    
    def test_get_asignaturas_with_data(self, db_session):
        """Test: get_asignaturas debe devolver lista correcta."""
        # Crear asignaturas
        for i in range(5):
            db_session.add(Asignatura(
                codigo_plan=f"ASG{i:03d}",
                nombre=f"Asignatura {i}",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL,
                activo=True
            ))
        db_session.commit()
        
        resultado = self.service.get_asignaturas(db_session)
        
        assert resultado.total == 5
        assert len(resultado.items) == 5
        assert all(isinstance(a, AsignaturaOut) for a in resultado.items)
    
    
    def test_get_asignaturas_pagination(self, db_session):
        """Test: Paginación debe calcularse correctamente."""
        # Crear 25 asignaturas
        for i in range(25):
            db_session.add(Asignatura(
                codigo_plan=f"ASG{i:03d}",
                nombre=f"Asignatura {i}",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL,
                activo=True
            ))
        db_session.commit()
        
        # Página 2 (items 10-19)
        resultado = self.service.get_asignaturas(db_session, skip=10, limit=10)
        
        assert resultado.total == 25
        assert len(resultado.items) == 10
        assert resultado.page == 2  # (skip=10 / limit=10) + 1
        assert resultado.size == 10
    
    
    def test_create_asignatura_success(self, db_session):
        """Test: Crear asignatura válida debe funcionar."""
        asignatura_in = AsignaturaCreate(
            codigo_plan="NEW001",
            nombre="Nueva Asignatura",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        
        resultado = self.service.create_asignatura(db_session, asignatura_in)
        
        assert isinstance(resultado, AsignaturaOut)
        assert resultado.id is not None
        assert resultado.codigo_plan == "NEW001"
    
    
    def test_create_asignatura_duplicate_codigo(self, db_session, sample_asignatura):
        """Test: Crear asignatura con código duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        asignatura_in = AsignaturaCreate(
            codigo_plan=sample_asignatura.codigo_plan,  # Duplicado
            nombre="Nombre Diferente",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.create_asignatura(db_session, asignatura_in)
        
        assert exc_info.value.status_code == 409
        assert "código" in exc_info.value.detail.lower()
    
    
    def test_create_asignatura_duplicate_nombre(self, db_session, sample_asignatura):
        """Test: Crear asignatura con nombre duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        asignatura_in = AsignaturaCreate(
            codigo_plan="OTRO01",  # Código diferente
            nombre=sample_asignatura.nombre,  # Duplicado
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.create_asignatura(db_session, asignatura_in)
        
        assert exc_info.value.status_code == 409
        assert "nombre" in exc_info.value.detail.lower()
    
    
    def test_update_asignatura_success(self, db_session, sample_asignatura):
        """Test: Actualizar asignatura debe funcionar."""
        update_data = AsignaturaUpdate(nombre="Nombre Actualizado", ects=9)
        
        resultado = self.service.update_asignatura(
            db_session,
            sample_asignatura.id,
            update_data
        )
        
        assert resultado.nombre == "Nombre Actualizado"
        assert resultado.ects == 9
        assert resultado.id == sample_asignatura.id
    
    
    def test_update_asignatura_not_found(self, db_session):
        """Test: Actualizar asignatura inexistente debe lanzar 404."""
        from fastapi import HTTPException
        
        update_data = AsignaturaUpdate(nombre="Test")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_asignatura(db_session, 9999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_asignatura_duplicate_codigo(self, db_session):
        """Test: Actualizar a código duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        # Crear dos asignaturas
        asig1 = Asignatura(
            codigo_plan="ASG001",
            nombre="Asignatura 1",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        asig2 = Asignatura(
            codigo_plan="ASG002",
            nombre="Asignatura 2",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        db_session.add_all([asig1, asig2])
        db_session.commit()
        
        # Intentar actualizar asig2 con el código de asig1
        update_data = AsignaturaUpdate(codigo_plan="ASG001")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_asignatura(db_session, asig2.id, update_data)
        
        assert exc_info.value.status_code == 409
        assert "código" in exc_info.value.detail.lower()
    
    
    def test_update_asignatura_duplicate_nombre(self, db_session):
        """Test: Actualizar a nombre duplicado debe lanzar 409."""
        from fastapi import HTTPException
        
        # Crear dos asignaturas
        asig1 = Asignatura(
            codigo_plan="ASG001",
            nombre="Asignatura 1",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        asig2 = Asignatura(
            codigo_plan="ASG002",
            nombre="Asignatura 2",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        )
        db_session.add_all([asig1, asig2])
        db_session.commit()
        
        # Intentar actualizar asig2 con el nombre de asig1
        update_data = AsignaturaUpdate(nombre="Asignatura 1")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update_asignatura(db_session, asig2.id, update_data)
        
        assert exc_info.value.status_code == 409
        assert "nombre" in exc_info.value.detail.lower()
    
    
    def test_delete_asignatura_success(self, db_session, sample_asignatura):
        """Test: Delete debe devolver mensaje de éxito."""
        resultado = self.service.delete_asignatura(db_session, sample_asignatura.id)
        
        assert "message" in resultado
        assert "desactivada" in resultado["message"].lower()
    
    
    def test_delete_asignatura_not_found(self, db_session):
        """Test: Delete de asignatura inexistente debe lanzar 404."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.delete_asignatura(db_session, 9999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TEST SUITE 4: ROUTER (API Endpoints)
# ============================================================

class TestAsignaturaRouter:
    """Tests para endpoints REST API."""
    
    def test_listar_asignaturas_empty(self, client):
        """Test: GET /asignaturas sin datos debe devolver lista vacía."""
        response = client.get("/v0/catalogo/asignaturas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["size"] == 100
    
    
    def test_listar_asignaturas_with_data(self, client, db_session):
        """Test: GET /asignaturas debe devolver asignaturas existentes."""
        # Crear asignaturas
        db_session.add(Asignatura(
            codigo_plan="MAT101",
            nombre="Matemáticas I",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="FIS201",
            nombre="Física II",
            periodo=Periodo.SEGUNDO_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.ONLINE,
            idioma=Idioma.INGLES,
            activo=True
        ))
        db_session.commit()
        
        response = client.get("/v0/catalogo/asignaturas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["items"]) == 2
    
    
    def test_listar_asignaturas_filter_periodo(self, client, db_session):
        """Test: Filtro por periodo debe funcionar."""
        # Crear asignaturas de diferentes periodos
        db_session.add(Asignatura(
            codigo_plan="C1A",
            nombre="Cuatrimestral 1",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="C2A",
            nombre="Cuatrimestral 2",
            periodo=Periodo.SEGUNDO_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar por periodo=primer_cuatrimestre
        response = client.get("/v0/catalogo/asignaturas?periodo=primer_cuatrimestre")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["periodo"] == "primer_cuatrimestre"
    
    
    def test_listar_asignaturas_filter_modalidad(self, client, db_session):
        """Test: Filtro por modalidad debe funcionar."""
        db_session.add(Asignatura(
            codigo_plan="PRES1",
            nombre="Presencial",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="ONL1",
            nombre="Online",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.ONLINE,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar por modalidad=online
        response = client.get("/v0/catalogo/asignaturas?modalidad=online")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["modalidad"] == "online"
    
    
    def test_listar_asignaturas_filter_idioma(self, client, db_session):
        """Test: Filtro por idioma debe funcionar."""
        db_session.add(Asignatura(
            codigo_plan="ESP1",
            nombre="Español",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="ENG1",
            nombre="English",
            periodo=Periodo.ANUAL,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.INGLES,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar por idioma=ingles (sin tilde en la URL)
        response = client.get("/v0/catalogo/asignaturas?idioma=ingles")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["idioma"] == "ingles"
    
    
    def test_listar_asignaturas_pagination(self, client, db_session):
        """Test: Paginación debe funcionar correctamente."""
        # Crear 15 asignaturas
        for i in range(15):
            db_session.add(Asignatura(
                codigo_plan=f"ASG{i:03d}",
                nombre=f"Asignatura {i}",
                periodo=Periodo.ANUAL,
                ects=6,
                modalidad=ModalidadAsignatura.PRESENCIAL,
                idioma=Idioma.ESPAÑOL,
                activo=True
            ))
        db_session.commit()
        
        # Página 2 (skip=10, limit=5)
        response = client.get("/v0/catalogo/asignaturas?skip=10&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 15
        assert len(data["items"]) == 5
        assert data["page"] == 3  # (10 / 5) + 1
    
    
    def test_obtener_asignatura_success(self, client, db_session, sample_asignatura):
        """Test: GET /asignaturas/{id} debe devolver asignatura."""
        response = client.get(f"/v0/catalogo/asignaturas/{sample_asignatura.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == sample_asignatura.id
        assert data["codigo_plan"] == sample_asignatura.codigo_plan
    
    
    def test_obtener_asignatura_not_found(self, client):
        """Test: GET /asignaturas/{id} inexistente debe devolver 404."""
        response = client.get("/v0/catalogo/asignaturas/9999")
        
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"].lower()
    
    
    def test_obtener_asignatura_invalid_id(self, client):
        """Test: ID inválido debe devolver 422."""
        response = client.get("/v0/catalogo/asignaturas/abc")
        
        assert response.status_code == 422
    
    
    def test_obtener_asignatura_by_codigo_success(self, client, db_session, sample_asignatura):
        """Test: GET /asignaturas/codigo/{codigo} debe devolver asignatura."""
        response = client.get(f"/v0/catalogo/asignaturas/codigo/{sample_asignatura.codigo_plan}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["codigo_plan"] == sample_asignatura.codigo_plan
        assert data["nombre"] == sample_asignatura.nombre
    
    
    def test_obtener_asignatura_by_codigo_not_found(self, client):
        """Test: GET /asignaturas/codigo/{codigo} inexistente debe devolver 404."""
        response = client.get("/v0/catalogo/asignaturas/codigo/NOEXST")  # 6 caracteres
        
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"].lower()
    
    
    def test_crear_asignatura_success(self, client):
        """Test: POST /asignaturas debe crear asignatura."""
        data = {
            "codigo_plan": "NEW001",
            "nombre": "Nueva Asignatura",
            "periodo": "primer_cuatrimestre",
            "ects": 6,
            "modalidad": "presencial",
            "idioma": "español",
            "activo": True
        }
        
        response = client.post("/v0/catalogo/asignaturas", json=data)
        
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["id"] is not None
        assert response_data["codigo_plan"] == "NEW001"
        assert response_data["nombre"] == "Nueva Asignatura"
    
    
    def test_crear_asignatura_invalid_data(self, client):
        """Test: Datos inválidos deben devolver 422."""
        data = {
            "codigo_plan": "",  # Vacío - inválido
            "nombre": "Test",
            "periodo": "anual",
            "ects": 6,
            "modalidad": "presencial",
            "idioma": "español"
        }
        
        response = client.post("/v0/catalogo/asignaturas", json=data)
        
        assert response.status_code == 422
    
    
    def test_crear_asignatura_duplicate_codigo(self, client, db_session, sample_asignatura):
        """Test: Crear con código duplicado debe devolver 409."""
        data = {
            "codigo_plan": sample_asignatura.codigo_plan,  # Duplicado
            "nombre": "Nombre Diferente",
            "periodo": "anual",
            "ects": 6,
            "modalidad": "presencial",
            "idioma": "español",
            "activo": True
        }
        
        response = client.post("/v0/catalogo/asignaturas", json=data)
        
        assert response.status_code == 409
        assert "código" in response.json()["detail"].lower()
    
    
    def test_crear_asignatura_duplicate_nombre(self, client, db_session, sample_asignatura):
        """Test: Crear con nombre duplicado debe devolver 409."""
        data = {
            "codigo_plan": "OTRO01",  # Código diferente
            "nombre": sample_asignatura.nombre,  # Duplicado
            "periodo": "anual",
            "ects": 6,
            "modalidad": "presencial",
            "idioma": "español",
            "activo": True
        }
        
        response = client.post("/v0/catalogo/asignaturas", json=data)
        
        assert response.status_code == 409
        assert "nombre" in response.json()["detail"].lower()
    
    
    def test_actualizar_asignatura_success(self, client, db_session, sample_asignatura):
        """Test: PUT /asignaturas/{id} debe actualizar."""
        data = {"nombre": "Nombre Actualizado", "ects": 9}
        
        response = client.put(
            f"/v0/catalogo/asignaturas/{sample_asignatura.id}",
            json=data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["nombre"] == "Nombre Actualizado"
        assert response_data["ects"] == 9
        assert response_data["id"] == sample_asignatura.id
    
    
    def test_actualizar_asignatura_not_found(self, client):
        """Test: PUT asignatura inexistente debe devolver 404."""
        data = {"nombre": "Test"}
        
        response = client.put("/v0/catalogo/asignaturas/9999", json=data)
        
        assert response.status_code == 404
    
    
    def test_eliminar_asignatura_success(self, client, db_session, sample_asignatura):
        """Test: DELETE /asignaturas/{id} debe desactivar."""
        response = client.delete(f"/v0/catalogo/asignaturas/{sample_asignatura.id}")
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verificar que está inactiva
        db_session.refresh(sample_asignatura)
        assert sample_asignatura.activo is False
    
    
    def test_eliminar_asignatura_not_found(self, client):
        """Test: DELETE asignatura inexistente debe devolver 404."""
        response = client.delete("/v0/catalogo/asignaturas/9999")
        
        assert response.status_code == 404


# ============================================================
#  TESTS DE INTEGRACIÓN
# ============================================================

class TestIntegracion:
    """Tests de flujo completo end-to-end."""
    
    def test_flujo_crud_completo(self, client, db_session):
        """
        Test de integración: Flujo completo CREATE → READ → UPDATE → DELETE.
        """
        # 1. CREATE: Crear nueva asignatura
        create_data = {
            "codigo_plan": "INT001",
            "nombre": "Asignatura de Integración",
            "periodo": "anual",
            "ects": 6,
            "modalidad": "presencial",
            "idioma": "español",
            "activo": True
        }
        
        create_response = client.post("/v0/catalogo/asignaturas", json=create_data)
        assert create_response.status_code == 201
        asignatura_id = create_response.json()["id"]
        
        # 2. READ: Obtener asignatura creada
        get_response = client.get(f"/v0/catalogo/asignaturas/{asignatura_id}")
        assert get_response.status_code == 200
        assert get_response.json()["codigo_plan"] == "INT001"
        
        # 3. UPDATE: Actualizar asignatura
        update_data = {"nombre": "Asignatura Actualizada", "ects": 9}
        update_response = client.put(
            f"/v0/catalogo/asignaturas/{asignatura_id}",
            json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["nombre"] == "Asignatura Actualizada"
        assert update_response.json()["ects"] == 9
        
        # 4. DELETE: Desactivar asignatura
        delete_response = client.delete(f"/v0/catalogo/asignaturas/{asignatura_id}")
        assert delete_response.status_code == 200
        
        # 5. VERIFY: Verificar que está inactiva
        verify_response = client.get(f"/v0/catalogo/asignaturas/{asignatura_id}")
        assert verify_response.status_code == 200
        assert verify_response.json()["activo"] is False
    
    
    def test_filtros_combinados(self, client, db_session):
        """Test: Múltiples filtros deben funcionar en conjunto."""
        # Crear asignaturas con diferentes características
        db_session.add(Asignatura(
            codigo_plan="TEST1",
            nombre="Test 1",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="TEST2",
            nombre="Test 2",
            periodo=Periodo.PRIMER_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.ONLINE,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.add(Asignatura(
            codigo_plan="TEST3",
            nombre="Test 3",
            periodo=Periodo.SEGUNDO_CUATRIMESTRE,
            ects=6,
            modalidad=ModalidadAsignatura.PRESENCIAL,
            idioma=Idioma.ESPAÑOL,
            activo=True
        ))
        db_session.commit()
        
        # Filtrar: periodo=primer_cuatrimestre AND modalidad=presencial
        response = client.get(
            "/v0/catalogo/asignaturas?periodo=primer_cuatrimestre&modalidad=presencial"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1  # Solo TEST1 cumple ambas condiciones
        assert data["items"][0]["codigo_plan"] == "TEST1"


# ============================================================
#  EJECUCIÓN DE TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
