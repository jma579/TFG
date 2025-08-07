"""
Test completo para verificar que todos los schemas funcionan correctamente
"""
from datetime import time
from constants.enums import DiaSemanaEnum, CuatrimestreEnum, TipoAulaEnum, TipoRestriccionEnum
from schemas.grado import GradoCreate, GradoUpdate
from schemas.mencion import MencionCreate, MencionUpdate
from schemas.asignatura import AsignaturaCreate, AsignaturaUpdate
from schemas.profesor import ProfesorCreate, ProfesorUpdate
from schemas.aula import AulaCreate, AulaUpdate
from schemas.sesion import SesionCreate, SesionUpdate
from schemas.restriccion import RestriccionCreate, RestriccionUpdate

def test_grado_schema():
    """Test completo del schema de Grado"""
    print("🧪 Probando schema Grado...")
    
    # Caso válido
    grado_data = {
        "nombre": "grado en ingeniería informática"
    }
    grado = GradoCreate(**grado_data)
    assert grado.nombre == "Grado En Ingeniería Informática"
    print("✅ Grado válido creado correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({"nombre": "AB"}, "nombre muy corto"),
        ({"nombre": "123"}, "solo números"),
        ({"nombre": ""}, "nombre vacío"),
        ({"nombre": "   "}, "solo espacios"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            GradoCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except ValueError:
            print(f"✅ Validación correcta: {descripcion}")
    
    # Test GradoUpdate
    update_data = {"nombre": "nuevo nombre"}
    update = GradoUpdate(**update_data)
    assert update.nombre == "Nuevo Nombre"
    print("✅ GradoUpdate funciona correctamente")
    
    return True

def test_mencion_schema():
    """Test completo del schema de Mención"""
    print("\n🧪 Probando schema Mención...")
    
    # Caso válido
    mencion_data = {
        "nombre": "computación",
        "grado_id": 1
    }
    mencion = MencionCreate(**mencion_data)
    assert mencion.nombre == "Computación"
    assert mencion.grado_id == 1
    print("✅ Mención válida creada correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({"nombre": "A", "grado_id": 1}, "nombre muy corto"),
        ({"nombre": "123", "grado_id": 1}, "solo números"),
        ({"nombre": "Válido", "grado_id": 0}, "grado_id inválido"),
        ({"nombre": "Válido", "grado_id": -1}, "grado_id negativo"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            MencionCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except ValueError:
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_asignatura_schema():
    """Test completo del schema de Asignatura"""
    print("\n🧪 Probando schema Asignatura...")
    
    # Caso válido
    asignatura_data = {
        "nombre": "programación orientada a objetos",
        "creditos": 6,
        "horas_semanales": 4,
        "curso": 2,
        "cuatrimestre": CuatrimestreEnum.PRIMERO
    }
    asignatura = AsignaturaCreate(**asignatura_data)
    assert asignatura.nombre == "Programación Orientada A Objetos"
    assert asignatura.creditos == 6
    print("✅ Asignatura válida creada correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({**asignatura_data, "creditos": 0}, "créditos = 0"),
        ({**asignatura_data, "creditos": 15}, "demasiados créditos"),
        ({**asignatura_data, "horas_semanales": 0}, "horas = 0"),
        ({**asignatura_data, "curso": 0}, "curso inválido"),
        ({**asignatura_data, "curso": 7}, "curso muy alto"),
        ({**asignatura_data, "nombre": "AB"}, "nombre muy corto"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            AsignaturaCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except ValueError:
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_profesor_schema():
    """Test completo del schema de Profesor"""
    print("\n🧪 Probando schema Profesor...")
    
    # Caso válido
    profesor_data = {
        "nombre": "dr. juan pérez garcía",
        "disponibilidad": {
            "lunes": ["08:00-10:00", "12:00-14:00"],
            "martes": ["10:00-12:00"],
            "miercoles": ["08:00-12:00"]
        }
    }
    profesor = ProfesorCreate(**profesor_data)
    assert profesor.nombre == "Dr. Juan Pérez García"
    print("✅ Profesor válido creado correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({"nombre": "Juan", "disponibilidad": {"lunes": ["08:00-10:00"]}}, "solo un nombre"),
        ({"nombre": "Juan Pérez", "disponibilidad": {"sabado": ["08:00-10:00"]}}, "día inválido"),
        ({"nombre": "Juan Pérez", "disponibilidad": {"lunes": ["8:00-10:00"]}}, "formato hora incorrecto"),
        ({"nombre": "Juan Pérez", "disponibilidad": {"lunes": ["10:00-08:00"]}}, "hora fin antes que inicio"),
        ({"nombre": "Juan Pérez", "disponibilidad": "no es dict"}, "disponibilidad no es diccionario"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            ProfesorCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except (ValueError, TypeError):
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_aula_schema():
    """Test completo del schema de Aula"""
    print("\n🧪 Probando schema Aula...")
    
    # Caso válido
    aula_data = {
        "nombre": "a1.01",
        "capacidad": 30,
        "tipo": TipoAulaEnum.TEORIA
    }
    aula = AulaCreate(**aula_data)
    assert aula.nombre == "A1.01"
    assert aula.capacidad == 30
    print("✅ Aula válida creada correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({"nombre": "", "capacidad": 30, "tipo": TipoAulaEnum.TEORIA}, "nombre vacío"),
        ({"nombre": "A1.01", "capacidad": 0, "tipo": TipoAulaEnum.TEORIA}, "capacidad = 0"),
        ({"nombre": "A1.01", "capacidad": 600, "tipo": TipoAulaEnum.TEORIA}, "capacidad muy alta"),
        ({"nombre": "LAB01", "capacidad": 30, "tipo": TipoAulaEnum.LABORATORIO}, "laboratorio con mucha capacidad"),
        ({"nombre": "MAGNA", "capacidad": 20, "tipo": TipoAulaEnum.MAGNA}, "aula magna con poca capacidad"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            AulaCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except ValueError:
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_sesion_schema():
    """Test completo del schema de Sesión"""
    print("\n🧪 Probando schema Sesión...")
    
    # Caso válido
    sesion_data = {
        "asignatura_id": 1,
        "profesor_id": 1,
        "aula_id": 1,
        "dia": DiaSemanaEnum.LUNES,
        "hora_inicio": time(8, 0),
        "hora_fin": time(10, 0)
    }
    sesion = SesionCreate(**sesion_data)
    assert sesion.dia == DiaSemanaEnum.LUNES
    print("✅ Sesión válida creada correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({**sesion_data, "asignatura_id": 0}, "asignatura_id = 0"),
        ({**sesion_data, "hora_inicio": time(7, 0)}, "hora muy temprano"),
        ({**sesion_data, "hora_inicio": time(21, 0)}, "hora muy tarde"),
        ({**sesion_data, "hora_inicio": time(8, 15)}, "minutos no válidos"),
        ({**sesion_data, "hora_fin": time(23, 0)}, "hora fin muy tarde"),
        ({**sesion_data, "hora_inicio": time(10, 0), "hora_fin": time(8, 0)}, "hora fin antes que inicio"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            SesionCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except ValueError:
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_restriccion_schema():
    """Test completo del schema de Restricción"""
    print("\n🧪 Probando schema Restricción...")
    
    # Caso válido
    restriccion_data = {
        "tipo": TipoRestriccionEnum.HORARIO_PROFESOR,
        "valor": {
            "dias_no_disponible": ["viernes"],
            "horario_maximo": "18:00",
            "razon": "Profesor de tiempo parcial"
        },
        "profesor_id": 1,
        "prioridad": 3
    }
    restriccion = RestriccionCreate(**restriccion_data)
    assert restriccion.tipo == TipoRestriccionEnum.HORARIO_PROFESOR
    print("✅ Restricción válida creada correctamente")
    
    # Casos inválidos
    casos_invalidos = [
        ({**restriccion_data, "prioridad": 0}, "prioridad muy baja"),
        ({**restriccion_data, "prioridad": 6}, "prioridad muy alta"),
        ({**restriccion_data, "valor": "no es dict"}, "valor no es diccionario"),
    ]
    
    for data, descripcion in casos_invalidos:
        try:
            RestriccionCreate(**data)
            print(f"❌ Debería haber fallado: {descripcion}")
            return False
        except (ValueError, TypeError):
            print(f"✅ Validación correcta: {descripcion}")
    
    return True

def test_enums():
    """Test de los enums"""
    print("\n🧪 Probando Enums...")
    
    # Test DiaSemanaEnum
    assert DiaSemanaEnum.LUNES == "lunes"
    assert DiaSemanaEnum.VIERNES == "viernes"
    print("✅ DiaSemanaEnum funciona correctamente")
    
    # Test CuatrimestreEnum
    assert CuatrimestreEnum.PRIMERO == "1"
    assert CuatrimestreEnum.ANUAL == "anual"
    print("✅ CuatrimestreEnum funciona correctamente")
    
    # Test TipoAulaEnum
    assert TipoAulaEnum.TEORIA == "teoria"
    assert TipoAulaEnum.LABORATORIO == "laboratorio"
    print("✅ TipoAulaEnum funciona correctamente")
    
    # Test TipoRestriccionEnum
    assert TipoRestriccionEnum.HORARIO_PROFESOR == "horario_profesor"
    print("✅ TipoRestriccionEnum funciona correctamente")
    
    return True

def main():
    """Ejecutar todos los tests"""
    print("🧪 TESTS COMPLETOS DE VALIDACIÓN DE SCHEMAS")
    print("=" * 70)
    
    tests = [
        ("Enums", test_enums),
        ("Grado", test_grado_schema),
        ("Mención", test_mencion_schema),
        ("Asignatura", test_asignatura_schema),
        ("Profesor", test_profesor_schema),
        ("Aula", test_aula_schema),
        ("Sesión", test_sesion_schema),
        ("Restricción", test_restriccion_schema),
    ]
    
    resultados = []
    for nombre, funcion in tests:
        try:
            resultado = funcion()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"❌ Error inesperado en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Resumen
    print("\n📊 RESUMEN DE PRUEBAS")
    print("=" * 70)
    todas_exitosas = True
    for nombre, exitosa in resultados:
        estado = "✅ EXITOSA" if exitosa else "❌ FALLÓ"
        print(f"{estado:<12} {nombre}")
        if not exitosa:
            todas_exitosas = False
    
    print("\n" + "=" * 70)
    if todas_exitosas:
        print("🎉 ¡TODOS LOS SCHEMAS FUNCIONAN CORRECTAMENTE!")
        print("🚀 Las validaciones están implementadas y funcionando.")
        print("📋 Schemas probados: Grado, Mención, Asignatura, Profesor, Aula, Sesión, Restricción")
        print("✨ Validaciones probadas: Formatos, rangos, lógica de negocio, enums")
    else:
        print("⚠️  ALGUNOS SCHEMAS TIENEN PROBLEMAS. Revisa los errores arriba.")
    print("=" * 70)
    
    return todas_exitosas

if __name__ == "__main__":
    main()
