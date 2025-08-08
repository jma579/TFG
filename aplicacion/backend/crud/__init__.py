"""
CRUD Operations Package

Este paquete contiene todas las operaciones CRUD para las entidades del sistema.
Cada módulo maneja las operaciones básicas de base de datos con:
- Validaciones de integridad referencial
- Manejo robusto de errores  
- Logging estructurado
- Consultas simples de filtrado
"""

# Importaciones de funciones CRUD principales
from .asignatura import (
    create_asignatura, get_asignaturas, get_asignatura_by_id, 
    update_asignatura, delete_asignatura,
    create_asignatura_grado, delete_asignatura_grado, get_asignaturas_by_grado_id,
    create_asignatura_mencion, delete_asignatura_mencion, get_asignaturas_by_mencion_id
)

from .profesor import (
    create_profesor, get_profesores, get_profesor_by_id,
    update_profesor, delete_profesor,
    create_profesor_asignatura, delete_profesor_asignatura, 
    get_profesores_by_asignatura_id
)

from .grado import (
    create_grado, get_grados, get_grado_by_id, get_grado_by_nombre,
    update_grado, delete_grado
)

from .aula import (
    create_aula, get_aulas, get_aula_by_id,
    update_aula, delete_aula, get_aulas_by_tipo
)

from .mencion import (
    create_mencion, get_menciones, get_mencion_by_id,
    update_mencion, delete_mencion, get_menciones_by_grado_id
)

from .restriccion import (
    create_restriccion, get_restricciones, get_restriccion_by_id,
    update_restriccion, delete_restriccion, get_restricciones_filtradas
)

from .sesion import (
    create_sesion, get_sesiones, get_sesion_by_id,
    update_sesion, delete_sesion,
    get_sesiones_with_relations, get_sesion_by_id_with_relations,
    get_sesiones_by_profesor, get_sesiones_by_asignatura, get_sesiones_by_aula
)

# Lista de todas las funciones exportadas para facilitar su uso
__all__ = [
    # Asignatura
    "create_asignatura", "get_asignaturas", "get_asignatura_by_id", 
    "update_asignatura", "delete_asignatura",
    "create_asignatura_grado", "delete_asignatura_grado", "get_asignaturas_by_grado_id",
    "create_asignatura_mencion", "delete_asignatura_mencion", "get_asignaturas_by_mencion_id",
    
    # Profesor
    "create_profesor", "get_profesores", "get_profesor_by_id",
    "update_profesor", "delete_profesor",
    "create_profesor_asignatura", "delete_profesor_asignatura", 
    "get_profesores_by_asignatura_id",
    
    # Grado
    "create_grado", "get_grados", "get_grado_by_id", "get_grado_by_nombre",
    "update_grado", "delete_grado",
    
    # Aula
    "create_aula", "get_aulas", "get_aula_by_id",
    "update_aula", "delete_aula", "get_aulas_by_tipo",
    
    # Mención
    "create_mencion", "get_menciones", "get_mencion_by_id",
    "update_mencion", "delete_mencion", "get_menciones_by_grado_id",
    
    # Restricción
    "create_restriccion", "get_restricciones", "get_restriccion_by_id",
    "update_restriccion", "delete_restriccion", "get_restricciones_filtradas",
    
    # Sesión
    "create_sesion", "get_sesiones", "get_sesion_by_id",
    "update_sesion", "delete_sesion",
    "get_sesiones_with_relations", "get_sesion_by_id_with_relations",
    "get_sesiones_by_profesor", "get_sesiones_by_asignatura", "get_sesiones_by_aula",
]