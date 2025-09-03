# Importar Base para registrar metadata
from database.models import Base

# Importar todos los modelos para registrar en metadata
from .catalogo.programa import Programa
from .catalogo.asignatura import Asignatura
from .catalogo.mencion import Mencion
from .catalogo.asociaciones import ProgramaAsignatura, AsignaturaMencion

from .recursos.profesor import Profesor
from .recursos.aula import Aula
from .recursos.restriccion import Restriccion
from .recursos.asociaciones import ProfesorAsignatura

from .docencia.grupo_docente import GrupoDocente
from .docencia.sesion import Sesion
from .docencia.asociaciones import ProfesorSesion

from .conflictos.conflicto import Conflicto

from .ingesta.documento import Documento
from .ingesta.import_run import ImportRun
from .ingesta.extraccion import Extraccion

# Exportar todos los modelos
__all__ = [
    'Base',
    'Programa', 'Asignatura', 'Mencion', 'ProgramaAsignatura', 'AsignaturaMencion',
    'Profesor', 'Aula', 'Restriccion', 'ProfesorAsignatura',
    'GrupoDocente', 'Sesion', 'ProfesorSesion',
    'Conflicto',
    'Documento', 'ImportRun', 'Extraccion'
]