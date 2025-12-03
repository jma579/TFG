"""
Repository para operaciones de base de datos de Profesor.

Proporciona métodos CRUD y consultas específicas para la entidad Profesor.
Sigue el patrón repository: separación entre lógica de acceso a datos y lógica de negocio.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Tuple

from database.models import Profesor
from modules.recursos.schemas.profesor import ProfesorCreate, ProfesorUpdate


class ProfesorRepository:
    """
    Repository para gestionar operaciones de base de datos de Profesor.
    
    Métodos:
    - get_by_id: Obtener profesor por ID
    - get_by_nombre: Buscar profesores por nombre/apellidos
    - get_multi: Listar profesores con filtros y paginación
    - create: Crear nuevo profesor
    - update: Actualizar profesor existente
    - delete: Soft delete de profesor
    """
    
    
    def get_by_id(self, db: Session, id: int) -> Optional[Profesor]:
        """
        Obtener un profesor por su ID.
        
        Args:
            db: Sesión de base de datos
            id: ID del profesor
            
        Returns:
            Profesor si existe, None si no existe
            
        Example:
            >>> profesor = repo.get_by_id(db, 1)
            >>> print(profesor.nombre)
            "Juan"
        """
        return db.query(Profesor).filter(Profesor.id == id).first()
    
    
    def get_by_nombre(self, db: Session, busqueda: str) -> List[Profesor]:
        """
        Buscar profesores por nombre y/o apellidos (case-insensitive, búsqueda parcial).
        
        Busca en ambos órdenes: "nombre apellidos" y "apellidos nombre".
        Útil para búsquedas flexibles donde el usuario puede escribir en cualquier orden.
        
        Args:
            db: Sesión de base de datos
            busqueda: Texto a buscar (parcial, case-insensitive)
            
        Returns:
            Lista de profesores que coinciden (ordenados por apellidos, nombre)
            
        Examples:
            >>> # Profesores: Juan Gómez, Kike Gómez, Juan Arroyo
            >>> repo.get_by_nombre(db, "Gómez")
            [Juan Gómez, Kike Gómez]
            
            >>> repo.get_by_nombre(db, "Juan")
            [Juan Arroyo, Juan Gómez]
            
            >>> repo.get_by_nombre(db, "Juan Gómez")
            [Juan Gómez]
            
            >>> repo.get_by_nombre(db, "Kike")
            [Kike Gómez]
        """
        # Normalizar búsqueda: lowercase + LIKE con wildcards
        busqueda_lower = f"%{busqueda.lower()}%"
        
        return db.query(Profesor).filter(
            or_(
                # Buscar en "nombre apellidos"
                func.lower(
                    func.concat(Profesor.nombre, ' ', Profesor.apellidos)
                ).like(busqueda_lower),
                
                # Buscar en "apellidos nombre"
                func.lower(
                    func.concat(Profesor.apellidos, ' ', Profesor.nombre)
                ).like(busqueda_lower)
            )
        ).order_by(
            Profesor.apellidos,
            Profesor.nombre
        ).all()


    def get_by_nombre_apellidos(
        self,
        db: Session,
        nombre: str,
        apellidos: str
    ) -> Optional[Profesor]:
        """
        Buscar profesor por nombre y apellidos exactos.
        
        Args:
            db: Sesión de base de datos
            nombre: Nombre del profesor
            apellidos: Apellidos del profesor
            
        Returns:
            Profesor si existe, None si no existe
            
        Note:
            - Búsqueda case-insensitive (no distingue mayúsculas/minúsculas)
            - Normaliza espacios extra (trim)
            - Útil para detectar duplicados al extraer fichas
            
        Example:
            >>> # Buscar con capitalización diferente
            >>> profesor = profesor_repository.get_by_nombre_apellidos(
            ...     db, 
            ...     nombre="juan", 
            ...     apellidos="PÉREZ GARCÍA"
            ... )
            >>> # Encontrará "Juan Pérez García" si existe
            >>> if profesor:
            ...     print(f"Profesor encontrado: ID {profesor.id}")
        """
        from sqlalchemy import func
        
        # Normalizar búsqueda (minúsculas, sin espacios extra)
        nombre_norm = nombre.strip().lower()
        apellidos_norm = apellidos.strip().lower()
        
        return db.query(Profesor)\
            .filter(
                func.lower(func.trim(Profesor.nombre)) == nombre_norm,
                func.lower(func.trim(Profesor.apellidos)) == apellidos_norm
            )\
            .first()

    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        departamento: Optional[str] = None,
        activo: Optional[bool] = None
    ) -> Tuple[List[Profesor], int]:
        """
        Listar profesores con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (offset)
            limit: Número máximo de registros a retornar
            departamento: Filtrar por departamento exacto (opcional)
            activo: Filtrar por estado activo/inactivo (opcional)
            
        Returns:
            Tupla (lista_profesores, total_sin_paginar)
            
        Examples:
            >>> # Obtener primeros 20 profesores activos
            >>> profesores, total = repo.get_multi(db, skip=0, limit=20, activo=True)
            
            >>> # Obtener profesores de Matemáticas (página 2)
            >>> profesores, total = repo.get_multi(
            ...     db, skip=20, limit=20, departamento="Matemáticas"
            ... )
            
            >>> # Obtener todos los profesores inactivos
            >>> profesores, total = repo.get_multi(db, activo=False)
        """
        # Query base
        query = db.query(Profesor)
        
        # Aplicar filtros opcionales
        if departamento is not None:
            query = query.filter(Profesor.departamento == departamento)
        
        if activo is not None:
            query = query.filter(Profesor.activo == activo)
        
        # Ordenar por apellidos + nombre
        query = query.order_by(Profesor.apellidos, Profesor.nombre)
        
        # Contar total ANTES de aplicar paginación
        total = query.count()
        
        # Aplicar paginación
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    
    def create(self, db: Session, obj_in: ProfesorCreate) -> Profesor:
        """
        Crear un nuevo profesor.
        
        Args:
            db: Sesión de base de datos
            obj_in: Datos del profesor a crear (schema Pydantic)
            
        Returns:
            Profesor creado (modelo SQLAlchemy con ID generado)
            
        Example:
            >>> from schemas.profesor import ProfesorCreate
            >>> data = ProfesorCreate(
            ...     nombre="Juan",
            ...     apellidos="García López",
            ...     email="juan.garcia@uam.es",
            ...     departamento="Matemáticas"
            ... )
            >>> profesor = repo.create(db, data)
            >>> print(profesor.id)
            1
        """
        # Convertir schema Pydantic a dict
        db_obj = Profesor(**obj_in.model_dump())
        
        # Añadir a la sesión
        db.add(db_obj)
        
        # Hacer commit y refrescar para obtener ID
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    
    
    def update(
        self, 
        db: Session, 
        db_obj: Profesor, 
        obj_in: ProfesorUpdate
    ) -> Profesor:
        """
        Actualizar un profesor existente.
        
        Solo actualiza los campos proporcionados (update parcial).
        Los campos con valor None no se modifican.
        
        Args:
            db: Sesión de base de datos
            db_obj: Profesor existente (modelo SQLAlchemy)
            obj_in: Datos a actualizar (schema Pydantic)
            
        Returns:
            Profesor actualizado
            
        Example:
            >>> # Actualizar solo email y departamento
            >>> profesor = repo.get_by_id(db, 1)
            >>> update_data = ProfesorUpdate(
            ...     email="nuevo.email@uam.es",
            ...     departamento="Ingeniería Informática"
            ... )
            >>> profesor_actualizado = repo.update(db, profesor, update_data)
        """
        # Convertir schema a dict, excluyendo campos None
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Actualizar solo los campos proporcionados
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        # Commit y refrescar
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    
    
    def delete(self, db: Session, id: int) -> Optional[Profesor]:
        """
        Soft delete de un profesor (cambiar activo=False).
        
        NO elimina físicamente el registro de la base de datos.
        Solo marca el profesor como inactivo para mantener integridad referencial.
        
        Args:
            db: Sesión de base de datos
            id: ID del profesor a eliminar
            
        Returns:
            Profesor eliminado (con activo=False) si existía, None si no existe
            
        Example:
            >>> profesor = repo.delete(db, 1)
            >>> print(profesor.activo)
            False
        """
        # Obtener profesor
        db_obj = self.get_by_id(db, id)
        
        if db_obj is None:
            return None
        
        # Soft delete: cambiar activo a False
        db_obj.activo = False
        
        # Commit y refrescar
        db.commit()
        db.refresh(db_obj)
        
        return db_obj


# Instancia singleton del repository
profesor_repository = ProfesorRepository()