#!/usr/bin/env python3
"""
Script para probar conexión a base de datos
"""

print('🔍 Testing database connection...')
try:
    from db.session import test_connection, get_db_info, engine
    
    print('📊 Información del engine:')
    print(f'  - Nombre: {engine.name}')
    print(f'  - Driver: {engine.driver}')
    print(f'  - URL: {engine.url}')
    
    print('\n🔗 Probando conexión...')
    if test_connection():
        print('✅ Conexión a base de datos exitosa!')
        
        print('\n📋 Información detallada:')
        info = get_db_info()
        for key, value in info.items():
            print(f'  - {key}: {value}')
            
    else:
        print('❌ Error de conexión a base de datos')
        
    print('\n🗂️ Verificando archivo de base de datos...')
    from pathlib import Path
    from config.settings import get_settings
    
    settings = get_settings()
    # La DB debería estar en aplicacion/database/dev.db
    db_path = settings.base_dir.parent / "database" / "dev.db"
    
    if db_path.exists():
        print(f'✅ Archivo DB encontrado: {db_path}')
        print(f'  - Tamaño: {db_path.stat().st_size} bytes')
    else:
        print(f'⚠️ Archivo DB no encontrado: {db_path}')
        print('  (Se creará al arrancar la app)')
    
    print('🎉 Database test completado!')
    
except Exception as e:
    print(f'❌ Error en database: {e}')
    import traceback
    traceback.print_exc()
