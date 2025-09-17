# Roadmap Backend v1.0 - Sistema de Detección de Conflictos en Horarios Académicos

## Índice

1. [Visión General](#visión-general)
2. [Fase 1: Infraestructura Base](#fase-1-infraestructura-base)
3. [Fase 2: Módulos Core](#fase-2-módulos-core)
4. [Fase 3: Módulos de Dominio](#fase-3-módulos-de-dominio)
5. [Fase 4: Lógica de Negocio Crítica](#fase-4-lógica-de-negocio-crítica)
6. [Fase 5: Integración y Testing](#fase-5-integración-y-testing)
7. [Fase 6: Optimización y Deploy](#fase-6-optimización-y-deploy)
8. [Criterios de Aceptación](#criterios-de-aceptación)
9. [Dependencias y Herramientas](#dependencias-y-herramientas)

---

## Visión General

### Objetivo

Desarrollar un backend completo en FastAPI que permita:

- Gestionar catálogo académico (programas, asignaturas, menciones)
- Administrar recursos (profesores, aulas)
- Planificar docencia (grupos, sesiones)
- Definir restricciones de horarios
- **Detectar automáticamente conflictos** en horarios
- **Extraer información de PDFs** mediante OCR/PLN
- Gestionar el ciclo de vida de conflictos

### Arquitectura Target

```
FastAPI App
├── API Layer (/v0/*)
├── Service Layer (casos de uso)
├── Repository Layer (acceso datos)
├── Core Logic (conflicts + extraction)
└── Database (SQLAlchemy + SQLite/PostgreSQL)
```

### Principios de Diseño

- **Feature-sliced architecture**: Modular por dominio
- **Clean Architecture**: Core independiente del framework
- **Session-per-request**: Patrón de DB limpio
- **Type-safe**: Tipado estricto con Pydantic v2
- **Test-first**: TDD donde sea crítico

---

## Fase 1: Infraestructura Base

### 1.1 Configuración del Proyecto

**Duración estimada**: 1-2 días
**Prioridad**: CRÍTICA

#### Tareas:

- [X] **1.1.1** Crear estructura de carpetas completa según el árbol definido
- [X] **1.1.2** Configurar `requirements.txt` con todas las dependencias
- [X] **1.1.3** Configurar `config/settings.py` con pydantic-settings
- [X] **1.1.4** Crear `db/session.py` con SessionLocal y get_db()
- [X] **1.1.5** Configurar `dependencies/common.py` con inyecciones básicas
- [X] **1.1.6** Crear `main.py` con FastAPI app y health check

#### Estructura de Carpetas:

```
app/
├── catalogo/
│   ├── api/routers.py
│   ├── schemas/{programa.py, asignatura.py, mencion.py}
│   ├── services/{programa_service.py, asignatura_service.py, mencion_service.py}
│   ├── repositories/{programa_repo.py, asignatura_repo.py, mencion_repo.py}
│   └── __init__.py
├── recursos/
│   ├── api/routers.py
│   ├── schemas/{profesor.py, aula.py}
│   ├── services/{profesor_service.py, aula_service.py}
│   ├── repositories/{profesor_repo.py, aula_repo.py}
│   └── __init__.py
├── docencia/
│   ├── api/routers.py
│   ├── schemas/{grupo_docente.py, sesion.py}
│   ├── services/{grupo_service.py, sesion_service.py}
│   ├── repositories/{grupo_repo.py, sesion_repo.py}
│   └── __init__.py
├── reglas/
│   ├── api/routers.py
│   ├── schemas/restriccion.py
│   ├── services/restriccion_service.py
│   ├── repositories/restriccion_repo.py
│   └── __init__.py
├── conflictos/
│   ├── api/routers.py
│   ├── schemas/conflicto.py
│   ├── services/conflicto_service.py
│   ├── repositories/conflicto_repo.py
│   └── __init__.py
├── ingesta/
│   ├── api/routers.py
│   ├── schemas/{documento.py, import_run.py, extraccion.py}
│   ├── services/ingesta_service.py
│   ├── repositories/{documento_repo.py, import_run_repo.py, extraccion_repo.py}
│   └── __init__.py
├── core/
│   ├── conflicts/
│   │   ├── engine.py
│   │   ├── rules.py
│   │   ├── hashing.py
│   │   ├── types.py
│   │   └── __init__.py
│   ├── extraction/
│   │   ├── ocr.py
│   │   ├── parsing.py
│   │   ├── normalize.py
│   │   └── __init__.py
│   └── __init__.py
├── db/
│   ├── session.py
│   └── __init__.py
├── dependencies/
│   ├── common.py
│   └── __init__.py
├── config/
│   ├── settings.py
│   └── __init__.py
├── utils/
│   ├── pagination.py
│   ├── errors.py
│   └── __init__.py
└── main.py
```

#### Configuraciones Críticas:

**requirements.txt**:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
pytesseract==0.3.10
spacy==3.7.2
pandas==2.1.4
PyPDF2==3.0.1
pytest==7.4.3
pytest-asyncio==0.21.1
alembic==1.13.1
```

**config/settings.py** (esqueleto):

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dev.db"
  
    # API
    api_v0_prefix: str = "/v0"
    cors_origins: list[str] = ["http://localhost:3000"]
  
    # OCR/Extraction
    tesseract_cmd: Optional[str] = None
    spacy_model: str = "es_core_news_sm"
  
    # App
    debug: bool = True
    log_level: str = "INFO"
  
    class Config:
        env_file = ".env"

settings = Settings()
```

#### Criterios de Validación:

- [X] App FastAPI arranca sin errores
- [X] GET /health devuelve {"status": "ok"}
- [X] Conexión a base de datos funciona
- [X] Todos los módulos se importan correctamente

---

## Fase 2: Módulos Core

### 2.1 Core Conflicts (Motor de Detección)

**Duración estimada**: 3-4 días
**Prioridad**: CRÍTICA

#### Tareas:

- [X] **2.1.1** Definir tipos base en `core/conflicts/types.py`
- [X] **2.1.2** Implementar `core/conflicts/hashing.py` para generar hashes únicos
- [X] **2.1.3** Implementar reglas básicas en `core/conflicts/basic_rules.py`
- [X] **2.1.4** Implementar interfaz principal en `core/conflicts/engine.py`

**Nota**: La arquitectura de reglas se ha diseñado de forma modular:

- `basic_rules.py` contiene las reglas fundamentales (solapamientos, restricciones básicas)
- Futuras reglas avanzadas irán en módulos especializados (capacity_rules.py, business_rules.py, etc.)
- Esta separación permite mejor mantenibilidad y configuración granular
- **Las reglas avanzadas se implementarán en la Fase 4.1.4** (ver sección de Ampliación de Reglas)

#### core/conflicts/types.py:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, time
from enum import Enum

class TipoConflicto(str, Enum):
    SOLAPAMIENTO_PROFESOR = "solapamiento_profesor"
    SOLAPAMIENTO_AULA = "solapamiento_aula"
    VIOLACION_RESTRICCION = "violacion_restriccion"
    RECURSOS_INSUFICIENTES = "recursos_insuficientes"

class SeveridadConflicto(str, Enum):
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"

class Intervalo(BaseModel):
    """Representa un intervalo de tiempo genérico"""
    inicio: datetime
    fin: datetime
  
    def overlaps(self, other: 'Intervalo') -> bool:
        """Detecta si dos intervalos se solapan"""
        return self.inicio < other.fin and other.inicio < self.fin

class SlotSemanal(BaseModel):
    """Representa un slot semanal recurrente"""
    dia_semana: int = Field(..., ge=0, le=6)  # 0=Lunes, 6=Domingo
    hora_inicio: time
    hora_fin: time
  
    def overlaps(self, other: 'SlotSemanal') -> bool:
        """Detecta si dos slots semanales se solapan"""
        if self.dia_semana != other.dia_semana:
            return False
        return self.hora_inicio < other.hora_fin and other.hora_inicio < self.hora_fin

class ResultadoDeteccion(BaseModel):
    """Resultado de la detección de un conflicto"""
    tipo: TipoConflicto
    severidad: SeveridadConflicto
    descripcion: str
  
    # Referencias a entidades involucradas
    sesion_id: int
    sesion_2_id: Optional[int] = None
    profesor_id: Optional[int] = None
    aula_id: Optional[int] = None
    restriccion_id: Optional[int] = None
  
    # Metadatos
    hash_deteccion: str
    datos_contexto: dict = Field(default_factory=dict)

class ParametrosDeteccion(BaseModel):
    """Parámetros para configurar la detección"""
    incluir_solapamientos_profesor: bool = True
    incluir_solapamientos_aula: bool = True
    incluir_violaciones_restriccion: bool = True
    severidad_minima: SeveridadConflicto = SeveridadConflicto.BAJA
    rango_fechas: Optional[tuple[datetime, datetime]] = None
```

#### core/conflicts/engine.py (interfaz):

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from .types import ResultadoDeteccion, ParametrosDeteccion

class ConflictDetectionEngine:
    """Motor principal de detección de conflictos"""
  
    def __init__(self):
        self.rules = []  # TODO: cargar reglas
  
    def detect_conflicts_for_session(
        self,
        sesion_id: int,
        db_session: Session,
        params: Optional[ParametrosDeteccion] = None
    ) -> List[ResultadoDeteccion]:
        """
        Detecta conflictos que involucran a una sesión específica
  
        Args:
            sesion_id: ID de la sesión a analizar
            db_session: Sesión de SQLAlchemy
            params: Parámetros de configuración
  
        Returns:
            Lista de conflictos detectados
        """
        # TODO: Implementar lógica de detección
        return []
  
    def detect_conflicts_for_range(
        self,
        db_session: Session,
        params: Optional[ParametrosDeteccion] = None
    ) -> List[ResultadoDeteccion]:
        """
        Detecta conflictos en un rango completo (toda la BD o filtrado)
  
        Args:
            db_session: Sesión de SQLAlchemy
            params: Parámetros de configuración
  
        Returns:
            Lista de conflictos detectados
        """
        # TODO: Implementar lógica de detección masiva
        return []
  
    def validate_session_constraints(
        self,
        sesion_data: dict,
        db_session: Session
    ) -> List[ResultadoDeteccion]:
        """
        Valida que una sesión (nueva o modificada) no genere conflictos
  
        Args:
            sesion_data: Datos de la sesión a validar
            db_session: Sesión de SQLAlchemy
  
        Returns:
            Lista de conflictos potenciales
        """
        # TODO: Implementar validación previa
        return []

# Instancia global del motor
conflict_engine = ConflictDetectionEngine()
```

#### Criterios de Validación:

- [X] Tipos base compilar sin errores
- [X] Interfaces del engine están definidas
- [X] Hash generation funciona (aunque sea stub)
- [X] Tests unitarios básicos pasan

### 2.2 Core Extraction (OCR/PLN)

**Duración estimada**: 2-3 días
**Prioridad**: MEDIA

#### Tareas:

- [X] **2.2.1** Implementar `core/extraction/ocr.py` (stub con Tesseract)
- [ ] **2.2.2** Crear `core/extraction/parsing.py` (regex/spaCy básico)
- [ ] **2.2.3** Implementar `core/extraction/normalize.py` (a estructuras intermedias)

#### core/extraction/ocr.py:

```python
import pytesseract
from PIL import Image
import PyPDF2
from typing import Dict, Any
from pathlib import Path

class OCRExtractor:
    """Extractor de texto usando Tesseract OCR"""
  
    def __init__(self, tesseract_cmd: str = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
  
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrae texto de un PDF usando PyPDF2 + OCR como fallback
  
        Args:
            pdf_path: Ruta al archivo PDF
  
        Returns:
            Texto extraído
        """
        # TODO: Implementar extracción real
        return "TODO: Implementar OCR real"
  
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extrae texto de una imagen usando Tesseract
  
        Args:
            image_path: Ruta a la imagen
  
        Returns:
            Texto extraído
        """
        # TODO: Implementar OCR de imágenes
        return "TODO: Implementar OCR de imágenes"
  
    def extract_metadata_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrae metadatos del PDF (autor, título, fechas, etc.)
  
        Args:
            pdf_path: Ruta al archivo PDF
  
        Returns:
            Diccionario con metadatos
        """
        # TODO: Implementar extracción de metadatos
        return {"TODO": "metadatos"}
```

#### Criterios de Validación:

- [ ] Interfaces OCR definidas
- [ ] Stubs funcionales retornan valores esperados
- [ ] Dependencias (Tesseract, PyPDF2) se importan correctamente

---

## Fase 3: Módulos de Dominio

### 3.1 Módulo Catálogo (Programas, Asignaturas, Menciones)

**Duración estimada**: 4-5 días
**Prioridad**: ALTA

#### Tareas:

- [ ] **3.1.1** Implementar schemas Pydantic para Programa, Asignatura, Mencion
- [ ] **3.1.2** Crear repositories con operaciones CRUD
- [ ] **3.1.3** Implementar services con lógica de negocio
- [ ] **3.1.4** Crear routers con endpoints REST
- [ ] **3.1.5** Añadir validaciones de integridad básicas

#### catalogo/schemas/programa.py:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from backend.constants.enums import TipoPrograma

class ProgramaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: TipoPrograma
    activo: bool = True

class ProgramaCreate(ProgramaBase):
    """Schema para crear un programa"""
    pass

class ProgramaUpdate(BaseModel):
    """Schema para actualizar un programa"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    tipo: Optional[TipoPrograma] = None
    activo: Optional[bool] = None

class ProgramaOut(ProgramaBase):
    """Schema para respuesta de API"""
    id: int
  
    class Config:
        from_attributes = True

class ProgramaConMenciones(ProgramaOut):
    """Schema con menciones anidadas"""
    menciones: List['MencionOut'] = []

class ProgramaConAsignaturas(ProgramaOut):
    """Schema con asignaturas anidadas"""
    asignaturas: List['AsignaturaOut'] = []
```

#### catalogo/repositories/programa_repo.py:

```python
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from database.models import Programa, Mencion, ProgramaAsignatura
from ..schemas.programa import ProgramaCreate, ProgramaUpdate

class ProgramaRepository:
    """Repositorio para operaciones CRUD de Programa"""
  
    def list(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Programa]:
        """Lista programas con filtros y paginación"""
        query = db.query(Programa)
  
        if filters:
            if filters.get("tipo"):
                query = query.filter(Programa.tipo == filters["tipo"])
            if filters.get("activo") is not None:
                query = query.filter(Programa.activo == filters["activo"])
            if filters.get("nombre_like"):
                query = query.filter(
                    Programa.nombre.ilike(f"%{filters['nombre_like']}%")
                )
  
        return query.offset(skip).limit(limit).all()
  
    def get_by_id(self, db: Session, programa_id: int) -> Optional[Programa]:
        """Obtiene programa por ID"""
        return db.query(Programa).filter(Programa.id == programa_id).first()
  
    def get_with_menciones(self, db: Session, programa_id: int) -> Optional[Programa]:
        """Obtiene programa con menciones cargadas"""
        return db.query(Programa).options(
            selectinload(Programa.menciones)
        ).filter(Programa.id == programa_id).first()
  
    def create(self, db: Session, programa_data: ProgramaCreate) -> Programa:
        """Crea un nuevo programa"""
        programa = Programa(**programa_data.model_dump())
        db.add(programa)
        db.commit()
        db.refresh(programa)
        return programa
  
    def update(
        self,
        db: Session,
        programa_id: int,
        programa_data: ProgramaUpdate
    ) -> Optional[Programa]:
        """Actualiza un programa existente"""
        programa = self.get_by_id(db, programa_id)
        if not programa:
            return None
  
        update_data = programa_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(programa, field, value)
  
        db.commit()
        db.refresh(programa)
        return programa
  
    def delete(self, db: Session, programa_id: int) -> bool:
        """Elimina un programa (soft delete)"""
        programa = self.get_by_id(db, programa_id)
        if not programa:
            return False
  
        programa.activo = False
        db.commit()
        return True
  
    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Cuenta programas con filtros"""
        query = db.query(Programa)
  
        if filters:
            if filters.get("tipo"):
                query = query.filter(Programa.tipo == filters["tipo"])
            if filters.get("activo") is not None:
                query = query.filter(Programa.activo == filters["activo"])
  
        return query.count()

programa_repo = ProgramaRepository()
```

#### catalogo/services/programa_service.py:

```python
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..repositories.programa_repo import programa_repo
from ..schemas.programa import (
    ProgramaCreate, ProgramaUpdate, ProgramaOut, ProgramaConMenciones
)
from utils.errors import NotFoundError, ValidationError

class ProgramaService:
    """Casos de uso para gestión de programas"""
  
    def __init__(self):
        self.repo = programa_repo
  
    def list_programas(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ProgramaOut]:
        """Lista programas con paginación y filtros"""
        programas = self.repo.list(db, skip=skip, limit=limit, filters=filters)
        return [ProgramaOut.model_validate(p) for p in programas]
  
    def get_programa(self, db: Session, programa_id: int) -> ProgramaOut:
        """Obtiene un programa por ID"""
        programa = self.repo.get_by_id(db, programa_id)
        if not programa:
            raise NotFoundError(f"Programa {programa_id} no encontrado")
        return ProgramaOut.model_validate(programa)
  
    def get_programa_with_menciones(
        self, db: Session, programa_id: int
    ) -> ProgramaConMenciones:
        """Obtiene programa con menciones"""
        programa = self.repo.get_with_menciones(db, programa_id)
        if not programa:
            raise NotFoundError(f"Programa {programa_id} no encontrado")
        return ProgramaConMenciones.model_validate(programa)
  
    def create_programa(
        self, db: Session, programa_data: ProgramaCreate
    ) -> ProgramaOut:
        """Crea un nuevo programa"""
        # Validaciones de negocio
        self._validate_programa_business_rules(db, programa_data)
  
        programa = self.repo.create(db, programa_data)
        return ProgramaOut.model_validate(programa)
  
    def update_programa(
        self, db: Session, programa_id: int, programa_data: ProgramaUpdate
    ) -> ProgramaOut:
        """Actualiza un programa existente"""
        programa = self.repo.update(db, programa_id, programa_data)
        if not programa:
            raise NotFoundError(f"Programa {programa_id} no encontrado")
        return ProgramaOut.model_validate(programa)
  
    def delete_programa(self, db: Session, programa_id: int) -> bool:
        """Elimina un programa (soft delete)"""
        # TODO: Validar que no tenga asignaturas activas
        return self.repo.delete(db, programa_id)
  
    def _validate_programa_business_rules(
        self, db: Session, programa_data: ProgramaCreate
    ):
        """Valida reglas de negocio para programas"""
        # TODO: Implementar validaciones específicas
        # - No duplicar nombre+tipo
        # - Validaciones según tipo de programa
        pass

programa_service = ProgramaService()
```

#### catalogo/api/routers.py:

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from dependencies.common import get_db, pagination
from ..services.programa_service import programa_service
from ..services.asignatura_service import asignatura_service
from ..services.mencion_service import mencion_service
from ..schemas.programa import (
    ProgramaCreate, ProgramaUpdate, ProgramaOut, ProgramaConMenciones
)
from ..schemas.asignatura import AsignaturaOut
from backend.constants.enums import TipoPrograma

router = APIRouter(prefix="/v0/catalogo", tags=["catálogo"])

# ========== PROGRAMAS ==========

@router.get("/programas", response_model=List[ProgramaOut])
def list_programas(
    db: Session = Depends(get_db),
    pagination: Dict[str, int] = Depends(pagination),
    tipo: Optional[TipoPrograma] = Query(None, description="Filtrar por tipo"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado"),
    nombre_like: Optional[str] = Query(None, description="Buscar por nombre (LIKE)")
):
    """Lista todos los programas con filtros opcionales"""
    filters = {}
    if tipo:
        filters["tipo"] = tipo
    if activo is not None:
        filters["activo"] = activo
    if nombre_like:
        filters["nombre_like"] = nombre_like
  
    return programa_service.list_programas(
        db=db,
        skip=pagination["offset"],
        limit=pagination["limit"],
        filters=filters
    )

@router.get("/programas/{programa_id}", response_model=ProgramaOut)
def get_programa(programa_id: int, db: Session = Depends(get_db)):
    """Obtiene un programa específico por ID"""
    return programa_service.get_programa(db=db, programa_id=programa_id)

@router.get("/programas/{programa_id}/menciones", response_model=ProgramaConMenciones)
def get_programa_with_menciones(
    programa_id: int, db: Session = Depends(get_db)
):
    """Obtiene un programa con sus menciones"""
    return programa_service.get_programa_with_menciones(
        db=db, programa_id=programa_id
    )

@router.post("/programas", response_model=ProgramaOut, status_code=status.HTTP_201_CREATED)
def create_programa(
    programa_data: ProgramaCreate, db: Session = Depends(get_db)
):
    """Crea un nuevo programa"""
    return programa_service.create_programa(db=db, programa_data=programa_data)

@router.put("/programas/{programa_id}", response_model=ProgramaOut)
def update_programa(
    programa_id: int,
    programa_data: ProgramaUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza un programa existente"""
    return programa_service.update_programa(
        db=db, programa_id=programa_id, programa_data=programa_data
    )

@router.delete("/programas/{programa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_programa(programa_id: int, db: Session = Depends(get_db)):
    """Elimina un programa (soft delete)"""
    success = programa_service.delete_programa(db=db, programa_id=programa_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programa {programa_id} no encontrado"
        )

# TODO: Endpoints para ASIGNATURAS y MENCIONES siguiendo el mismo patrón
```

#### Criterios de Validación:

- [ ] CRUD completo funciona para Programas
- [ ] Paginación funciona correctamente
- [ ] Filtros básicos operativos
- [ ] Validaciones Pydantic funcionan
- [ ] Manejo de errores 404/400 correcto

### 3.2 Módulo Recursos (Profesores, Aulas)

**Duración estimada**: 3-4 días
**Prioridad**: ALTA

#### Tareas:

- [ ] **3.2.1** Schemas para Profesor y Aula (Create/Update/Out)
- [ ] **3.2.2** Repositories con operaciones CRUD + búsquedas especializadas
- [ ] **3.2.3** Services con validaciones específicas de recursos
- [ ] **3.2.4** Routers con endpoints REST

#### Funcionalidades Específicas:

- **Profesores**: Búsqueda por departamento, disponibilidad, asignaturas impartidas
- **Aulas**: Búsqueda por tipo, capacidad, disponibilidad en horario específico
- **Validaciones**: Email único para profesores, códigos únicos para aulas

### 3.3 Módulo Docencia (Grupos, Sesiones)

**Duración estimada**: 5-6 días
**Prioridad**: CRÍTICA (conecta con detección)

#### Tareas:

- [ ] **3.3.1** Schemas para GrupoDocente y Sesion (tipos complejos con horarios)
- [ ] **3.3.2** Repositories con queries especializadas por horarios
- [ ] **3.3.3** Services con lógica de planificación horaria
- [ ] **3.3.4** **INTEGRACIÓN**: Llamar a `core/conflicts` al crear/modificar sesiones
- [ ] **3.3.5** Routers con endpoints específicos de planificación

#### docencia/services/sesion_service.py (crítico):

```python
from core.conflicts.engine import conflict_engine
from conflictos.services.conflicto_service import conflicto_service

class SesionService:
    def create_sesion(self, db: Session, sesion_data: SesionCreate) -> SesionOut:
        """Crea sesión y detecta conflictos automáticamente"""
        # 1. Crear sesión
        sesion = self.repo.create(db, sesion_data)
  
        # 2. DETECTAR CONFLICTOS automáticamente
        conflictos = conflict_engine.detect_conflicts_for_session(
            sesion.id, db
        )
  
        # 3. Persistir conflictos encontrados
        for conflicto_data in conflictos:
            conflicto_service.create_conflicto_from_detection(
                db, conflicto_data
            )
  
        return SesionOut.model_validate(sesion)
```

### 3.4 Módulo Reglas (Restricciones)

**Duración estimada**: 2-3 días
**Prioridad**: MEDIA

### 3.5 Módulo Conflictos (Gestión)

**Duración estimada**: 3-4 días
**Prioridad**: ALTA

### 3.6 Módulo Ingesta (Documentos, OCR)

**Duración estimada**: 4-5 días
**Prioridad**: BAJA (para v1.0)

---

## Fase 4: Lógica de Negocio Crítica

### 4.1 Implementación del Motor de Conflictos

**Duración estimada**: 8-10 días
**Prioridad**: CRÍTICA

#### Tareas:

- [ ] **4.1.1** Implementar detección de solapamientos de profesores (ya implementado en basic_rules.py)
- [ ] **4.1.2** Implementar detección de solapamientos de aulas (ya implementado en basic_rules.py)
- [ ] **4.1.3** Implementar validación de restricciones (ya implementado en basic_rules.py)
- [ ] **4.1.4** **AMPLIAR**: Implementar reglas avanzadas en módulos especializados
- [ ] **4.1.5** Motor de detección masiva (toda la base de datos)
- [ ] **4.1.6** Optimizaciones de rendimiento

#### 4.1.4 Ampliación de Reglas de Detección:

Las reglas básicas implementadas en `basic_rules.py` (Fase 2.1.3) cubren los conflictos fundamentales.
En esta fase se implementarán reglas avanzadas en módulos especializados:

**Módulos de Reglas Avanzadas a Implementar**:

- **`capacity_rules.py`**: Reglas de capacidad y recursos físicos

  - CapacidadAulaInsuficienteRule
  - RecursosEquipamientoInsuficientesRule
  - ViolacionAfororMaximoRule
- **`business_rules.py`**: Reglas de negocio específicas académicas

  - RestriccionModalidadIncompatibleRule
  - ConflictoAsignaturasCorrelativasRule
  - ViolacionPoliticasHorariosRule
- **`scheduling_rules.py`**: Reglas de planificación temporal avanzada

  - ViolacionVentanasTemporalesRule
  - ConflictoDistribucionSemanalRule
  - OptimizacionUsoRecursosRule
- **`custom_rules.py`**: Reglas personalizables por institución

  - ReglasEspecificasUniversidadRule
  - ReglasTemporalesEventosEspecialesRule
  - ConfiguracionPoliticasPersonalizadasRule

#### Algoritmos Críticos:

**Detección de Solapamientos**:

```python
def detect_professor_overlaps(db: Session, sesion_id: int) -> List[ResultadoDeteccion]:
    """
    Detecta si un profesor está asignado a múltiples sesiones simultáneas
  
    Algoritmo:
    1. Obtener la sesión objetivo
    2. Obtener todos los profesores asignados a esa sesión
    3. Para cada profesor, buscar otras sesiones en el mismo horario
    4. Generar ResultadoDeteccion para cada conflicto
    """
  
def detect_room_overlaps(db: Session, sesion_id: int) -> List[ResultadoDeteccion]:
    """
    Detecta si un aula está asignada a múltiples sesiones simultáneas
    """
  
def detect_restriction_violations(db: Session, sesion_id: int) -> List[ResultadoDeteccion]:
    """
    Detecta violaciones de restricciones (profesor/aula no disponible)
    """
```

**Generación de Hash**:

```python
def build_conflict_hash(conflicto: ResultadoDeteccion) -> str:
    """
    Genera hash único para evitar duplicados
  
    Componentes del hash:
    - Tipo de conflicto
    - IDs de sesiones involucradas (ordenados)
    - ID de profesor/aula (si aplica)
    - ID de restricción (si aplica)
  
    Returns:
        SHA256 hash de 64 caracteres
    """
```

### 4.2 Implementación de Extracción OCR (Opcional v1.0)

**Duración estimada**: 6-8 días
**Prioridad**: BAJA

---

## Fase 5: Integración y Testing

### 5.1 Testing Unitario

**Duración estimada**: 4-5 días
**Prioridad**: ALTA

#### Cobertura Target:

- **Core Logic**: >90% cobertura
- **Services**: >80% cobertura
- **Repositories**: >70% cobertura
- **APIs**: Tests de integración básicos

#### tests/test_core_conflicts.py:

```python
import pytest
from core.conflicts.engine import conflict_engine
from core.conflicts.types import ResultadoDeteccion, TipoConflicto

class TestConflictDetection:
    def test_detect_professor_overlap(self, db_session, sample_sessions):
        """Test detección de solapamiento de profesores"""
        conflictos = conflict_engine.detect_conflicts_for_session(
            sesion_id=1, db_session=db_session
        )
  
        assert len(conflictos) > 0
        assert any(c.tipo == TipoConflicto.SOLAPAMIENTO_PROFESOR for c in conflictos)
  
    def test_detect_room_overlap(self, db_session, sample_sessions):
        """Test detección de solapamiento de aulas"""
        # TODO: Implementar test
        pass
  
    def test_hash_generation(self):
        """Test generación de hash únicos"""
        # TODO: Implementar test
        pass
```

### 5.2 Testing de Integración

**Duración estimada**: 2-3 días
**Prioridad**: MEDIA

### 5.3 Testing End-to-End

**Duración estimada**: 3-4 días
**Prioridad**: MEDIA

---

## Fase 6: Optimización y Deploy

### 6.1 Optimización de Rendimiento

**Duración estimada**: 3-4 días
**Prioridad**: MEDIA

#### Tareas:

- [ ] **6.1.1** Optimizar queries SQLAlchemy (índices, selectinload)
- [ ] **6.1.2** Cache en memoria para detección de conflictos
- [ ] **6.1.3** Paginación eficiente para listas grandes
- [ ] **6.1.4** Benchmarking y profiling

### 6.2 Configuración para Producción

**Duración estimada**: 2-3 días
**Prioridad**: BAJA (para v1.0)

---

## Criterios de Aceptación

### Funcionalidades Mínimas v1.0:

- [ ] ✅ **CRUD completo** para todas las entidades del modelo
- [ ] ✅ **Detección automática** de conflictos al crear/editar sesiones
- [ ] ✅ **API REST** completamente documentada (OpenAPI/Swagger)
- [ ] ✅ **Gestión de conflictos** (listar, marcar como resuelto, etc.)
- [ ] ✅ **Validaciones** de integridad y reglas de negocio
- [ ] ✅ **Manejo de errores** robusto (4xx/5xx apropados)

### Funcionalidades Opcionales v1.0:

- [ ] 🔄 **Extracción OCR** básica de PDFs
- [ ] 🔄 **Dashboard** de conflictos (estadísticas)
- [ ] 🔄 **Exportación** de reportes
- [ ] 🔄 **Logging** estructurado

### Criterios de Calidad:

- [ ] ✅ **Cobertura de tests** >70%
- [ ] ✅ **Documentación** completa de APIs
- [ ] ✅ **Type hints** en todo el código
- [ ] ✅ **Rendimiento** <500ms para operaciones CRUD
- [ ] ✅ **Rendimiento** <2s para detección de conflictos por sesión

---

## Dependencias y Herramientas

### Stack Tecnológico Confirmado:

```python
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
sqlalchemy==2.0.23
alembic==1.13.1

# Validation & Serialization
pydantic==2.5.0
pydantic-settings==2.1.0

# OCR & Processing (opcional v1.0)
pytesseract==0.3.10
spacy==3.7.2
pandas==2.1.4
PyPDF2==3.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2  # para tests de API

# Development
black==23.11.0
mypy==1.7.1
ruff==0.1.6
```

### Herramientas de Desarrollo:

- **Linter**: Ruff (más rápido que flake8)
- **Formatter**: Black
- **Type Checker**: MyPy
- **Testing**: Pytest
- **API Docs**: FastAPI auto-generated (Swagger UI)

### Base de Datos:

- **Desarrollo**: SQLite (`dev.db`)
- **Testing**: SQLite en memoria
- **Producción**: PostgreSQL (preparado pero no requerido v1.0)

---

## Timeline Estimado

| Fase                                  | Duración | Prioridad | Dependencias |
| ------------------------------------- | --------- | --------- | ------------ |
| **Fase 1**: Infraestructura     | 2 días   | CRÍTICA  | -            |
| **Fase 2**: Core Modules        | 6 días   | CRÍTICA  | Fase 1       |
| **Fase 3**: Módulos de Dominio | 20 días  | ALTA      | Fase 1, 2    |
| **Fase 4**: Lógica de Negocio  | 10 días  | CRÍTICA  | Fase 3       |
| **Fase 5**: Testing             | 9 días   | ALTA      | Fase 4       |
| **Fase 6**: Optimización       | 5 días   | MEDIA     | Fase 5       |

**Total estimado**: ~52 días de desarrollo
**Con buffer (20%)**: ~62 días
**Timeline realista**: **2.5-3 meses**

---

## Notas Finales

### Riesgos Identificados:

1. **Complejidad de detección de conflictos**: La lógica de solapamientos puede ser más compleja de lo esperado
2. **Rendimiento de consultas**: Con muchas sesiones, las queries pueden ser lentas
3. **Integración OCR**: Las herramientas de OCR pueden ser inconsistentes

### Estrategias de Mitigación:

1. **Implementar detección paso a paso**: Empezar con casos simples
2. **Optimizar desde el principio**: Usar selectinload, índices apropiados
3. **OCR como opcional**: Priorizar funcionalidad core primero

### Próximos Pasos:

1. **Validar este roadmap** con stakeholders
2. **Configurar entorno de desarrollo**
3. **Empezar con Fase 1**: Infraestructura base
4. **Iterar** basándose en feedback y pruebas

---

*Documento vivo - Actualizar según progreso y descubrimientos durante el desarrollo*
