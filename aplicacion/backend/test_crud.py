#!/usr/bin/env python3
"""
Batería de Tests para la Capa CRUD
===================================

Tests sencillos pero completos para verificar que todas las operaciones CRUD
funcionan correctamente. Incluye validaciones de integridad y manejo de errores.
"""

import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

# Configurar path para importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importaciones del proyecto
from database.session import SessionLocal
from config import settings
import crud
from schemas.grado import GradoCreate, GradoUpdate
from schemas.mencion import MencionCreate, MencionUpdate
from schemas.aula import AulaCreate, AulaUpdate
from schemas.profesor import ProfesorCreate, ProfesorUpdate
from schemas.asignatura import AsignaturaCreate, AsignaturaUpdate
from schemas.restriccion import RestriccionCreate, RestriccionUpdate
from schemas.sesion import SesionCreate, SesionUpdate


class TestSuite:
    """Clase principal para ejecutar todos los tests CRUD"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.test_data = {}
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Registra el resultado de un test"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"    📝 {details}")
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
    
    def assert_success(self, test_name: str, result, error_msg: str = ""):
        """Verifica que el resultado sea exitoso (sin error)"""
        entity, error = result
        success = entity is not None and error is None
        if not success and error:
            self.log_test(test_name, False, f"Error: {error}")
        else:
            self.log_test(test_name, True)
        return entity if success else None
    
    def assert_failure(self, test_name: str, result, expected_error: str = ""):
        """Verifica que el resultado sea un fallo esperado"""
        entity, error = result
        failed_as_expected = entity is None and error is not None
        if failed_as_expected:
            self.log_test(test_name, True, f"Error esperado: {error}")
        else:
            self.log_test(test_name, False, f"Se esperaba error pero obtuvo: {entity}")
        return failed_as_expected
    
    def cleanup_database(self):
        """Limpia la base de datos para pruebas"""
        print("🧹 Limpiando base de datos para pruebas...")
        try:
            # Orden de eliminación respetando integridad referencial
            tables = [
                'sesiones', 'restricciones', 'asignatura_grado', 
                'asignatura_mencion', 'profesor_asignatura',
                'menciones', 'asignaturas', 'profesores', 'aulas', 'grados'
            ]
            
            for table in tables:
                self.db.execute(text(f"DELETE FROM {table}"))
            
            self.db.commit()
            print("✅ Base de datos limpiada exitosamente")
            
        except Exception as e:
            print(f"❌ Error limpiando base de datos: {e}")
            self.db.rollback()
    
    def test_grado_crud(self):
        """Tests para operaciones CRUD de Grado"""
        print("\n🎓 === TESTS GRADO ===")
        
        # 1. Crear grado
        grado_data = GradoCreate(nombre="Ingeniería Informática")
        result = crud.create_grado(self.db, grado_data)
        grado = self.assert_success("Crear grado", result)
        if grado:
            self.test_data['grado'] = grado
            
        # 2. Crear grado duplicado (debe fallar)
        result = crud.create_grado(self.db, grado_data)
        self.assert_failure("Crear grado duplicado", result)
        
        # 3. Obtener grados
        grados = crud.get_grados(self.db)
        self.log_test("Obtener grados", len(grados) >= 1, f"Encontrados {len(grados)} grados")
        
        # 4. Obtener grado por ID
        if grado:
            grado_encontrado = crud.get_grado_by_id(self.db, grado.id)
            self.log_test("Obtener grado por ID", grado_encontrado is not None)
            
        # 5. Obtener grado por nombre
        grado_por_nombre = crud.get_grado_by_nombre(self.db, "Ingeniería Informática")
        self.log_test("Obtener grado por nombre", grado_por_nombre is not None)
        
        # 6. Actualizar grado
        if grado:
            update_data = GradoUpdate()
            result = crud.update_grado(self.db, grado.id, update_data)
            self.assert_success("Actualizar grado", result)
    
    def test_mencion_crud(self):
        """Tests para operaciones CRUD de Mención"""
        print("\n📚 === TESTS MENCIÓN ===")
        
        grado = self.test_data.get('grado')
        if not grado:
            print("⚠️ Saltando tests de mención - No hay grado disponible")
            return
            
        # 1. Crear mención
        mencion_data = MencionCreate(
            nombre="Inteligencia Artificial",
            grado_id=grado.id
        )
        result = crud.create_mencion(self.db, mencion_data)
        mencion = self.assert_success("Crear mención", result)
        if mencion:
            self.test_data['mencion'] = mencion
            
        # 2. Obtener menciones
        menciones = crud.get_menciones(self.db)
        self.log_test("Obtener menciones", len(menciones) >= 1, f"Encontradas {len(menciones)} menciones")
        
        # 3. Obtener menciones por grado
        menciones_grado = crud.get_menciones_by_grado_id(self.db, grado.id)
        self.log_test("Obtener menciones por grado", len(menciones_grado) >= 1)
    
    def test_aula_crud(self):
        """Tests para operaciones CRUD de Aula"""
        print("\n🏫 === TESTS AULA ===")
        
        # 1. Crear aula de teoría
        aula_data = AulaCreate(
            nombre="A101",
            capacidad=50,
            tipo="teoria"
        )
        result = crud.create_aula(self.db, aula_data)
        aula = self.assert_success("Crear aula", result)
        if aula:
            self.test_data['aula'] = aula
            
        # 2. Crear aula de laboratorio
        aula_lab_data = AulaCreate(
            nombre="LAB01",
            capacidad=25,
            tipo="laboratorio"
        )
        result = crud.create_aula(self.db, aula_lab_data)
        aula_lab = self.assert_success("Crear aula laboratorio", result)
        if aula_lab:
            self.test_data['aula_lab'] = aula_lab
            
        # 3. Obtener aulas
        aulas = crud.get_aulas(self.db)
        self.log_test("Obtener aulas", len(aulas) >= 2, f"Encontradas {len(aulas)} aulas")
        
        # 4. Obtener aulas por tipo
        aulas_lab = crud.get_aulas_by_tipo(self.db, "laboratorio")
        self.log_test("Obtener aulas laboratorio", len(aulas_lab) >= 1)
        
        # 5. Obtener aula por ID
        if aula:
            aula_encontrada = crud.get_aula_by_id(self.db, aula.id)
            self.log_test("Obtener aula por ID", aula_encontrada is not None)
    
    def test_profesor_crud(self):
        """Tests para operaciones CRUD de Profesor"""
        print("\n👨‍🏫 === TESTS PROFESOR ===")
        
        # 1. Crear profesor
        profesor_data = ProfesorCreate(
            nombre="Dr. Juan Pérez",
            disponibilidad={
                "lunes": ["08:00-10:00", "14:00-16:00"],
                "miercoles": ["09:00-13:00"],
                "viernes": ["08:00-12:00"]
            }
        )
        result = crud.create_profesor(self.db, profesor_data)
        profesor = self.assert_success("Crear profesor", result)
        if profesor:
            self.test_data['profesor'] = profesor
            
        # 2. Obtener profesores
        profesores = crud.get_profesores(self.db)
        self.log_test("Obtener profesores", len(profesores) >= 1, f"Encontrados {len(profesores)} profesores")
        
        # 3. Obtener profesor por ID
        if profesor:
            profesor_encontrado = crud.get_profesor_by_id(self.db, profesor.id)
            self.log_test("Obtener profesor por ID", profesor_encontrado is not None)
            
        # 4. Actualizar profesor
        if profesor:
            update_data = ProfesorUpdate(nombre="Dr. Juan Pérez García")
            result = crud.update_profesor(self.db, profesor.id, update_data)
            self.assert_success("Actualizar profesor", result)
    
    def test_asignatura_crud(self):
        """Tests para operaciones CRUD de Asignatura"""
        print("\n📖 === TESTS ASIGNATURA ===")
        
        grado = self.test_data.get('grado')
        if not grado:
            print("⚠️ Saltando tests de asignatura - No hay grado disponible")
            return
            
        # 1. Crear asignatura
        asignatura_data = AsignaturaCreate(
            nombre="Programación I",
            creditos=6,
            horas_semanales=4,
            curso=1,
            cuatrimestre="1",
            grado_id=grado.id
        )
        result = crud.create_asignatura(self.db, asignatura_data)
        asignatura = self.assert_success("Crear asignatura", result)
        if asignatura:
            self.test_data['asignatura'] = asignatura
            
        # 2. Crear segunda asignatura
        asignatura_data2 = AsignaturaCreate(
            nombre="Base de Datos",
            creditos=6,
            horas_semanales=5,
            curso=2,
            cuatrimestre="2",
            grado_id=grado.id
        )
        result = crud.create_asignatura(self.db, asignatura_data2)
        asignatura2 = self.assert_success("Crear segunda asignatura", result)
        if asignatura2:
            self.test_data['asignatura2'] = asignatura2
            
        # 3. Obtener asignaturas
        asignaturas = crud.get_asignaturas(self.db)
        self.log_test("Obtener asignaturas", len(asignaturas) >= 2, f"Encontradas {len(asignaturas)} asignaturas")
        
        # 4. Obtener asignaturas por grado
        asignaturas_grado = crud.get_asignaturas_by_grado_id(self.db, grado.id)
        self.log_test("Obtener asignaturas por grado", len(asignaturas_grado) >= 2)
        
        # 5. Obtener asignatura por ID
        if asignatura:
            asignatura_encontrada = crud.get_asignatura_by_id(self.db, asignatura.id)
            self.log_test("Obtener asignatura por ID", asignatura_encontrada is not None)
    
    def test_restriccion_crud(self):
        """Tests para operaciones CRUD de Restricción"""
        print("\n🚫 === TESTS RESTRICCIÓN ===")
        
        profesor = self.test_data.get('profesor')
        aula = self.test_data.get('aula')
        
        # 1. Crear restricción de profesor
        if profesor:
            restriccion_data = RestriccionCreate(
                tipo="horario_profesor",
                valor={
                    "dias_no_disponible": ["viernes"],
                    "horario_maximo": "18:00",
                    "razon": "Profesor no disponible los viernes"
                },
                profesor_id=profesor.id
            )
            result = crud.create_restriccion(self.db, restriccion_data)
            restriccion = self.assert_success("Crear restricción profesor", result)
            if restriccion:
                self.test_data['restriccion'] = restriccion
        
        # 2. Crear restricción de aula
        if aula:
            restriccion_aula_data = RestriccionCreate(
                tipo="disponibilidad_aula",
                valor={
                    "horarios_no_disponible": ["14:00-16:00"],
                    "dias_afectados": ["lunes"],
                    "razon": "Aula en mantenimiento"
                },
                aula_id=aula.id
            )
            result = crud.create_restriccion(self.db, restriccion_aula_data)
            self.assert_success("Crear restricción aula", result)
        
        # 3. Obtener restricciones
        restricciones = crud.get_restricciones(self.db)
        self.log_test("Obtener restricciones", len(restricciones) >= 1, f"Encontradas {len(restricciones)} restricciones")
    
    def test_sesion_crud(self):
        """Tests para operaciones CRUD de Sesión"""
        print("\n⏰ === TESTS SESIÓN ===")
        
        asignatura = self.test_data.get('asignatura')
        aula = self.test_data.get('aula')
        profesor = self.test_data.get('profesor')
        
        if not all([asignatura, aula, profesor]):
            print("⚠️ Saltando tests de sesión - Faltan entidades requeridas")
            return
            
        # 1. Crear sesión
        sesion_data = SesionCreate(
            asignatura_id=asignatura.id,
            aula_id=aula.id,
            profesor_id=profesor.id,
            dia_semana="lunes",
            hora_inicio="08:00",
            hora_fin="10:00"
        )
        result = crud.create_sesion(self.db, sesion_data)
        sesion = self.assert_success("Crear sesión", result)
        if sesion:
            self.test_data['sesion'] = sesion
            
        # 2. Crear sesión con conflicto (debe fallar)
        sesion_conflicto = SesionCreate(
            asignatura_id=asignatura.id,
            aula_id=aula.id,
            profesor_id=profesor.id,
            dia_semana="lunes",
            hora_inicio="09:00",  # Solapa con la sesión anterior
            hora_fin="11:00"
        )
        result = crud.create_sesion(self.db, sesion_conflicto)
        self.assert_failure("Crear sesión con conflicto", result)
        
        # 3. Obtener sesiones
        sesiones = crud.get_sesiones(self.db)
        self.log_test("Obtener sesiones", len(sesiones) >= 1, f"Encontradas {len(sesiones)} sesiones")
        
        # 4. Obtener sesiones por asignatura
        sesiones_asignatura = crud.get_sesiones_by_asignatura_id(self.db, asignatura.id)
        self.log_test("Obtener sesiones por asignatura", len(sesiones_asignatura) >= 1)
        
        # 5. Obtener sesiones por aula
        sesiones_aula = crud.get_sesiones_by_aula_id(self.db, aula.id)
        self.log_test("Obtener sesiones por aula", len(sesiones_aula) >= 1)
    
    def test_relationships(self):
        """Tests para relaciones entre entidades"""
        print("\n🔗 === TESTS RELACIONES ===")
        
        asignatura = self.test_data.get('asignatura')
        profesor = self.test_data.get('profesor')
        mencion = self.test_data.get('mencion')
        
        # 1. Relación profesor-asignatura
        if profesor and asignatura:
            try:
                from schemas.profesor import ProfesorAsignaturaCreate
                rel_data = ProfesorAsignaturaCreate(
                    profesor_id=profesor.id,
                    asignatura_id=asignatura.id
                )
                result = crud.create_profesor_asignatura(self.db, rel_data)
                self.assert_success("Crear relación profesor-asignatura", result)
            except ImportError:
                self.log_test("Crear relación profesor-asignatura", False, "Schema no disponible")
        
        # 2. Relación asignatura-mención
        if asignatura and mencion:
            try:
                from schemas.asignatura import AsignaturaMencionCreate
                rel_data = AsignaturaMencionCreate(
                    asignatura_id=asignatura.id,
                    mencion_id=mencion.id
                )
                result = crud.create_asignatura_mencion(self.db, rel_data)
                self.assert_success("Crear relación asignatura-mención", result)
            except ImportError:
                self.log_test("Crear relación asignatura-mención", False, "Schema no disponible")
    
    def run_all_tests(self):
        """Ejecuta todos los tests de la suite"""
        print("🚀 === INICIANDO TESTS CRUD ===")
        print(f"📊 Configuración: DEBUG={settings.DEBUG}")
        
        # Ejecutar tests en orden de dependencias
        self.test_grado_crud()
        self.test_mencion_crud()
        self.test_aula_crud()
        self.test_profesor_crud()
        self.test_asignatura_crud()
        self.test_restriccion_crud()
        self.test_sesion_crud()
        self.test_relationships()
        
        # Resumen final
        total_tests = self.passed_tests + self.failed_tests
        print(f"\n📊 === RESUMEN DE TESTS ===")
        print(f"✅ Tests exitosos: {self.passed_tests}")
        print(f"❌ Tests fallidos: {self.failed_tests}")
        print(f"📈 Total tests: {total_tests}")
        
        if self.failed_tests == 0:
            print("🎉 ¡Todos los tests pasaron exitosamente!")
        else:
            print(f"⚠️ {self.failed_tests} tests fallaron. Revisar implementación.")


def main():
    """Función principal para ejecutar los tests"""
    print("🧪 === SUITE DE TESTS CRUD ===")
    
    # Verificar si la base de datos está vacía
    db = SessionLocal()
    grado_count = db.execute(text("SELECT COUNT(*) FROM grados")).fetchone()[0]
    if grado_count == 0:
        print("Base de datos vacía - Creando datos de prueba")
    else:
        print(f"Base de datos contiene {grado_count} grados existentes")
    
    # Ejecutar tests
    tester = TestSuite()
    tester.cleanup_database()
    tester.run_all_tests()
    
    # Cerrar conexión
    db.close()


if __name__ == "__main__":
    main()
