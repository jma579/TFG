"""
Repositorio para operaciones de base de datos de Aula.

Responsabilidades:
- Acceso directo a la tabla aulas
- Queries básicas (CRUD)
- Búsquedas y filtros
- NO contiene lógica de negocio (va en service)
- Retorna modelos SQLAlchemy (Aula)

Métodos:
- get_by_id: Obtener aula por ID
- get_by_codigo: Obtener aula por código único
- get_by_nombre: Obtener aula por nombre único
- get_multi: Listar con filtros y paginación
- create: Crear nueva aula
- update: Actualizar aula existente
- delete: Eliminar aula (DELETE físico, no soft delete)
- exists_by_codigo: Verificar existencia por código
- exists_by_nombre: Verificar existencia por nombre
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database.models import Aula
from modules.recursos.schemas.aula import AulaCreate, AulaUpdate
from constants.enums import TipoAula


class AulaRepository:
    """
    Repositorio para operaciones de base de datos de Aula.
    
    Patrón Repository: Encapsula el acceso a datos y queries complejas.
    """
    
    def get_by_id(self, db: Session, id: int) -> Optional[Aula]:
        """
        Obtener aula por ID.
        
        Args:
            db: Sesión de base de datos
            id: ID único del aula
            
        Returns:
            Aula si existe, None si no
        """
        return db.query(Aula).filter(Aula.id == id).first()
    
    
    def get_by_codigo(self, db: Session, codigo: str) -> Optional[Aula]:
        """
        Obtener aula por código único.
        
        Args:
            db: Sesión de base de datos
            codigo: Código único del aula (case-insensitive)
            
        Returns:
            Aula si existe, None si no
        """
        return db.query(Aula).filter(
            func.lower(Aula.codigo) == codigo.lower()
        ).first()
    
    
    def get_by_nombre(self, db: Session, nombre: str) -> Optional[Aula]:
        """
        Obtener aula por nombre único.
        
        Args:
            db: Sesión de base de datos
            nombre: Nombre único del aula (case-insensitive)
            
        Returns:
            Aula si existe, None si no
        """
        return db.query(Aula).filter(
            func.lower(Aula.nombre) == nombre.lower()
        ).first()
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        tipo: Optional[TipoAula] = None,
        capacidad_min: Optional[int] = None,
        capacidad_max: Optional[int] = None,
        busqueda: Optional[str] = None
    ) -> Tuple[List[Aula], int]:
        """
        Listar aulas con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros a retornar
            tipo: Filtrar por tipo de aula (TipoAula enum)
            capacidad_min: Filtrar por capacidad mínima (>=)
            capacidad_max: Filtrar por capacidad máxima (<=)
            busqueda: Buscar en nombre o código (case-insensitive)
            
        Returns:
            Tupla (lista_aulas, total_sin_paginar)
            
        Ejemplo:
            >>> items, total = repo.get_multi(db, skip=0, limit=10, tipo=TipoAula.LABORATORIO)
            >>> # items: primeras 10 aulas de tipo LABORATORIO
            >>> # total: total de aulas LABORATORIO (sin paginar)
        """
        # Query base
        query = db.query(Aula)
        
        # Aplicar filtros
        if tipo is not None:
            query = query.filter(Aula.tipo == tipo)
        
        if capacidad_min is not None:
            query = query.filter(Aula.capacidad >= capacidad_min)
        
        if capacidad_max is not None:
            query = query.filter(Aula.capacidad <= capacidad_max)
        
        if busqueda is not None:
            # Buscar en nombre O código (case-insensitive)
            busqueda_lower = busqueda.lower()
            query = query.filter(
                or_(
                    func.lower(Aula.nombre).contains(busqueda_lower),
                    func.lower(Aula.codigo).contains(busqueda_lower)
                )
            )
        
        # Contar total ANTES de paginar
        total = query.count()
        
        # Ordenar por código (alfabético)
        query = query.order_by(Aula.codigo)
        
        # Aplicar paginación
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    
    def create(self, db: Session, obj_in: AulaCreate) -> Aula:
        """
        Crear nueva aula.
        
        Args:
            db: Sesión de base de datos
            obj_in: Datos del aula a crear (AulaCreate schema)
            
        Returns:
            Aula creada con ID asignado
            
        Nota:
            - No valida unicidad (debe hacerse en service layer)
            - Commit se hace en el service
        """
        # Convertir schema Pydantic a dict
        aula_data = obj_in.model_dump()
        
        # Crear instancia del modelo
        db_aula = Aula(**aula_data)
        
        # Añadir a sesión
        db.add(db_aula)
        db.flush()  # Asignar ID sin hacer commit
        db.refresh(db_aula)
        
        return db_aula
    
    
    def update(
        self,
        db: Session,
        db_obj: Aula,
        obj_in: AulaUpdate
    ) -> Aula:
        """
        Actualizar aula existente.
        
        Args:
            db: Sesión de base de datos
            db_obj: Aula existente de la DB
            obj_in: Datos a actualizar (AulaUpdate schema)
            
        Returns:
            Aula actualizada
            
        Nota:
            - Solo actualiza campos proporcionados (exclude_unset=True)
            - No valida unicidad (debe hacerse en service layer)
        """
        # Obtener datos a actualizar (solo campos proporcionados)
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Actualizar campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.flush()
        db.refresh(db_obj)
        
        return db_obj
    
    
    def delete(self, db: Session, id: int) -> Optional[Aula]:
        """
        Eliminar aula (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene campo 'activo', por lo que
        se hace DELETE físico de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID del aula a eliminar
            
        Returns:
            Aula eliminada si existía, None si no
            
        Raises:
            IntegrityError: Si hay registros relacionados (sesiones, restricciones)
        """
        aula = self.get_by_id(db, id)
        
        if aula:
            db.delete(aula)
            db.flush()
        
        return aula
    
    
    def exists_by_codigo(
        self,
        db: Session,
        codigo: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe un aula con el código dado.
        
        Args:
            db: Sesión de base de datos
            codigo: Código a verificar
            exclude_id: ID a excluir de la búsqueda (para updates)
            
        Returns:
            True si existe, False si no
            
        Ejemplo:
            >>> # Para crear: verificar que no exista
            >>> existe = repo.exists_by_codigo(db, "A101")
            >>> if existe:
            >>>     raise HTTPException(409, "Código ya existe")
            
            >>> # Para actualizar: excluir el propio ID
            >>> existe = repo.exists_by_codigo(db, "A101", exclude_id=5)
            >>> if existe:
            >>>     raise HTTPException(409, "Código ya existe en otra aula")
        """
        query = db.query(Aula).filter(
            func.lower(Aula.codigo) == codigo.lower()
        )
        
        if exclude_id is not None:
            query = query.filter(Aula.id != exclude_id)
        
        return query.first() is not None
    
    
    def exists_by_nombre(
        self,
        db: Session,
        nombre: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe un aula con el nombre dado.
        
        Args:
            db: Sesión de base de datos
            nombre: Nombre a verificar
            exclude_id: ID a excluir de la búsqueda (para updates)
            
        Returns:
            True si existe, False si no
        """
        query = db.query(Aula).filter(
            func.lower(Aula.nombre) == nombre.lower()
        )
        
        if exclude_id is not None:
            query = query.filter(Aula.id != exclude_id)
        
        return query.first() is not None


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

aula_repository = AulaRepository()
"""
Instancia singleton del repositorio de Aula.

Uso:
    from modules.recursos.repositories.aula_repo import aula_repository
    
    aula = aula_repository.get_by_id(db, 1)
"""