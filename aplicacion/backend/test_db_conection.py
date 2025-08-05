from database import SessionLocal  # Importación desde el módulo database local

def probar_conexion():
    try:
        db = SessionLocal()
        print("✅ Conexión a la base de datos establecida correctamente.")
    except Exception as e:
        print("❌ Error al conectar a la base de datos:", e)
    finally:
        if 'db' in locals():
            db.close()

probar_conexion()
