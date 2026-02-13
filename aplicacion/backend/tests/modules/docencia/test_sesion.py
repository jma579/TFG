"""
Tests completos para la entidad Sesion.

Estructura de tests:
- TestSesionRepository: Tests de la capa de datos (repository)
- TestSesionService: Tests de la lógica de negocio (service)
- TestSesionAPI: Tests de los endpoints REST
- TestSesionEdgeCases: Tests de casos límite y validaciones

Cobertura:
- CRUD completo (create, read, update, delete)
- Búsquedas especializadas (por grupo, aula, profesor, fechas)
- Filtros múltiples (modalidad, tipo_recurrencia, dia_semana)
- Paginación
- Validaciones de FK (grupo_docente_id, aula_id, profesor_id)
- Gestión de relación M:N con Profesor
- Horarios duales (semanal vs puntual)
- Validaciones de horarios (rangos, campos correctos)

Total: ~80 tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, time

from database.models import (
    Base, Sesion, GrupoDocente, Asignatura, Programa, Aula, Profesor, ProfesorSesion
)
from main import app
from db.session import get_db
from modules.docencia.repositories.sesion_repo import sesion_repository
from modules.docencia.services.sesion_service import sesion_service
from modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, ProfesorSesionCreate
)
from constants.enums import (
    TipoGrupoDocente, TipoPrograma, Periodo, ModalidadAsignatura, Idioma,
    TipoAula, ModalidadSesion, TipoRecurrencia, DiaSemana
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
def asignatura_data(db, programa_data):
    """Fixture que crea una asignatura de prueba."""
    asignatura = Asignatura(
        codigo_plan="PROG01",
        nombre="Programación I",
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
def grupo_data(db, asignatura_data):
    """Fixture que crea un grupo docente de prueba."""
    grupo = GrupoDocente(
        asignatura_id=asignatura_data.id,
        codigo="T1",
        tipo=TipoGrupoDocente.TEORIA,
        curso=1,
        turno="mañana"
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@pytest.fixture
def aula_data(db):
    """Fixture que crea un aula de prueba."""
    aula = Aula(
        nombre="Aula Magna",
        codigo="MAGNA",
        tipo=TipoAula.TEORICA,
        capacidad=200
    )
    db.add(aula)
    db.commit()
    db.refresh(aula)
    return aula


@pytest.fixture
def profesor_data_1(db):
    """Fixture que crea un profesor de prueba."""
    profesor = Profesor(
        nombre="Juan",
        apellidos="García López",
        email="juan.garcia@universidad.es",
        activo=True
    )
    db.add(profesor)
    db.commit()
    db.refresh(profesor)
    return profesor


@pytest.fixture
def profesor_data_2(db):
    """Fixture que crea un segundo profesor de prueba."""
    profesor = Profesor(
        nombre="María",
        apellidos="Rodríguez Pérez",
        email="maria.rodriguez@universidad.es",
        activo=True
    )
    db.add(profesor)
    db.commit()
    db.refresh(profesor)
    return profesor


@pytest.fixture
def sesion_semanal_data(grupo_data, aula_data):
    """Datos de prueba para crear una sesión semanal (schema)."""
    return SesionCreate(
        grupo_docente_id=grupo_data.id,
        aula_id=aula_data.id,
        modalidad=ModalidadSesion.PRESENCIAL,
        tipo_recurrencia=TipoRecurrencia.SEMANAL,
        dia_semana=DiaSemana.LUNES,
        hora_inicio=time(9, 0),
        hora_fin=time(11, 0),
        profesores=[]
    )


@pytest.fixture
def sesion_puntual_data(grupo_data, aula_data):
    """Datos de prueba para crear una sesión puntual (schema)."""
    return SesionCreate(
        grupo_docente_id=grupo_data.id,
        aula_id=aula_data.id,
        modalidad=ModalidadSesion.ONLINE,
        tipo_recurrencia=TipoRecurrencia.PUNTUAL,
        inicio=datetime(2025, 10, 25, 9, 0),
        fin=datetime(2025, 10, 25, 11, 0),
        profesores=[]
    )


# ============================================================
#  FUNCIONES HELPER
# ============================================================

def crear_sesion_semanal(db, grupo_id, aula_id, dia_semana=DiaSemana.LUNES, 
                         hora_inicio=time(9, 0), hora_fin=time(11, 0)):
    """Helper para crear una sesión semanal directamente en BD."""
    sesion = Sesion(
        grupo_docente_id=grupo_id,
        aula_id=aula_id,
        modalidad=ModalidadSesion.PRESENCIAL,
        tipo_recurrencia=TipoRecurrencia.SEMANAL,
        dia_semana=dia_semana,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def crear_sesion_puntual(db, grupo_id, aula_id, inicio, fin):
    """Helper para crear una sesión puntual directamente en BD."""
    sesion = Sesion(
        grupo_docente_id=grupo_id,
        aula_id=aula_id,
        modalidad=ModalidadSesion.ONLINE,
        tipo_recurrencia=TipoRecurrencia.PUNTUAL,
        inicio=inicio,
        fin=fin
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def asignar_profesor(db, sesion_id, profesor_id, rol_en_sesion=None):
    """Helper para asignar un profesor a una sesión."""
    prof_sesion = ProfesorSesion(
        sesion_id=sesion_id,
        profesor_id=profesor_id,
        rol_en_sesion=rol_en_sesion
    )
    db.add(prof_sesion)
    db.commit()
    return prof_sesion


# ============================================================
#  TESTS DE REPOSITORY
# ============================================================

class TestSesionRepository:
    """Tests de la capa de datos (repository)."""
    
    # ========== Tests CRUD básico ==========
    
    def test_create_sesion_semanal(self, db, sesion_semanal_data):
        """Test crear sesión semanal básica."""
        sesion = sesion_repository.create(db, sesion_semanal_data)
        
        assert sesion.id is not None
        assert sesion.grupo_docente_id == sesion_semanal_data.grupo_docente_id
        assert sesion.aula_id == sesion_semanal_data.aula_id
        assert sesion.modalidad == ModalidadSesion.PRESENCIAL
        assert sesion.tipo_recurrencia == TipoRecurrencia.SEMANAL
        assert sesion.dia_semana == DiaSemana.LUNES
        assert sesion.hora_inicio == time(9, 0)
        assert sesion.hora_fin == time(11, 0)
        assert sesion.inicio is None
        assert sesion.fin is None
    
    
    def test_create_sesion_puntual(self, db, sesion_puntual_data):
        """Test crear sesión puntual."""
        sesion = sesion_repository.create(db, sesion_puntual_data)
        
        assert sesion.id is not None
        assert sesion.tipo_recurrencia == TipoRecurrencia.PUNTUAL
        assert sesion.inicio == datetime(2025, 10, 25, 9, 0)
        assert sesion.fin == datetime(2025, 10, 25, 11, 0)
        assert sesion.dia_semana is None
        assert sesion.hora_inicio is None
        assert sesion.hora_fin is None
    
    
    def test_get_by_id_existente(self, db, grupo_data, aula_data):
        """Test obtener sesión existente por ID."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        resultado = sesion_repository.get_by_id(db, sesion.id)
        
        assert resultado is not None
        assert resultado.id == sesion.id
        assert resultado.grupo_docente_id == grupo_data.id
    
    
    def test_get_by_id_no_existente(self, db):
        """Test obtener sesión que no existe retorna None."""
        resultado = sesion_repository.get_by_id(db, 9999)
        assert resultado is None
    
    
    def test_update_sesion(self, db, grupo_data, aula_data):
        """Test actualizar sesión."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        update_data = SesionUpdate(
            hora_inicio=time(10, 0),
            hora_fin=time(12, 0),
            modalidad=ModalidadSesion.HIBRIDA
        )
        
        sesion_actualizada = sesion_repository.update(db, sesion, update_data)
        
        assert sesion_actualizada.hora_inicio == time(10, 0)
        assert sesion_actualizada.hora_fin == time(12, 0)
        assert sesion_actualizada.modalidad == ModalidadSesion.HIBRIDA
        # Campos no actualizados permanecen igual
        assert sesion_actualizada.dia_semana == DiaSemana.LUNES
    
    
    def test_delete_sesion(self, db, grupo_data, aula_data):
        """Test eliminar sesión (DELETE físico)."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        sesion_id = sesion.id
        
        resultado = sesion_repository.delete(db, sesion_id)
        
        assert resultado is not None
        assert resultado.id == sesion_id
        # Verificar que se eliminó
        assert sesion_repository.get_by_id(db, sesion_id) is None
    
    
    def test_delete_sesion_no_existente(self, db):
        """Test eliminar sesión que no existe retorna None."""
        resultado = sesion_repository.delete(db, 9999)
        assert resultado is None
    
    
    # ========== Tests de búsquedas ==========
    
    def test_get_multi_sin_filtros(self, db, grupo_data, aula_data):
        """Test listar todas las sesiones sin filtros."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MARTES)
        
        items, total = sesion_repository.get_multi(db)
        
        assert total == 2
        assert len(items) == 2
    
    
    def test_get_multi_con_paginacion(self, db, grupo_data, aula_data):
        """Test paginación de sesiones."""
        for i in range(5):
            crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        items, total = sesion_repository.get_multi(db, skip=2, limit=2)
        
        assert total == 5
        assert len(items) == 2
    
    
    def test_get_multi_filtro_grupo_docente(self, db, aula_data, asignatura_data):
        """Test filtrar sesiones por grupo docente."""
        grupo1 = GrupoDocente(asignatura_id=asignatura_data.id, codigo="G1", tipo=TipoGrupoDocente.TEORIA)
        grupo2 = GrupoDocente(asignatura_id=asignatura_data.id, codigo="G2", tipo=TipoGrupoDocente.PRACTICA)
        db.add_all([grupo1, grupo2])
        db.commit()
        
        crear_sesion_semanal(db, grupo1.id, aula_data.id)
        crear_sesion_semanal(db, grupo1.id, aula_data.id, DiaSemana.MARTES)
        crear_sesion_semanal(db, grupo2.id, aula_data.id)
        
        items, total = sesion_repository.get_multi(db, grupo_docente_id=grupo1.id)
        
        assert total == 2
        assert all(s.grupo_docente_id == grupo1.id for s in items)
    
    
    def test_get_multi_filtro_aula(self, db, grupo_data):
        """Test filtrar sesiones por aula."""
        aula1 = Aula(nombre="A1", codigo="A1", tipo=TipoAula.TEORICA)
        aula2 = Aula(nombre="A2", codigo="A2", tipo=TipoAula.TEORICA)
        db.add_all([aula1, aula2])
        db.commit()
        
        crear_sesion_semanal(db, grupo_data.id, aula1.id)
        crear_sesion_semanal(db, grupo_data.id, aula2.id)
        
        items, total = sesion_repository.get_multi(db, aula_id=aula1.id)
        
        assert total == 1
        assert items[0].aula_id == aula1.id
    
    
    def test_get_multi_filtro_modalidad(self, db, grupo_data, aula_data):
        """Test filtrar sesiones por modalidad."""
        sesion1 = Sesion(
            grupo_docente_id=grupo_data.id, aula_id=aula_data.id,
            modalidad=ModalidadSesion.PRESENCIAL, tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES, hora_inicio=time(9, 0), hora_fin=time(11, 0)
        )
        sesion2 = Sesion(
            grupo_docente_id=grupo_data.id, aula_id=aula_data.id,
            modalidad=ModalidadSesion.ONLINE, tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.MARTES, hora_inicio=time(9, 0), hora_fin=time(11, 0)
        )
        db.add_all([sesion1, sesion2])
        db.commit()
        
        items, total = sesion_repository.get_multi(db, modalidad=ModalidadSesion.ONLINE)
        
        assert total == 1
        assert items[0].modalidad == ModalidadSesion.ONLINE
    
    
    def test_get_multi_filtro_tipo_recurrencia(self, db, grupo_data, aula_data):
        """Test filtrar sesiones por tipo de recurrencia."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        crear_sesion_puntual(db, grupo_data.id, aula_data.id, 
                            datetime(2025, 10, 25, 9, 0), datetime(2025, 10, 25, 11, 0))
        
        items, total = sesion_repository.get_multi(db, tipo_recurrencia=TipoRecurrencia.SEMANAL)
        
        assert total == 1
        assert items[0].tipo_recurrencia == TipoRecurrencia.SEMANAL
    
    
    def test_get_multi_filtro_dia_semana(self, db, grupo_data, aula_data):
        """Test filtrar sesiones por día de la semana."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MARTES)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        
        items, total = sesion_repository.get_multi(db, dia_semana=DiaSemana.LUNES)
        
        assert total == 2
        assert all(s.dia_semana == DiaSemana.LUNES for s in items)
    
    
    def test_get_by_grupo_docente(self, db, grupo_data, aula_data):
        """Test obtener todas las sesiones de un grupo."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MIERCOLES)
        
        sesiones = sesion_repository.get_by_grupo_docente(db, grupo_data.id)
        
        assert len(sesiones) == 2
        assert all(s.grupo_docente_id == grupo_data.id for s in sesiones)
    
    
    def test_get_by_aula(self, db, grupo_data, aula_data):
        """Test obtener todas las sesiones de un aula."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MARTES)
        
        sesiones = sesion_repository.get_by_aula(db, aula_data.id)
        
        assert len(sesiones) == 2
        assert all(s.aula_id == aula_data.id for s in sesiones)
    
    
    def test_get_by_profesor(self, db, grupo_data, aula_data, profesor_data_1):
        """Test obtener todas las sesiones de un profesor."""
        sesion1 = crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.LUNES)
        sesion2 = crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MARTES)
        
        asignar_profesor(db, sesion1.id, profesor_data_1.id, "Docente")
        asignar_profesor(db, sesion2.id, profesor_data_1.id, "Docente")
        
        sesiones = sesion_repository.get_by_profesor(db, profesor_data_1.id)
        
        assert len(sesiones) == 2
    
    
    def test_get_by_fecha_range(self, db, grupo_data, aula_data):
        """Test obtener sesiones puntuales en un rango de fechas."""
        crear_sesion_puntual(db, grupo_data.id, aula_data.id,
                            datetime(2025, 10, 25, 9, 0), datetime(2025, 10, 25, 11, 0))
        crear_sesion_puntual(db, grupo_data.id, aula_data.id,
                            datetime(2025, 11, 15, 9, 0), datetime(2025, 11, 15, 11, 0))
        crear_sesion_puntual(db, grupo_data.id, aula_data.id,
                            datetime(2025, 12, 5, 9, 0), datetime(2025, 12, 5, 11, 0))
        
        sesiones = sesion_repository.get_by_fecha_range(
            db, datetime(2025, 10, 1), datetime(2025, 11, 30)
        )
        
        assert len(sesiones) == 2
    
    
    # ========== Tests gestión profesores (M:N) ==========
    
    def test_add_profesor(self, db, grupo_data, aula_data, profesor_data_1):
        """Test asignar profesor a sesión."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        prof_sesion = sesion_repository.add_profesor(
            db, sesion.id, profesor_data_1.id, "Docente"
        )
        
        assert prof_sesion.sesion_id == sesion.id
        assert prof_sesion.profesor_id == profesor_data_1.id
        assert prof_sesion.rol_en_sesion == "Docente"
    
    
    def test_remove_profesor(self, db, grupo_data, aula_data, profesor_data_1):
        """Test desasignar profesor de sesión."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        asignar_profesor(db, sesion.id, profesor_data_1.id)
        
        resultado = sesion_repository.remove_profesor(db, sesion.id, profesor_data_1.id)
        
        assert resultado is True
        # Verificar que se eliminó
        profesores = sesion_repository.get_profesores_by_sesion(db, sesion.id)
        assert len(profesores) == 0
    
    
    def test_update_profesores_reemplaza_lista(self, db, grupo_data, aula_data, 
                                              profesor_data_1, profesor_data_2):
        """Test actualizar lista completa de profesores (reemplaza)."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        asignar_profesor(db, sesion.id, profesor_data_1.id, "Docente")
        
        # Reemplazar con nueva lista
        nuevos_profesores = [
            {'profesor_id': profesor_data_2.id, 'rol_en_sesion': 'Ayudante'}
        ]
        sesion_repository.update_profesores(db, sesion.id, nuevos_profesores)
        
        profesores = sesion_repository.get_profesores_by_sesion(db, sesion.id)
        assert len(profesores) == 1
        assert profesores[0].profesor_id == profesor_data_2.id
    
    
    def test_get_profesores_by_sesion(self, db, grupo_data, aula_data, 
                                     profesor_data_1, profesor_data_2):
        """Test obtener lista de profesores de una sesión."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        asignar_profesor(db, sesion.id, profesor_data_1.id, "Docente")
        asignar_profesor(db, sesion.id, profesor_data_2.id, "Ayudante")
        
        profesores = sesion_repository.get_profesores_by_sesion(db, sesion.id)
        
        assert len(profesores) == 2


# ============================================================
#  TESTS DE SERVICE
# ============================================================

class TestSesionService:
    """Tests de la lógica de negocio (service)."""
    
    # ========== Tests create con validaciones ==========
    
    def test_create_sesion_semanal_exitoso(self, db, sesion_semanal_data):
        """Test crear sesión semanal con validaciones OK."""
        sesion = sesion_service.create(db, sesion_semanal_data)
        
        assert sesion.id is not None
        assert sesion.grupo_docente_id == sesion_semanal_data.grupo_docente_id
        assert sesion.modalidad == ModalidadSesion.PRESENCIAL
    
    
    def test_create_sesion_con_profesores(self, db, grupo_data, aula_data, profesor_data_1):
        """Test crear sesión con profesores asignados."""
        sesion_data = SesionCreate(
            grupo_docente_id=grupo_data.id,
            aula_id=aula_data.id,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            profesores=[
                ProfesorSesionCreate(profesor_id=profesor_data_1.id, rol_en_sesion="Docente")
            ]
        )
        
        sesion = sesion_service.create(db, sesion_data)
        
        assert sesion.id is not None
        assert len(sesion.profesores) == 1
        assert sesion.profesores[0].profesor_id == profesor_data_1.id
    
    
    def test_create_sesion_grupo_no_existe(self, db, aula_data):
        """Test crear sesión con grupo que no existe (404)."""
        sesion_data = SesionCreate(
            grupo_docente_id=9999,
            aula_id=aula_data.id,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            profesores=[]
        )
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.create(db, sesion_data)
        
        assert exc_info.value.status_code == 404
        assert "Grupo docente" in str(exc_info.value.detail)
    
    
    def test_create_sesion_aula_no_existe(self, db, grupo_data):
        """Test crear sesión con aula que no existe (404)."""
        sesion_data = SesionCreate(
            grupo_docente_id=grupo_data.id,
            aula_id=9999,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            profesores=[]
        )
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.create(db, sesion_data)
        
        assert exc_info.value.status_code == 404
        assert "Aula" in str(exc_info.value.detail)
    
    
    def test_create_sesion_profesor_no_existe(self, db, grupo_data, aula_data):
        """Test crear sesión con profesor que no existe (404)."""
        sesion_data = SesionCreate(
            grupo_docente_id=grupo_data.id,
            aula_id=aula_data.id,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            profesores=[
                ProfesorSesionCreate(profesor_id=9999, rol_en_sesion="Docente")
            ]
        )
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.create(db, sesion_data)
        
        assert exc_info.value.status_code == 404
        assert "Profesor" in str(exc_info.value.detail)
    
    
    # ========== Tests get ==========
    
    def test_get_by_id_existente(self, db, grupo_data, aula_data):
        """Test obtener sesión existente."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        resultado = sesion_service.get_by_id(db, sesion.id)
        
        assert resultado.id == sesion.id
    
    
    def test_get_by_id_no_existente(self, db):
        """Test obtener sesión que no existe (404)."""
        with pytest.raises(Exception) as exc_info:
            sesion_service.get_by_id(db, 9999)
        
        assert exc_info.value.status_code == 404
    
    
    def test_get_multi_retorna_tupla(self, db, grupo_data, aula_data):
        """Test get_multi retorna tupla (items, total)."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        resultado = sesion_service.get_multi(db)
        
        assert isinstance(resultado, tuple)
        assert len(resultado) == 2
        items, total = resultado
        assert isinstance(items, list)
        assert isinstance(total, int)
    
    
    # ========== Tests update ==========
    
    def test_update_sesion_exitoso(self, db, grupo_data, aula_data):
        """Test actualizar sesión existente."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        update_data = SesionUpdate(modalidad=ModalidadSesion.HIBRIDA)
        
        resultado = sesion_service.update(db, sesion.id, update_data)
        
        assert resultado.modalidad == ModalidadSesion.HIBRIDA
        assert resultado.dia_semana == DiaSemana.LUNES  # No cambió
    
    
    def test_update_sesion_no_existente(self, db):
        """Test actualizar sesión que no existe (404)."""
        update_data = SesionUpdate(modalidad=ModalidadSesion.ONLINE)
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.update(db, 9999, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_sesion_cambiar_grupo_no_existe(self, db, grupo_data, aula_data):
        """Test actualizar con nuevo grupo que no existe (404)."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        update_data = SesionUpdate(grupo_docente_id=9999)
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.update(db, sesion.id, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_sesion_cambiar_aula_no_existe(self, db, grupo_data, aula_data):
        """Test actualizar con nueva aula que no existe (404)."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        update_data = SesionUpdate(aula_id=9999)
        
        with pytest.raises(Exception) as exc_info:
            sesion_service.update(db, sesion.id, update_data)
        
        assert exc_info.value.status_code == 404
    
    
    def test_update_sesion_reemplazar_profesores(self, db, grupo_data, aula_data, 
                                                profesor_data_1, profesor_data_2):
        """Test actualizar lista de profesores."""
        sesion_data = SesionCreate(
            grupo_docente_id=grupo_data.id,
            aula_id=aula_data.id,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL,
            dia_semana=DiaSemana.LUNES,
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            profesores=[
                ProfesorSesionCreate(profesor_id=profesor_data_1.id, rol_en_sesion="Docente")
            ]
        )
        sesion = sesion_service.create(db, sesion_data)
        
        update_data = SesionUpdate(
            profesores=[
                ProfesorSesionCreate(profesor_id=profesor_data_2.id, rol_en_sesion="Ayudante")
            ]
        )
        
        resultado = sesion_service.update(db, sesion.id, update_data)
        
        assert len(resultado.profesores) == 1
        assert resultado.profesores[0].profesor_id == profesor_data_2.id
    
    
    # ========== Tests delete ==========
    
    def test_delete_sesion_existente(self, db, grupo_data, aula_data):
        """Test eliminar sesión existente."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        sesion_service.delete(db, sesion.id)
        
        # Verificar que se eliminó
        with pytest.raises(Exception) as exc_info:
            sesion_service.get_by_id(db, sesion.id)
        assert exc_info.value.status_code == 404
    
    
    def test_delete_sesion_no_existente(self, db):
        """Test eliminar sesión que no existe (404)."""
        with pytest.raises(Exception) as exc_info:
            sesion_service.delete(db, 9999)
        
        assert exc_info.value.status_code == 404


# ============================================================
#  TESTS DE API (Endpoints REST)
# ============================================================

class TestSesionAPI:
    """Tests de los endpoints REST."""
    
    # ========== Tests GET /sesiones ==========
    
    def test_listar_sesiones_endpoint(self, client, db, grupo_data, aula_data):
        """Test GET /sesiones."""
        crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        crear_sesion_semanal(db, grupo_data.id, aula_data.id, DiaSemana.MARTES)
        
        response = client.get("/v0/docencia/sesiones")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert "page" in data
        assert "size" in data
    
    
    def test_listar_sesiones_con_filtro_grupo(self, client, db, aula_data, asignatura_data):
        """Test GET /sesiones con filtro grupo_docente_id."""
        grupo1 = GrupoDocente(asignatura_id=asignatura_data.id, codigo="G1", tipo=TipoGrupoDocente.TEORIA)
        grupo2 = GrupoDocente(asignatura_id=asignatura_data.id, codigo="G2", tipo=TipoGrupoDocente.PRACTICA)
        db.add_all([grupo1, grupo2])
        db.commit()
        
        crear_sesion_semanal(db, grupo1.id, aula_data.id)
        crear_sesion_semanal(db, grupo2.id, aula_data.id)
        
        response = client.get(f"/v0/docencia/sesiones?grupo_docente_id={grupo1.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    
    
    def test_listar_sesiones_con_paginacion(self, client, db, grupo_data, aula_data):
        """Test GET /sesiones con paginación."""
        for i in range(5):
            crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        response = client.get("/v0/docencia/sesiones?skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
    
    
    # ========== Tests GET /sesiones/{id} ==========
    
    def test_obtener_sesion_endpoint(self, client, db, grupo_data, aula_data):
        """Test GET /sesiones/{id}."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        response = client.get(f"/v0/docencia/sesiones/{sesion.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sesion.id
        assert data["grupo_docente_id"] == grupo_data.id
    
    
    def test_obtener_sesion_no_existente_endpoint(self, client, db):
        """Test GET /sesiones/{id} con ID que no existe."""
        response = client.get("/v0/docencia/sesiones/9999")
        
        assert response.status_code == 404
    
    
    # ========== Tests POST /sesiones ==========
    
    def test_crear_sesion_semanal_endpoint(self, client, db, grupo_data, aula_data):
        """Test POST /sesiones (sesión semanal)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["modalidad"] == "presencial"
        assert data["tipo_recurrencia"] == "semanal"
    
    
    def test_crear_sesion_puntual_endpoint(self, client, db, grupo_data, aula_data):
        """Test POST /sesiones (sesión puntual)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "online",
                "tipo_recurrencia": "puntual",
                "inicio": "2025-10-25T09:00:00",
                "fin": "2025-10-25T11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_recurrencia"] == "puntual"
        assert data["inicio"] is not None
    
    
    def test_crear_sesion_con_profesores_endpoint(self, client, db, grupo_data, aula_data, profesor_data_1):
        """Test POST /sesiones con profesores."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": [
                    {"profesor_id": profesor_data_1.id, "rol_en_sesion": "Docente"}
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["profesores"]) == 1
    
    
    def test_crear_sesion_grupo_no_existe_endpoint(self, client, db, aula_data):
        """Test POST /sesiones con grupo que no existe (404)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": 9999,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 404
    
    
    def test_crear_sesion_datos_invalidos_endpoint(self, client, db):
        """Test POST /sesiones con datos inválidos (422)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": -1,  # Inválido
                "aula_id": -1,
                "modalidad": "invalido",  # No existe
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    # ========== Tests PUT /sesiones/{id} ==========
    
    def test_actualizar_sesion_endpoint(self, client, db, grupo_data, aula_data):
        """Test PUT /sesiones/{id}."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        response = client.put(
            f"/v0/docencia/sesiones/{sesion.id}",
            json={"modalidad": "hibrida"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["modalidad"] == "hibrida"
    
    
    def test_actualizar_sesion_no_existente_endpoint(self, client, db):
        """Test PUT /sesiones/{id} con ID que no existe."""
        response = client.put(
            "/v0/docencia/sesiones/9999",
            json={"modalidad": "online"}
        )
        
        assert response.status_code == 404
    
    
    # ========== Tests DELETE /sesiones/{id} ==========
    
    def test_eliminar_sesion_endpoint(self, client, db, grupo_data, aula_data):
        """Test DELETE /sesiones/{id}."""
        sesion = crear_sesion_semanal(db, grupo_data.id, aula_data.id)
        
        response = client.delete(f"/v0/docencia/sesiones/{sesion.id}")
        
        assert response.status_code == 204
        # Verificar que se eliminó
        response_get = client.get(f"/v0/docencia/sesiones/{sesion.id}")
        assert response_get.status_code == 404
    
    
    def test_eliminar_sesion_no_existente_endpoint(self, client, db):
        """Test DELETE /sesiones/{id} con ID que no existe."""
        response = client.delete("/v0/docencia/sesiones/9999")
        
        assert response.status_code == 404


# ============================================================
#  TESTS DE CASOS LÍMITE
# ============================================================

class TestSesionEdgeCases:
    """Tests de casos límite y validaciones especiales."""
    
    def test_validacion_horario_semanal_campos_correctos(self, client, db, grupo_data, aula_data):
        """Test que sesión semanal requiere dia_semana + hora_inicio + hora_fin."""
        # Intentar crear semanal sin dia_semana
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_validacion_horario_puntual_campos_correctos(self, client, db, grupo_data, aula_data):
        """Test que sesión puntual requiere inicio + fin."""
        # Intentar crear puntual sin inicio
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "online",
                "tipo_recurrencia": "puntual",
                "fin": "2025-10-25T11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_validacion_horario_semanal_no_debe_tener_inicio_fin(self, client, db, grupo_data, aula_data):
        """Test que sesión semanal NO debe tener inicio/fin (solo para puntuales)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "inicio": "2025-10-25T09:00:00",  # No debe estar
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_validacion_horario_puntual_no_debe_tener_dia_semana(self, client, db, grupo_data, aula_data):
        """Test que sesión puntual NO debe tener dia_semana (solo para recurrentes)."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "online",
                "tipo_recurrencia": "puntual",
                "dia_semana": "lunes",  # No debe estar
                "inicio": "2025-10-25T09:00:00",
                "fin": "2025-10-25T11:00:00",
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_validacion_hora_inicio_menor_que_fin(self, client, db, grupo_data, aula_data):
        """Test que hora_inicio debe ser menor que hora_fin."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "11:00:00",
                "hora_fin": "09:00:00",  # Menor que inicio
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_validacion_inicio_menor_que_fin_puntual(self, client, db, grupo_data, aula_data):
        """Test que inicio debe ser menor que fin en sesiones puntuales."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "online",
                "tipo_recurrencia": "puntual",
                "inicio": "2025-10-25T11:00:00",
                "fin": "2025-10-25T09:00:00",  # Menor que inicio
                "profesores": []
            }
        )
        
        assert response.status_code == 422
    
    
    def test_todos_los_tipos_modalidad_validos(self, client, db, grupo_data, aula_data):
        """Test que todos los valores de ModalidadSesion son válidos."""
        modalidades = ["presencial", "online", "hibrida"]
        dias = ["lunes", "martes", "miercoles"]  # Usar días diferentes para evitar solapamientos
        
        for idx, modalidad in enumerate(modalidades):
            response = client.post(
                "/v0/docencia/sesiones",
                json={
                    "grupo_docente_id": grupo_data.id,
                    "aula_id": aula_data.id,
                    "modalidad": modalidad,
                    "tipo_recurrencia": "semanal",
                    "dia_semana": dias[idx],
                    "hora_inicio": "09:00:00",
                    "hora_fin": "11:00:00",
                    "profesores": []
                }
            )
            
            assert response.status_code == 201
    
    
    def test_todos_los_dias_semana_validos(self, client, db, grupo_data, aula_data):
        """Test que todos los valores de DiaSemana son válidos."""
        dias = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        
        for idx, dia in enumerate(dias):
            response = client.post(
                "/v0/docencia/sesiones",
                json={
                    "grupo_docente_id": grupo_data.id,
                    "aula_id": aula_data.id,
                    "modalidad": "presencial",
                    "tipo_recurrencia": "semanal",
                    "dia_semana": dia,
                    "hora_inicio": "09:00:00",  # Misma hora para todos, pero en días diferentes
                    "hora_fin": "11:00:00",
                    "profesores": []
                }
            )
            
            assert response.status_code == 201
    
    
    def test_todos_los_tipos_recurrencia_validos(self, client, db, grupo_data, aula_data):
        """Test que todos los valores de TipoRecurrencia son válidos."""
        # Semanal
        response_semanal = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": []
            }
        )
        assert response_semanal.status_code == 201
        
        # Quincenal
        response_quincenal = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "quincenal",
                "dia_semana": "martes",
                "hora_inicio": "10:00:00",
                "hora_fin": "12:00:00",
                "profesores": []
            }
        )
        assert response_quincenal.status_code == 201
        
        # Mensual
        response_mensual = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "mensual",
                "dia_semana": "miercoles",
                "hora_inicio": "11:00:00",
                "hora_fin": "13:00:00",
                "profesores": []
            }
        )
        assert response_mensual.status_code == 201
        
        # Puntual
        response_puntual = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "online",
                "tipo_recurrencia": "puntual",
                "inicio": "2025-10-25T09:00:00",
                "fin": "2025-10-25T11:00:00",
                "profesores": []
            }
        )
        assert response_puntual.status_code == 201
    
    
    def test_multiple_profesores_por_sesion(self, client, db, grupo_data, aula_data, 
                                           profesor_data_1, profesor_data_2):
        """Test crear sesión con múltiples profesores."""
        response = client.post(
            "/v0/docencia/sesiones",
            json={
                "grupo_docente_id": grupo_data.id,
                "aula_id": aula_data.id,
                "modalidad": "presencial",
                "tipo_recurrencia": "semanal",
                "dia_semana": "lunes",
                "hora_inicio": "09:00:00",
                "hora_fin": "11:00:00",
                "profesores": [
                    {"profesor_id": profesor_data_1.id, "rol_en_sesion": "Docente"},
                    {"profesor_id": profesor_data_2.id, "rol_en_sesion": "Ayudante"}
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["profesores"]) == 2
