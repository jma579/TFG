from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Time, Boolean, Text, Enum,
    ForeignKey, UniqueConstraint, Index, DateTime, func
)
from sqlalchemy.orm import relationship, declarative_base

# Importar enums desde constants
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.constants.enums import (
    TipoPrograma, Periodo, ModalidadAsignatura, Idioma, TipoAula,
    ModalidadSesion, TipoGrupoDocente, TipoRecurrencia, DiaSemana,
    TipoRestriccion, DurezaRestriccion, SeveridadConflicto, 
    TipoConflicto, EstadoConflicto
)

Base = declarative_base()

# ---------- CATÁLOGO ACADÉMICO ----------

class Programa(Base):
    __tablename__ = "programas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoPrograma), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    # No puede haber dos grados con el mismo nombre, ni dos másteres con el mismo nombre, pero sí un grado y un máster con el mismo nombre.
    __table_args__ = (UniqueConstraint('nombre', 'tipo', name='uq_nombre_tipo'),)


class Asignatura(Base):
    __tablename__ = "asignaturas"
    id = Column(Integer, primary_key=True)
    codigo_plan = Column(String(6), nullable=False, unique=True)
    nombre = Column(String(250), nullable=False, unique=True)
    periodo = Column(Enum(Periodo), nullable=False)
    ects = Column(Integer)
    modalidad = Column(Enum(ModalidadAsignatura), nullable=False)
    idioma = Column(Enum(Idioma), nullable=False, default=Idioma.ESPAÑOL)
    english_friendly = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, default=True, nullable=False)


class Mencion(Base):
    __tablename__ = "menciones"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False, unique=True)
    programa_id = Column(Integer, ForeignKey('programas.id', ondelete="CASCADE"), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

# ---------- PERSONAS Y RECURSOS ----------

class Profesor(Base):
    __tablename__ = "profesores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(20), nullable=False)
    apellido1 = Column(String(30), nullable=False)
    apellido2 = Column(String(30), nullable=True)
    email = Column(String(200), unique=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class Aula(Base):
    __tablename__ = "aulas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False, unique=True)
    codigo = Column(String(10), nullable=False, unique=True)
    capacidad = Column(Integer)
    tipo = Column(Enum(TipoAula), nullable=False)
    recursos = Column(Text)
    activo = Column(Boolean, default=True, nullable=False)

class Restriccion(Base):
    __tablename__ = "restricciones"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoRestriccion), nullable=False)
    dureza = Column(Enum(DurezaRestriccion), nullable=False)
    profesor_id = Column(Integer, ForeignKey('profesores.id', ondelete="CASCADE"), nullable=True)
    aula_id = Column(Integer, ForeignKey('aulas.id', ondelete="CASCADE"), nullable=True)
    inicio = Column(DateTime, nullable=False)
    fin = Column(DateTime, nullable=False)   
    detalles = Column(Text, nullable=True)
    
    # Constraint para garantizar que una restricción pertenece EXACTAMENTE a un profesor O a un aula
    __table_args__ = (
        # Exactamente uno de los dos debe ser NOT NULL
        # Se implementa con un check constraint a nivel de aplicación o base de datos
        Index('ix_restriccion_profesor', 'profesor_id'),
        Index('ix_restriccion_aula', 'aula_id'),
    )

# ---------- DOCENCIA ----------

class GrupoDocente(Base):
    __tablename__ = "grupos_docentes"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id', ondelete="CASCADE"), nullable=False)
    tipo = Column(Enum(TipoGrupoDocente), nullable=False)
    etiqueta = Column(String(5), nullable=False)
    descripcion = Column(String(100))
    
    __table_args__ = (UniqueConstraint('asignatura_id', 'etiqueta', name='uq_asignatura_etiqueta'),)

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True)
    grupo_docente_id = Column(Integer, ForeignKey('grupos_docentes.id', ondelete="CASCADE"), nullable=False)
    aula_id = Column(Integer, ForeignKey('aulas.id', ondelete="SET NULL"))
    modalidad = Column(Enum(ModalidadSesion))
    tipo_recurrencia = Column(Enum(TipoRecurrencia), nullable=False)
    # Si semanal:
    dia_semana = Column(Enum(DiaSemana))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    # Si fechada:
    inicio = Column(DateTime)
    fin = Column(DateTime)

