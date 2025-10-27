from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Time, Boolean, Text, Enum,
    ForeignKey, UniqueConstraint, Index, DateTime, CheckConstraint, func
)
from sqlalchemy.orm import relationship, declarative_base

# Importar enums desde constants (mantén la ruta que ya usas en tu proyecto)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.constants.enums import (
    TipoPrograma, Periodo, ModalidadAsignatura, Idioma, TipoAula,
    ModalidadSesion, TipoGrupoDocente, TipoRecurrencia, DiaSemana,
    TipoRestriccion, DurezaRestriccion, SeveridadConflicto,
    TipoConflicto, EstadoConflicto, TipoAsignatura
)

Base = declarative_base()

# ============================
#  Catálogo académico
# ============================

class Programa(Base):
    __tablename__ = "programas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoPrograma), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("nombre", "tipo", name="uq_programa_nombre_tipo"),
    )

    # Relaciones
    menciones = relationship("Mencion", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)
    programa_asignaturas = relationship("ProgramaAsignatura", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)
    documentos = relationship("Documento", back_populates="programa", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="programas_asignaturas", viewonly=True, overlaps="programa_asignaturas,programas")


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

    # Relaciones
    grupos_docentes = relationship("GrupoDocente", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)
    programa_asignaturas = relationship("ProgramaAsignatura", back_populates="asignatura", passive_deletes=True)
    asignatura_menciones = relationship("AsignaturaMencion", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)
    profesores_asignaturas = relationship("ProfesorAsignatura", back_populates="asignatura", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia (solo lectura)
    programas = relationship("Programa", secondary="programas_asignaturas", viewonly=True, overlaps="programa_asignaturas,asignaturas")
    menciones = relationship("Mencion", secondary="asignaturas_menciones", viewonly=True, overlaps="asignatura_menciones,asignaturas")


class Mencion(Base):
    __tablename__ = "menciones"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("programa_id", "nombre", name="uq_mencion_programa_nombre"),
        Index("ix_mencion_programa", "programa_id"),
    )

    programa = relationship("Programa", back_populates="menciones", passive_deletes=True)
    asignatura_menciones = relationship("AsignaturaMencion", back_populates="mencion", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="asignaturas_menciones", viewonly=True, overlaps="asignatura_menciones,asignaturas")


# ============================
#  Personas y recursos
# ============================

class Profesor(Base):
    __tablename__ = "profesores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    apellidos = Column(String(200), nullable=False)
    email = Column(String(200), unique=True)
    telefono = Column(String(20), unique=True)
    departamento = Column(String(200))
    activo = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("nombre", "apellidos", name="uq_profesor_nombre_apellidos"),
        Index("ix_profesor_nombre_apellidos", "nombre", "apellidos"),  # Índice para búsquedas
    )

    profesores_asignaturas = relationship("ProfesorAsignatura", back_populates="profesor", passive_deletes=True)
    profesores_sesiones = relationship("ProfesorSesion", back_populates="profesor", passive_deletes=True)
    restricciones = relationship("Restriccion", back_populates="profesor", passive_deletes=True)
    conflictos = relationship("Conflicto", back_populates="profesor", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="profesores_asignaturas", viewonly=True, overlaps="profesores_asignaturas,profesores")
    sesiones = relationship("Sesion", secondary="profesores_sesiones", viewonly=True, overlaps="profesores_sesiones,sesiones")
    conflictos = relationship("Conflicto", back_populates="profesor", passive_deletes=True)

    # Conveniencia (solo lectura)
    asignaturas = relationship("Asignatura", secondary="profesores_asignaturas", viewonly=True, overlaps="profesores_asignaturas,asignaturas")
    sesiones = relationship("Sesion", secondary="profesores_sesiones", viewonly=True, overlaps="profesores_sesiones,sesiones")


class Aula(Base):
    __tablename__ = "aulas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False, unique=True)
    codigo = Column(String(50), nullable=False, unique=True)
    tipo = Column(Enum(TipoAula), nullable=False)
    capacidad = Column(Integer)

    __table_args__ = (
        CheckConstraint("capacidad > 0", name="ck_aula_capacidad_positiva"),
    )

    sesiones = relationship("Sesion", back_populates="aula", passive_deletes=True)
    restricciones = relationship("Restriccion", back_populates="aula", passive_deletes=True)
    conflictos = relationship("Conflicto", back_populates="aula", passive_deletes=True)


