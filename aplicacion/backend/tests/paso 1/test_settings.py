#!/usr/bin/env python3
"""
Script para probar configuración de settings
"""

print('🔍 Testing settings configuration...')
try:
    from config.settings import get_settings
    
    settings = get_settings()
    
    print(f'✅ Database URL: {settings.database_url}')
    print(f'✅ Debug mode: {settings.debug}')
    print(f'✅ Log level: {settings.log_level}')
    print(f'✅ CORS origins: {settings.cors_origins}')
    print(f'✅ API prefix: {settings.api_v0_prefix}')
    print(f'✅ Upload path: {settings.upload_path}')
    print(f'✅ Base dir: {settings.base_dir}')
    print(f'✅ Default page size: {settings.default_page_size}')
    
    print('🎉 Settings configuración OK!')
    
except Exception as e:
    print(f'❌ Error en settings: {e}')
    import traceback
    traceback.print_exc()
