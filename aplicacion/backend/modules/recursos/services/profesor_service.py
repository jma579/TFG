"""
Service para lógica de negocio de Profesor.

Responsabilidades:
- Validaciones de negocio (email único, existencia)
- Manejo de excepciones HTTP (404, 409)
- Conversión de modelos SQLAlchemy a Pydantic schemas
- Orquestación entre repository y API layer
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Tuple, Optional

from database.models import Profesor
from backend.modules.recursos.schemas.profesor import (
    ProfesorCreate, ProfesorUpdate, ProfesorOut
)
from backend.modules.recursos.repositories.profesor_repo import profesor_repository


class ProfesorService:
    """
    Service para gestionar lógica de negocio de Profesor.
    
    Métodos:
    - get_by_id: Obtener profesor por ID (404 si no existe)
    - get_by_nombre: Buscar profesores por nombre/apellidos
    - get_multi: Listar profesores con filtros y paginación
    - create: Crear profesor (valida email único si se proporciona)
    - update: Actualizar profesor (valida existencia y email único)
    - delete: Soft delete profesor (404 si no existe)
    """
    
    def __init__(self):
        """Inicializar service con instancia del repository."""
        self.repository = profesor_repository
    
    
    def get_by_id(self, db: Session, id: int) -> ProfesorOut:
        """
        Obtener un profesor por su ID.
        
        Args:
            db: Sesión de base de datos
            id: ID del profesor
            
        Returns:
            ProfesorOut con los datos del profesor
            
        Raises:
            HTTPException 404: Si el profesor no existe
            
        Example:
            >>> profesor = service.get_by_id(db, 1)
            >>> print(profesor.nombre)
            "Juan"
        """
        db_obj = self.repository.get_by_id(db, id)
        
        if not db_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Profesor con id {id} no encontrado"
            )
        
        return ProfesorOut.model_validate(db_obj)
    
    
    def get_by_nombre(self, db: Session, busqueda: str) -> List[ProfesorOut]:
        """
        Buscar profesores por nombre y/o apellidos.
        
        Búsqueda case-insensitive y parcial.
        NO lanza 404 si no encuentra resultados (retorna lista vacía).
        
        Args:
            db: Sesión de base de datos
            busqueda: Texto a buscar en nombre/apellidos
            
        Returns:
            Lista de profesores que coinciden (puede ser vacía)
            
        Examples:
            >>> profesores = service.get_by_nombre(db, "Gómez")
            >>> len(profesores)
            2
            
            >>> profesores = service.get_by_nombre(db, "NoExiste")
            >>> len(profesores)
            0
        """
        db_objs = self.repository.get_by_nombre(db, busqueda)
        
        return [ProfesorOut.model_validate(obj) for obj in db_objs]
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        departamento: Optional[str] = None,
        activo: Optional[bool] = None
    ) -> Tuple[List[ProfesorOut], int]:
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
            >>> profesores, total = service.get_multi(db, skip=0, limit=20, activo=True)
            >>> print(f"Mostrando {len(profesores)} de {total} profesores")
            "Mostrando 20 de 85 profesores"
        """
        items, total = self.repository.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            departamento=departamento,
            activo=activo
        )
        
        items_out = [ProfesorOut.model_validate(item) for item in items]
        
        return items_out, total
    
    
    def create(self, db: Session, obj_in: ProfesorCreate) -> ProfesorOut:
        """
        Crear un nuevo profesor.
        
        Validaciones:
        - Si email se proporciona, debe ser único en la base de datos
        
        Args:
            db: Sesión de base de datos
            obj_in: Datos del profesor a crear
            
        Returns:
            ProfesorOut con los datos del profesor creado (incluye ID)
            
        Raises:
            HTTPException 409: Si el email ya existe
            
        Example:
            >>> data = ProfesorCreate(
            ...     nombre="Juan",
            ...     apellidos="García",
            ...     email="juan@uam.es"
            ... )
            >>> profesor = service.create(db, data)
            >>> print(profesor.id)
            1
        """
        # Validar email único si se proporciona
        if obj_in.email:
            existing = db.query(Profesor).filter(
                Profesor.email == obj_in.email
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe un profesor con el email '{obj_in.email}'"
                )
        
        # Crear profesor
        db_obj = self.repository.create(db, obj_in)
        
        return ProfesorOut.model_validate(db_obj)
    
    
    def update(self, db: Session, id: int, obj_in: ProfesorUpdate) -> ProfesorOut:
        """
        Actualizar un profesor existente.
        
        Actualización parcial: solo se modifican los campos proporcionados.
        
        Comportamiento de campos:
        - Campo no incluido en request → No se modifica
        - Campo con valor → Se actualiza
        - Campo con null → Se borra (pone a None)
        
        Validaciones:
        - Profesor debe existir
        - Si se actualiza email (incluso a null), validar unicidad
        
        Args:
            db: Sesión de base de datos
            id: ID del profesor a actualizar
            obj_in: Datos a actualizar (solo campos proporcionados)
            
        Returns:
            ProfesorOut con los datos actualizados
            
        Raises:
            HTTPException 404: Si el profesor no existe
            HTTPException 409: Si el nuevo email ya existe (en otro profesor)
            
        Examples:
            >>> # Actualizar solo departamento
            >>> update_data = ProfesorUpdate(departamento="Matemáticas")
            >>> profesor = service.update(db, 1, update_data)
            
            >>> # Borrar email (poner a null)
            >>> update_data = ProfesorUpdate(email=None)
            >>> profesor = service.update(db, 1, update_data)
            
            >>> # Actualizar email
            >>> update_data = ProfesorUpdate(email="nuevo@uam.es")
            >>> profesor = service.update(db, 1, update_data)
        """
        # 1. Validar que el profesor existe
        db_obj = self.repository.get_by_id(db, id)
        
        if not db_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Profesor con id {id} no encontrado"
            )
        
        # 2. Obtener datos a actualizar (exclude_unset=True ignora campos no enviados)
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # 3. Si se está actualizando email, validar unicidad
        if "email" in update_data:
            new_email = update_data["email"]
            
            # Solo validar si el nuevo email NO es None (null borra el email, no necesita validación)
            if new_email is not None:
                existing = db.query(Profesor).filter(
                    Profesor.email == new_email,
                    Profesor.id != id  # Excluir el propio profesor
                ).first()
                
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Ya existe otro profesor con el email '{new_email}'"
                    )
        
        # 4. Actualizar profesor
        updated = self.repository.update(db, db_obj, obj_in)
        
        return ProfesorOut.model_validate(updated)
    
    
    def delete(self, db: Session, id: int) -> None:
        """
        Soft delete de un profesor (cambiar activo=False).
        
        NO elimina físicamente el registro.
        Útil para mantener integridad referencial con sesiones/restricciones.
        
        Args:
            db: Sesión de base de datos
            id: ID del profesor a eliminar
            
        Returns:
            None (el router retornará 204 No Content)
            
        Raises:
            HTTPException 404: Si el profesor no existe
            
        Example:
            >>> service.delete(db, 1)
            >>> # Profesor con id=1 ahora tiene activo=False
        """
        db_obj = self.repository.delete(db, id)
        
        if not db_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Profesor con id {id} no encontrado"
            )
        
        # No retornar nada (204 No Content en router)


# Instancia singleton del service
profesor_service = ProfesorService()