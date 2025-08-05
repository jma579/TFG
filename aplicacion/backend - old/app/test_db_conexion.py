from database import SessionLocal

def probar_conexion():
    try:
        db = SessionLocal()
        print("✅ Conexión a la base de datos establecida correctamente.")
    except Exception as e:
        print("❌ Error al conectar a la base de datos:", e)
    finally:
        db.close()

probar_conexion()