class Restriccion(Base):
    __tablename__ = "restricciones"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoRestriccion), nullable=False)
    dureza = Column(Enum(DurezaRestriccion), nullable=False)
    motivo = Column(Text)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="SET NULL"))
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"))
    # Modelos de ventana: semanal o fechada
    dia_semana = Column(Enum(DiaSemana))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    inicio = Column(DateTime)
    fin = Column(DateTime)

    __table_args__ = (
        # XOR exacto: o profesor o aula, pero no ambos y no ninguno
        CheckConstraint(
            "((profesor_id IS NULL AND aula_id IS NOT NULL) OR (profesor_id IS NOT NULL AND aula_id IS NULL))",
            name="ck_restriccion_exclusive_parent"
        ),
        Index("ix_restriccion_profesor", "profesor_id"),
        Index("ix_restriccion_aula", "aula_id"),
    )

    profesor = relationship("Profesor", back_populates="restricciones")
    aula = relationship("Aula", back_populates="restricciones")
    conflictos = relationship("Conflicto", back_populates="restriccion", passive_deletes=True)


# ============================
#  Docencia / planificación
# ============================

class GrupoDocente(Base):
    __tablename__ = "grupos_docentes"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    codigo = Column(String(50), nullable=False)
    tipo = Column(Enum(TipoGrupoDocente), nullable=False)
    curso = Column(Integer)  # opcional: 1,2,3,4...
    turno = Column(String(30))  # opcional

    __table_args__ = (
        UniqueConstraint("asignatura_id", "codigo", name="uq_grupo_asig_codigo"),
        Index("ix_grupo_asignatura", "asignatura_id"),
    )

    asignatura = relationship("Asignatura", back_populates="grupos_docentes", passive_deletes=True)
    sesiones = relationship("Sesion", back_populates="grupo_docente", cascade="all, delete-orphan", passive_deletes=True)


class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True)
    grupo_docente_id = Column(Integer, ForeignKey("grupos_docentes.id", ondelete="CASCADE"), nullable=False)
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"), nullable=False)
    modalidad = Column(Enum(ModalidadSesion), nullable=False)
    tipo_recurrencia = Column(Enum(TipoRecurrencia), nullable=False)

    # Si semanal:
    dia_semana = Column(Enum(DiaSemana))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)

    # Si fechada:
    inicio = Column(DateTime)
    fin = Column(DateTime)

    __table_args__ = (
        Index("ix_sesion_grupo", "grupo_docente_id"),
    )

    grupo_docente = relationship("GrupoDocente", back_populates="sesiones", passive_deletes=True)
    aula = relationship("Aula", back_populates="sesiones", passive_deletes=True)

    profesores_sesiones = relationship("ProfesorSesion", back_populates="sesion", cascade="all, delete-orphan", passive_deletes=True)

    # Conveniencia
    profesores = relationship("Profesor", secondary="profesores_sesiones", viewonly=True, overlaps="profesores_sesiones,profesores")

    conflictos_sesion_1 = relationship("Conflicto", back_populates="sesion", foreign_keys="Conflicto.sesion_id", passive_deletes=True)
    conflictos_sesion_2 = relationship("Conflicto", back_populates="sesion_2", foreign_keys="Conflicto.sesion_2_id", passive_deletes=True)


# ============================
#  Tablas de asociación
# ============================

class ProgramaAsignatura(Base):
    __tablename__ = "programas_asignaturas"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    curso = Column(Integer)  # p.ej. 1..4
    tipo_asignatura = Column(Enum(TipoAsignatura))

    __table_args__ = (
        UniqueConstraint("programa_id", "asignatura_id", name="uq_programa_asignatura"),
        Index("ix_prog_asig_programa", "programa_id"),
        Index("ix_prog_asig_asignatura", "asignatura_id"),
    )

    programa = relationship("Programa", back_populates="programa_asignaturas", passive_deletes=True)
    asignatura = relationship("Asignatura", back_populates="programa_asignaturas", passive_deletes=True)


class AsignaturaMencion(Base):
    __tablename__ = "asignaturas_menciones"
    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    mencion_id = Column(Integer, ForeignKey("menciones.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("asignatura_id", "mencion_id", name="uq_asignatura_mencion"),
        Index("ix_asig_men_asignatura", "asignatura_id"),
        Index("ix_asig_men_mencion", "mencion_id"),
    )

    asignatura = relationship("Asignatura", back_populates="asignatura_menciones", passive_deletes=True)
    mencion = relationship("Mencion", back_populates="asignatura_menciones", passive_deletes=True)


class ProfesorAsignatura(Base):
    __tablename__ = "profesores_asignaturas"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("profesor_id", "asignatura_id", name="uq_profesor_asignatura"),
        Index("ix_prof_asig_profesor", "profesor_id"),
        Index("ix_prof_asig_asignatura", "asignatura_id"),
    )

    profesor = relationship("Profesor", back_populates="profesores_asignaturas", passive_deletes=True)
    asignatura = relationship("Asignatura", back_populates="profesores_asignaturas", passive_deletes=True)


