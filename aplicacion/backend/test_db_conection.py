from database import SessionLocal, engine, get_db
from config import settings
from sqlalchemy import text
import logging

# Configurar logging para ver más detalles
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def probar_configuracion():
    """Muestra la configuración actual"""
    print("=" * 60)
    print("🔧 CONFIGURACIÓN ACTUAL")
    print("=" * 60)
    print(f"📱 Aplicación: {settings.APP_NAME}")
    print(f"🐛 Debug: {settings.DEBUG}")
    print(f"📊 Base de datos: {settings.DATABASE_URL}")
    print(f"🗃️  Tipo: {'SQLite' if settings.is_sqlite else 'PostgreSQL'}")
    print(f"📁 Directorio uploads: {settings.UPLOAD_DIR}")
    print(f"📏 Tamaño máximo archivo: {settings.MAX_FILE_SIZE / (1024*1024):.0f}MB")
    print()

def probar_conexion():
    """Prueba la conexión básica a la base de datos"""
    print("🔌 PROBANDO CONEXIÓN BÁSICA")
    print("-" * 40)
    try:
        db = SessionLocal()
        print("✅ Conexión a la base de datos establecida correctamente.")
        
        # Probar una query simple
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.scalar()
        print(f"✅ Query de prueba ejecutada: SELECT 1 = {test_value}")
        
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()
            print("🔒 Conexión cerrada correctamente.")
    
    return True

def probar_dependencia():
    """Prueba la función get_db()"""
    print("\n🔗 PROBANDO DEPENDENCIA GET_DB")
    print("-" * 40)
    try:
        # Simular el uso de la dependencia
        db_generator = get_db()
        db = next(db_generator)
        
        # Probar una query
        result = db.execute(text("SELECT 'Dependencia funcionando' as mensaje"))
        mensaje = result.scalar()
        print(f"✅ Dependencia get_db() funciona: {mensaje}")
        
        # Cerrar la dependencia
        try:
            next(db_generator)
        except StopIteration:
            print("✅ Dependencia cerrada correctamente.")
            
    except Exception as e:
        print(f"❌ Error en dependencia get_db(): {e}")
        return False
    
    return True

def probar_motor():
    """Prueba el motor de base de datos directamente"""
    print("\n⚙️  PROBANDO MOTOR DE BASE DE DATOS")
    print("-" * 40)
    try:
        # Probar conexión del motor
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 'Motor funcionando' as status"))
            status = result.scalar()
            print(f"✅ Motor de base de datos: {status}")
            
        return True
    except Exception as e:
        print(f"❌ Error en motor de base de datos: {e}")
        return False

def main():
    """Función principal que ejecuta todas las pruebas"""
    print("🧪 PRUEBAS DE CONEXIÓN A BASE DE DATOS")
    print("=" * 60)
    
    # Mostrar configuración
    probar_configuracion()
    
    # Ejecutar pruebas
    pruebas = [
        ("Conexión básica", probar_conexion),
        ("Dependencia get_db", probar_dependencia),
        ("Motor directo", probar_motor),
    ]
    
    resultados = []
    for nombre, funcion in pruebas:
        try:
            resultado = funcion()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"❌ Error inesperado en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Mostrar resumen
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
        print("🎉 ¡TODAS LAS PRUEBAS EXITOSAS! La configuración está funcionando correctamente.")
    else:
        print("⚠️  ALGUNAS PRUEBAS FALLARON. Revisa la configuración.")
    print("=" * 60)

if __name__ == "__main__":
    main()
