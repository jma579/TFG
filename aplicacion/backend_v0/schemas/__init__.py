from constants.enums import *
from .grado import *
from .mencion import *
from .asignatura import *
from .profesor import *
from .aula import *
from .sesion import *
from .restriccion import *

# Importaciones específicas para resolver referencias circulares
from .grado import GradoOut
from .mencion import MencionOut
from .asignatura import AsignaturaOut
from .profesor import ProfesorOut
from .aula import AulaOut
from .sesion import SesionOut
from .restriccion import RestriccionOut

# Re-exportar todas las clases principales para facilitar las importaciones
__all__ = [
    # Enums
    'DiaSemanaEnum',
    'CuatrimestreEnum', 
    'TipoAulaEnum',
    'TipoRestriccionEnum',
    
    # Grado
    'GradoBase', 'GradoCreate', 'GradoUpdate', 'GradoOut', 'GradoDetallado',
    
    # Mención
    'MencionBase', 'MencionCreate', 'MencionUpdate', 'MencionOut', 'MencionDetallada',
    
    # Asignatura
    'AsignaturaBase', 'AsignaturaCreate', 'AsignaturaUpdate', 'AsignaturaOut', 'AsignaturaDetallada',
    'AsignaturaGradoBase', 'AsignaturaGradoCreate', 'AsignaturaGradoUpdate', 'AsignaturaGradoOut',
    'AsignaturaMencionBase', 'AsignaturaMencionCreate', 'AsignaturaMencionUpdate', 'AsignaturaMencionOut',
    
    # Profesor
    'ProfesorBase', 'ProfesorCreate', 'ProfesorUpdate', 'ProfesorOut', 'ProfesorDetallado',
    'ProfesorAsignaturaBase', 'ProfesorAsignaturaCreate', 'ProfesorAsignaturaUpdate', 
    'ProfesorAsignaturaOut', 'ProfesorAsignaturaDetallado',
    
    # Aula
    'AulaBase', 'AulaCreate', 'AulaUpdate', 'AulaOut', 'AulaDetallada',
    
    # Sesión
    'SesionBase', 'SesionCreate', 'SesionUpdate', 'SesionOut', 'SesionDetallada',
    'ConsultaHorario', 'ConflictoHorario',
    
    # Restricción
    'RestriccionBase', 'RestriccionCreate', 'RestriccionUpdate', 'RestriccionOut', 'RestriccionDetallada',
    'ConsultaRestricciones', 'ValidacionRestriccion', 'ResultadoValidacion',
]
