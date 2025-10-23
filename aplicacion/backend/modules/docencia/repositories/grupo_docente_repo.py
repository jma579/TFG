"""
Repositorio para operaciones de base de datos de GrupoDocente.

Responsabilidades:
- Acceso directo a la tabla grupos_docentes
- Queries básicas (CRUD)
- Búsquedas y filtros (por asignatura, tipo, curso)
- NO contiene lógica de negocio (va en service)
- Retorna modelos SQLAlchemy (GrupoDocente)

Métodos:
- get_by_id: Obtener grupo por ID
- get_by_asignatura_codigo: Obtener por constraint único (asignatura_id, codigo)
- get_multi: Listar con filtros y paginación
- create: Crear nuevo grupo
- update: Actualizar grupo existente
- delete: Eliminar grupo (DELETE físico, no soft delete)
- exists_by_asignatura_codigo: Verificar existencia por constraint único
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import GrupoDocente
from backend.modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate
)
from backend.constants.enums import TipoGrupoDocente


class GrupoDocenteRepository:
    """
    Repositorio para operaciones de base de datos de GrupoDocente.
    
    Patrón Repository: Encapsula el acceso a datos y queries complejas.
    """
    
    def get_by_id(self, db: Session, id: int) -> Optional[GrupoDocente]:
        """
        Obtener grupo docente por ID.
        
        Args:
            db: Sesión de base de datos
            id: ID único del grupo
            
        Returns:
            GrupoDocente si existe, None si no
        """
        return db.query(GrupoDocente).filter(GrupoDocente.id == id).first()
    
    
    def get_by_asignatura_codigo(
        self,
        db: Session,
        asignatura_id: int,
        codigo: str
    ) -> Optional[GrupoDocente]:
        """
        Obtener grupo por constraint único (asignatura_id, codigo).
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            codigo: Código del grupo (case-insensitive)
            
        Returns:
            GrupoDocente si existe, None si no
            
        Ejemplo:
            >>> grupo = repo.get_by_asignatura_codigo(db, asignatura_id=42, codigo="T1")
        """
        return db.query(GrupoDocente).filter(
            GrupoDocente.asignatura_id == asignatura_id,
            func.lower(GrupoDocente.codigo) == codigo.lower()
        ).first()
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        asignatura_id: Optional[int] = None,
        tipo: Optional[TipoGrupoDocente] = None,
        curso: Optional[int] = None,
        turno: Optional[str] = None
    ) -> Tuple[List[GrupoDocente], int]:
        """
        Listar grupos docentes con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros a retornar
            asignatura_id: Filtrar por asignatura específica
            tipo: Filtrar por tipo de grupo (TipoGrupoDocente enum)
            curso: Filtrar por curso académico (1, 2, 3, etc.)
            turno: Filtrar por turno (case-insensitive, búsqueda parcial)
            
        Returns:
            Tupla (lista_grupos, total_sin_paginar)
            
        Ejemplo:
            >>> items, total = repo.get_multi(
            ...     db, skip=0, limit=10,
            ...     asignatura_id=42,
            ...     tipo=TipoGrupoDocente.TEORIA
            ... )
        """
        # Query base
        query = db.query(GrupoDocente)
        
        # Aplicar filtros
        if asignatura_id is not None:
            query = query.filter(GrupoDocente.asignatura_id == asignatura_id)
        
        if tipo is not None:
            query = query.filter(GrupoDocente.tipo == tipo)
        
        if curso is not None:
            query = query.filter(GrupoDocente.curso == curso)
        
        if turno is not None:
            # Búsqueda case-insensitive y parcial
            query = query.filter(
                func.lower(GrupoDocente.turno).contains(turno.lower())
            )
        
        # Contar total ANTES de paginar
        total = query.count()
        
        # Ordenar por asignatura_id, luego por codigo
        query = query.order_by(
            GrupoDocente.asignatura_id,
            GrupoDocente.codigo
        )
        
        # Aplicar paginación
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    
    def create(self, db: Session, obj_in: GrupoDocenteCreate) -> GrupoDocente:
        """
        Crear nuevo grupo docente.
        
        Args:
            db: Sesión de base de datos
            obj_in: Datos del grupo a crear (GrupoDocenteCreate schema)
            
        Returns:
            GrupoDocente creado con ID asignado
            
        Nota:
            - No valida unicidad ni FK (debe hacerse en service layer)
            - Commit se hace en el service
        """
        # Convertir schema Pydantic a dict
        grupo_data = obj_in.model_dump()
        
        # Crear instancia del modelo
        db_grupo = GrupoDocente(**grupo_data)
        
        # Añadir a sesión
        db.add(db_grupo)
        db.flush()  # Asignar ID sin hacer commit
        db.refresh(db_grupo)
        
        return db_grupo
    
    
    def update(
        self,
        db: Session,
        db_obj: GrupoDocente,
        obj_in: GrupoDocenteUpdate
    ) -> GrupoDocente:
        """
        Actualizar grupo docente existente.
        
        Args:
            db: Sesión de base de datos
            db_obj: GrupoDocente existente de la DB
            obj_in: Datos a actualizar (GrupoDocenteUpdate schema)
            
        Returns:
            GrupoDocente actualizado
            
        Nota:
            - Solo actualiza campos proporcionados (exclude_unset=True)
            - No valida unicidad ni FK (debe hacerse en service layer)
        """
        # Obtener datos a actualizar (solo campos proporcionados)
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.flush()
        db.refresh(db_obj)
        
        return db_obj
    
    
    def delete(self, db: Session, id: int) -> Optional[GrupoDocente]:
        """
        Eliminar grupo docente (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene campo 'activo', por lo que
        se hace DELETE físico de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID del grupo a eliminar
            
        Returns:
            GrupoDocente eliminado si existía, None si no
            
        Raises:
            IntegrityError: Si hay sesiones asociadas (FK constraint)
        """
        grupo = self.get_by_id(db, id)
        
        if grupo:
            db.delete(grupo)
            db.flush()
        
        return grupo
    
    
    def exists_by_asignatura_codigo(
        self,
        db: Session,
        asignatura_id: int,
        codigo: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe un grupo con la combinación (asignatura_id, codigo).
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            codigo: Código del grupo (case-insensitive)
            exclude_id: ID a excluir de la búsqueda (para updates)
            
        Returns:
            True si existe, False si no
            
        Ejemplo:
            >>> # Para crear: verificar que no exista
            >>> existe = repo.exists_by_asignatura_codigo(db, 42, "T1")
            >>> if existe:
            >>>     raise HTTPException(409, "Ya existe grupo T1 en esa asignatura")
            
            >>> # Para actualizar: excluir el propio ID
            >>> existe = repo.exists_by_asignatura_codigo(db, 42, "T1", exclude_id=5)
            >>> if existe:
            >>>     raise HTTPException(409, "Código duplicado en esa asignatura")
        """
        query = db.query(GrupoDocente).filter(
            GrupoDocente.asignatura_id == asignatura_id,
            func.lower(GrupoDocente.codigo) == codigo.lower()
        )
        
        if exclude_id is not None:
            query = query.filter(GrupoDocente.id != exclude_id)
        
        return query.first() is not None


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

grupo_docente_repository = GrupoDocenteRepository()
"""
Instancia singleton del repositorio de GrupoDocente.

Uso:
    from backend.modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
    
    grupo = grupo_docente_repository.get_by_id(db, 1)
"""