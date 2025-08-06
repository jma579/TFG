from database import engine, Base
from models import (
    Grado, Mencion, Asignatura, AsignaturaGrado, AsignaturaMencion,
    Profesor, ProfesorAsignatura, Aula, Sesion, Restriccion
)
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_modelos_importacion():
    """Prueba que todos los modelos se puedan importar correctamente"""
    print("🧪 PRUEBA DE IMPORTACIÓN DE MODELOS")
    print("=" * 50)
    
    modelos = [
        ('Grado', Grado),
        ('Mencion', Mencion),
        ('Asignatura', Asignatura),
        ('AsignaturaGrado', AsignaturaGrado),
        ('AsignaturaMencion', AsignaturaMencion),
        ('Profesor', Profesor),
        ('ProfesorAsignatura', ProfesorAsignatura),
        ('Aula', Aula),
        ('Sesion', Sesion),
        ('Restriccion', Restriccion),
    ]
    
    for nombre, modelo in modelos:
        try:
            # Verificar que el modelo tiene tablename
            assert hasattr(modelo, '__tablename__')
            # Verificar que tiene la columna id
            assert hasattr(modelo, 'id')
            print(f"✅ {nombre:<20} - Tabla: {modelo.__tablename__}")
        except Exception as e:
            print(f"❌ {nombre:<20} - Error: {e}")
            return False
    
    return True

def test_relationships():
    """Prueba que las relationships estén correctamente definidas"""
    print("\n🔗 PRUEBA DE RELATIONSHIPS")
    print("=" * 50)
    
    # Verificar relationships críticas
    tests = [
        # (Modelo, atributo_relationship, descripción)
        (Grado, 'menciones', 'Grado -> Menciones'),
        (Grado, 'asignaturas', 'Grado -> AsignaturaGrado'),
        (Mencion, 'grado', 'Mencion -> Grado'),
        (Mencion, 'asignaturas', 'Mencion -> AsignaturaMencion'),
        (Asignatura, 'grados', 'Asignatura -> AsignaturaGrado'),
        (Asignatura, 'menciones', 'Asignatura -> AsignaturaMencion'),
        (Asignatura, 'profesores', 'Asignatura -> ProfesorAsignatura'),
        (Asignatura, 'sesiones', 'Asignatura -> Sesiones'),
        (Profesor, 'asignaturas', 'Profesor -> ProfesorAsignatura'),
        (Profesor, 'sesiones', 'Profesor -> Sesiones'),
        (Aula, 'sesiones', 'Aula -> Sesiones'),
        (Sesion, 'asignatura', 'Sesion -> Asignatura'),
        (Sesion, 'profesor', 'Sesion -> Profesor'),
        (Sesion, 'aula', 'Sesion -> Aula'),
    ]
    
    errores = 0
    for modelo, attr, descripcion in tests:
        try:
            assert hasattr(modelo, attr), f"Falta atributo {attr}"
            print(f"✅ {descripcion}")
        except AssertionError as e:
            print(f"❌ {descripcion} - {e}")
            errores += 1
    
    return errores == 0

def test_foreign_keys():
    """Prueba que las foreign keys estén correctamente definidas"""
    print("\n🔑 PRUEBA DE FOREIGN KEYS")
    print("=" * 50)
    
    # Verificar foreign keys
    fk_tests = [
        (Mencion, 'grado_id', 'menciones.grado_id -> grados.id'),
        (AsignaturaGrado, 'asignatura_id', 'asignatura_grado.asignatura_id -> asignaturas.id'),
        (AsignaturaGrado, 'grado_id', 'asignatura_grado.grado_id -> grados.id'),
        (AsignaturaMencion, 'asignatura_id', 'asignatura_mencion.asignatura_id -> asignaturas.id'),
        (AsignaturaMencion, 'mencion_id', 'asignatura_mencion.mencion_id -> menciones.id'),
        (ProfesorAsignatura, 'profesor_id', 'profesor_asignatura.profesor_id -> profesores.id'),
        (ProfesorAsignatura, 'asignatura_id', 'profesor_asignatura.asignatura_id -> asignaturas.id'),
        (Sesion, 'asignatura_id', 'sesiones.asignatura_id -> asignaturas.id'),
        (Sesion, 'profesor_id', 'sesiones.profesor_id -> profesores.id'),
        (Sesion, 'aula_id', 'sesiones.aula_id -> aulas.id'),
        (Restriccion, 'asignatura_id', 'restricciones.asignatura_id -> asignaturas.id'),
        (Restriccion, 'profesor_id', 'restricciones.profesor_id -> profesores.id'),
        (Restriccion, 'aula_id', 'restricciones.aula_id -> aulas.id'),
    ]
    
    errores = 0
    for modelo, attr, descripcion in fk_tests:
        try:
            assert hasattr(modelo, attr), f"Falta foreign key {attr}"
            column = getattr(modelo, attr)
            assert hasattr(column.property, 'columns'), f"{attr} no es una columna"
            print(f"✅ {descripcion}")
        except AssertionError as e:
            print(f"❌ {descripcion} - {e}")
            errores += 1
    
    return errores == 0

def test_creacion_tablas():
    """Prueba crear las tablas en la base de datos"""
    print("\n🏗️  PRUEBA DE CREACIÓN DE TABLAS")
    print("=" * 50)
    
    try:
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        print("✅ Todas las tablas creadas exitosamente")
        
        # Verificar que las tablas existen
        with engine.connect() as conn:
            # Para SQLite
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tablas = [row[0] for row in result]
            
            tablas_esperadas = [
                'grados', 'menciones', 'asignaturas', 'asignatura_grado',
                'asignatura_mencion', 'profesores', 'profesor_asignatura',
                'aulas', 'sesiones', 'restricciones'
            ]
            
            for tabla in tablas_esperadas:
                if tabla in tablas:
                    print(f"✅ Tabla {tabla} existe en la BD")
                else:
                    print(f"❌ Tabla {tabla} NO existe en la BD")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        return False

def main():
    """Ejecuta todas las pruebas"""
    print("🧪 PRUEBAS DE VALIDACIÓN DE MODELOS")
    print("=" * 60)
    
    pruebas = [
        ("Importación de modelos", test_modelos_importacion),
        ("Relationships", test_relationships),
        ("Foreign Keys", test_foreign_keys),
        ("Creación de tablas", test_creacion_tablas),
    ]
    
    resultados = []
    for nombre, funcion in pruebas:
        try:
            resultado = funcion()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"❌ Error inesperado en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Resumen
    print("\n📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    todas_exitosas = True
    for nombre, exitosa in resultados:
        estado = "✅ EXITOSA" if exitosa else "❌ FALLÓ"
        print(f"{estado:<12} {nombre}")
        if not exitosa:
            todas_exitosas = False
    
    print("\n" + "=" * 60)
    if todas_exitosas:
        print("🎉 ¡TODOS LOS MODELOS ESTÁN CORRECTAMENTE CONFIGURADOS!")
        print("🚀 Listos para usar en el backend.")
    else:
        print("⚠️  ALGUNOS MODELOS TIENEN PROBLEMAS. Revisa los errores arriba.")
    print("=" * 60)

if __name__ == "__main__":
    main()