class ProfesorSesion(Base):
    __tablename__ = "profesores_sesiones"
    id = Column(Integer, primary_key=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False)
    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False)
    rol_en_sesion = Column(String(30), nullable=True)  # p.ej. Docente, Apoyo...

    __table_args__ = (
        UniqueConstraint("profesor_id", "sesion_id", name="uq_profesor_sesion"),
        Index("ix_prof_ses_profesor", "profesor_id"),
        Index("ix_prof_ses_sesion", "sesion_id"),
    )

    profesor = relationship("Profesor", back_populates="profesores_sesiones", passive_deletes=True)
    sesion = relationship("Sesion", back_populates="profesores_sesiones", passive_deletes=True)


# ============================
#  Detección de conflictos
# ============================

class Conflicto(Base):
    __tablename__ = "conflictos"
    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoConflicto), nullable=False)
    severidad = Column(Enum(SeveridadConflicto), nullable=False)
    estado = Column(Enum(EstadoConflicto), nullable=False, default=EstadoConflicto.ABIERTO)

    sesion_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False)
    sesion_2_id = Column(Integer, ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="SET NULL"))
    aula_id = Column(Integer, ForeignKey("aulas.id", ondelete="SET NULL"))
    restriccion_id = Column(Integer, ForeignKey("restricciones.id", ondelete="SET NULL"))

    descripcion = Column(Text)
    hash_deteccion = Column(String(64), nullable=False, unique=True)
    creado_en = Column(DateTime, default=func.now(), nullable=False)
    resuelto_en = Column(DateTime)

    __table_args__ = (
        CheckConstraint(
            "sesion_2_id IS NULL OR sesion_id <> sesion_2_id",
            name="ck_conflicto_sesiones_distintas"
        ),
        Index("ix_conflicto_sesion", "sesion_id"),
        Index("ix_conflicto_sesion_2", "sesion_2_id"),
        Index("ix_conflicto_profesor", "profesor_id"),
        Index("ix_conflicto_aula", "aula_id"),
        Index("ix_conflicto_restriccion", "restriccion_id"),
    )

    sesion = relationship("Sesion", foreign_keys=[sesion_id], back_populates="conflictos_sesion_1", passive_deletes=True)
    sesion_2 = relationship("Sesion", foreign_keys=[sesion_2_id], back_populates="conflictos_sesion_2", passive_deletes=True)
    profesor = relationship("Profesor", back_populates="conflictos", passive_deletes=True)
    aula = relationship("Aula", back_populates="conflictos", passive_deletes=True)
    restriccion = relationship("Restriccion", back_populates="conflictos", passive_deletes=True)


# ============================
#  Ingesta / OCR / trazabilidad
# ============================

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True)
    programa_id = Column(Integer, ForeignKey("programas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(250), nullable=False)
    tipo = Column(String(30), nullable=False)  # p.ej. PDF, CSV...
    ruta = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=func.now(), nullable=False)

    programa = relationship("Programa", back_populates="documentos", passive_deletes=True)
    import_runs = relationship("ImportRun", back_populates="documento", cascade="all, delete-orphan", passive_deletes=True)
    extracciones = relationship("Extraccion", back_populates="documento", passive_deletes=True)


class ImportRun(Base):
    __tablename__ = "import_runs"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String(20), nullable=False)  # Enum-like: SUCCESS, ERROR, PARTIAL
    inicio_en = Column(DateTime, default=func.now(), nullable=False)
    fin_en = Column(DateTime)
    resumen = Column(Text)

    documento = relationship("Documento", back_populates="import_runs", passive_deletes=True)
    extracciones = relationship("Extraccion", back_populates="import_run", cascade="all, delete-orphan", passive_deletes=True)


class Extraccion(Base):
    __tablename__ = "extracciones"
    id = Column(Integer, primary_key=True)
    import_run_id = Column(Integer, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)  # Enum-like: FICHA, HORARIO, METADATOS
    bloque = Column(String(80), nullable=False)
    contenido = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=func.now(), nullable=False)

    import_run = relationship("ImportRun", back_populates="extracciones", passive_deletes=True)
    documento = relationship("Documento", back_populates="extracciones", passive_deletes=True)
