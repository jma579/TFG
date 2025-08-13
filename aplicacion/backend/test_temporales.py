#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test simple para verificar el módulo conflictos_temporales
try:
    from core.deteccion_conflictos.conflictos_temporales import (
        detectar_todos_conflictos_temporales,
        detectar_solape_profesor,
        detectar_solape_aula,
        detectar_solape_asignatura,
        ConflictoTemporal
    )
    print("✅ Todas las importaciones exitosas")
    print("✅ Módulo conflictos_temporales funcionando correctamente")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
