#!/usr/bin/env python3
"""
Script temporal para probar imports de la Fase 1
"""

print('🔍 Testing imports...')
try:
    from config.settings import get_settings
    print('✅ config.settings OK')
    
    from db.session import get_db, engine
    print('✅ db.session OK')
    
    from dependencias.common import pagination, get_current_settings
    print('✅ dependencias.common OK')
    
    from constants.enums import TipoPrograma, SeveridadConflicto
    print('✅ constants.enums OK')
    
    from constants.defaults import DEFAULT_API_TITLE
    print('✅ constants.defaults OK')
    
    print('🎉 Todos los imports principales funcionan!')
    
except Exception as e:
    print(f'❌ Error de importación: {e}')
    import traceback
    traceback.print_exc()
