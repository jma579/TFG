"""
Capa de servicio para la entidad Aula.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)

Validaciones:
- Unicidad de código (case-insensitive)
- Unicidad de nombre (case-insensitive)
- Existencia de aula antes de actualizar/eliminar
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.recursos.repositories.aula_repo import aula_repository
from modules.recursos.schemas.aula import (
    AulaCreate, AulaUpdate, AulaOut
)
from constants.enums import TipoAula


class AulaService:
    """
    Servicio para gestionar la lógica de negocio de Aula.
    
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, aula_in: AulaCreate) -> AulaOut:
        """
        Crear nueva aula.
        
        Validaciones:
        1. Código único (case-insensitive)
        2. Nombre único (case-insensitive)
        
        Args:
            db: Sesión de base de datos
            aula_in: Datos del aula a crear
            
        Returns:
            AulaOut con el aula creada (incluye ID)
            
        Raises:
            HTTPException 409: Si el código o nombre ya existen
            
        Ejemplo:
            >>> aula_data = AulaCreate(
            ...     nombre="Aula Magna",
            ...     codigo="MAGNA",
            ...     tipo=TipoAula.TEORICA,
            ...     capacidad=200
            ... )
            >>> aula = aula_service.create(db, aula_data)
            >>> print(aula.id)  # ID autogenerado
        """
        # Validar unicidad de código
        if aula_repository.exists_by_codigo(db, aula_in.codigo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un aula con el código '{aula_in.codigo}'"
            )
        
        # Validar unicidad de nombre
        if aula_repository.exists_by_nombre(db, aula_in.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un aula con el nombre '{aula_in.nombre}'"
            )
        
        # Crear aula
        aula = aula_repository.create(db, aula_in)
        
        # Commit
        db.commit()
        db.refresh(aula)
        
        # Convertir modelo SQLAlchemy a schema Pydantic
        return AulaOut.model_validate(aula)
    
    
    def get_by_id(self, db: Session, id: int) -> AulaOut:
        """
        Obtener aula por ID.
        
        Args:
            db: Sesión de base de datos
            id: ID del aula
            
        Returns:
            AulaOut con los datos del aula
            
        Raises:
            HTTPException 404: Si el aula no existe
        """
        aula = aula_repository.get_by_id(db, id)
        
        if not aula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula con id {id} no encontrada"
            )
        
        return AulaOut.model_validate(aula)
    
    
    def get_by_codigo(self, db: Session, codigo: str) -> AulaOut:
        """
        Obtener aula por código único.
        
        Args:
            db: Sesión de base de datos
            codigo: Código del aula
            
        Returns:
            AulaOut con los datos del aula
            
        Raises:
            HTTPException 404: Si el aula no existe
        """
        aula = aula_repository.get_by_codigo(db, codigo)
        
        if not aula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula con código '{codigo}' no encontrada"
            )
        
        return AulaOut.model_validate(aula)
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        tipo: Optional[TipoAula] = None,
        capacidad_min: Optional[int] = None,
        capacidad_max: Optional[int] = None,
        busqueda: Optional[str] = None
    ) -> Tuple[List[AulaOut], int]:
        """
        Listar aulas con filtros y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Offset para paginación
            limit: Límite de resultados
            tipo: Filtrar por tipo de aula
            capacidad_min: Filtrar por capacidad mínima
            capacidad_max: Filtrar por capacidad máxima
            busqueda: Buscar en nombre o código
            
        Returns:
            Tupla (lista_aulas_out, total)
            
        Ejemplo:
            >>> items, total = aula_service.get_multi(
            ...     db, skip=0, limit=10, tipo=TipoAula.LABORATORIO
            ... )
            >>> print(f"Encontrados {total} laboratorios, mostrando {len(items)}")
        """
        # Obtener aulas del repository
        items, total = aula_repository.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            tipo=tipo,
            capacidad_min=capacidad_min,
            capacidad_max=capacidad_max,
            busqueda=busqueda
        )
        
        # Convertir modelos a schemas Pydantic
        items_out = [AulaOut.model_validate(item) for item in items]
        
        return items_out, total
    
    
    def update(
        self,
        db: Session,
        id: int,
        aula_in: AulaUpdate
    ) -> AulaOut:
        """
        Actualizar aula existente (actualización parcial).
        
        Validaciones:
        1. Aula debe existir
        2. Si se actualiza código, verificar unicidad (excluyendo la propia aula)
        3. Si se actualiza nombre, verificar unicidad (excluyendo la propia aula)
        
        Args:
            db: Sesión de base de datos
            id: ID del aula a actualizar
            aula_in: Datos a actualizar (solo campos proporcionados)
            
        Returns:
            AulaOut con el aula actualizada
            
        Raises:
            HTTPException 404: Si el aula no existe
            HTTPException 409: Si el nuevo código/nombre ya existe en otra aula
            
        Ejemplo:
            >>> # Actualizar solo la capacidad
            >>> update_data = AulaUpdate(capacidad=150)
            >>> aula = aula_service.update(db, id=1, aula_in=update_data)
        """
        # Verificar que el aula existe
        aula = aula_repository.get_by_id(db, id)
        if not aula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula con id {id} no encontrada"
            )
        
        # Si se actualiza el código, validar unicidad
        if aula_in.codigo is not None:
            if aula_repository.exists_by_codigo(db, aula_in.codigo, exclude_id=id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe otra aula con el código '{aula_in.codigo}'"
                )
        
        # Si se actualiza el nombre, validar unicidad
        if aula_in.nombre is not None:
            if aula_repository.exists_by_nombre(db, aula_in.nombre, exclude_id=id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe otra aula con el nombre '{aula_in.nombre}'"
                )
        
        # Actualizar aula
        aula = aula_repository.update(db, aula, aula_in)
        
        # Commit
        db.commit()
        db.refresh(aula)
        
        # Convertir a schema Pydantic
        return AulaOut.model_validate(aula)
    
    
    def delete(self, db: Session, id: int) -> None:
        """
        Eliminar aula (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene soft delete.
        Se elimina físicamente de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID del aula a eliminar
            
        Returns:
            None
            
        Raises:
            HTTPException 404: Si el aula no existe
            HTTPException 409: Si hay registros relacionados (IntegrityError)
            
        Ejemplo:
            >>> aula_service.delete(db, id=1)
            >>> # El aula se elimina de la DB
        """
        # Verificar que el aula existe
        aula = aula_repository.get_by_id(db, id)
        if not aula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula con id {id} no encontrada"
            )
        
        try:
            # Eliminar aula (DELETE físico)
            aula_repository.delete(db, id)
            db.commit()
            
        except Exception as e:
            db.rollback()
            # Si hay IntegrityError (FK constraint), lanzar 409
            if "FOREIGN KEY constraint failed" in str(e) or "foreign key constraint" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"No se puede eliminar el aula con id {id} porque tiene "
                        "sesiones, restricciones o conflictos asociados"
                    )
                )
            # Otro error, re-lanzar
            raise


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

aula_service = AulaService()
"""
Instancia singleton del servicio de Aula.

Uso:
    from modules.recursos.services.aula_service import aula_service
    
    aula = aula_service.get_by_id(db, 1)
"""