# ---------- TABLAS PUENTE ----------

class ProgramaAsignatura(Base):
    __tablename__ = "programas_asignaturas"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey('programas.id', ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id', ondelete="CASCADE"), nullable=False)
    curso = Column(Integer)  # En qué curso del programa se imparte
    obligatoria = Column(Boolean, default=True, nullable=False)  # Si es obligatoria u optativa
    
    __table_args__ = (UniqueConstraint('programa_id', 'asignatura_id', name='uq_programa_asignatura'),)

class AsignaturaMencion(Base):
    __tablename__ = "asignaturas_menciones"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id', ondelete="CASCADE"), nullable=False)
    mencion_id = Column(Integer, ForeignKey('menciones.id', ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (UniqueConstraint('asignatura_id', 'mencion_id', name='uq_asignatura_mencion'),)

class ProfesorAsignatura(Base):
    __tablename__ = "profesores_asignaturas"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey('profesores.id', ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey('asignaturas.id', ondelete="CASCADE"), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    
    __table_args__ = (UniqueConstraint('profesor_id', 'asignatura_id', name='uq_profesor_asignatura'),)

class ProfesorSesion(Base):
    __tablename__ = "profesores_sesiones"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey('profesores.id', ondelete="CASCADE"), nullable=False)
    sesion_id = Column(Integer, ForeignKey('sesiones.id', ondelete="CASCADE"), nullable=False)
    rol_en_sesion = Column(String(40))
    __table_args__ = (UniqueConstraint('profesor_id', 'sesion_id', name='uq_profesor_sesion'),)

# ---------- VALIDACIONES / CONFLICTOS ----------

class Conflictos(Base):
    __tablename__ = "conflictos"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoConflicto), nullable=False)
    estado = Column(Enum(EstadoConflicto), default=EstadoConflicto.ABIERTO, nullable=False)
    severidad = Column(Enum(SeveridadConflicto), nullable=False)
    sesion_id = Column(Integer, ForeignKey('sesiones.id', ondelete="CASCADE"), nullable=False)
    sesion_2_id = Column(Integer, ForeignKey('sesiones.id', ondelete="CASCADE"))
    profesor_id = Column(Integer, ForeignKey('profesores.id', ondelete="SET NULL"))
    aula_id = Column(Integer, ForeignKey('aulas.id', ondelete="SET NULL"))
    restriccion_id = Column(Integer, ForeignKey('restricciones.id', ondelete="SET NULL"))
    detectado_en = Column(DateTime, default=func.now(), nullable=False)
    hash_deteccion = Column(String(80), unique=True)
    descripcion = Column(Text)
    
    __table_args__ = (
        # Evitar que sesion_id y sesion_2_id sean iguales
        # Un conflicto debe involucrar sesiones diferentes
        # Se implementa con un check constraint a nivel de aplicación o base de datos
        Index('ix_conflicto_sesion', 'sesion_id'),
        Index('ix_conflicto_sesion_2', 'sesion_2_id'),
    )

# ---------- BAJA PRIORIDAD (INGESTA / OCR / TRAZABILIDAD) ----------

class Documentos(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True)
    nombre_archivo = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False) # Enum: FICHA, HORARIO, OTRO
    programa_id = Column(Integer, ForeignKey('programas.id', ondelete="SET NULL"))
    ruta_almacenamiento = Column(String(500), nullable=False)
    subido_por = Column(String(150))
    creado_en = Column(DateTime, default=func.now(), nullable=False)

class ImportRuns(Base):
    __tablename__ = "import_runs"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey('documentos.id', ondelete="CASCADE"), nullable=False)
    estado = Column(String(20), nullable=False) # Enum: SUCCESS, ERROR, PARTIAL
    inicio_en = Column(DateTime, default=func.now(), nullable=False)
    fin_en = Column(DateTime)
    resumen = Column(Text)

class Extracciones(Base):
    __tablename__ = "extracciones"
    id = Column(Integer, primary_key=True)
    import_run_id = Column(Integer, ForeignKey('import_runs.id', ondelete="CASCADE"), nullable=False)
    documento_id = Column(Integer, ForeignKey('documentos.id', ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False) # Enum: FICHA, HORARIO, METADATOS
    bloque = Column(String(80), nullable=False)
    contenido = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=func.now(), nullable=False)
