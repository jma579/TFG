"""
Service para la entidad Mencion.

Capa de lógica de negocio (Business Logic Layer).
Responsable de:
- Validaciones de negocio (existencia de FK, unicidad compuesta)
- Orquestación de operaciones del Repository
- Manejo de excepciones HTTP (404, 409)
- Transformación entre Schemas Pydantic y modelos ORM
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.modules.catalogo.repositories.mencion_repo import mencion_repository
from backend.modules.catalogo.repositories.programa_repo import programa_repository
from backend.modules.catalogo.schemas.mencion import (
    MencionCreate,
    MencionUpdate,
    MencionOut,
    MencionList
)


class MencionService:
    """
    Service para lógica de negocio de Mencion.
    
    Patrón: Singleton (una sola instancia compartida).
    """
    
    def __init__(self):
        """Inicializar service con instancias de repositorios."""
        self.repo = mencion_repository
        self.programa_repo = programa_repository
    
    
    # ============================================================
    #  OPERACIONES DE LECTURA (GET)
    # ============================================================
    
    def get_mencion(self, db: Session, mencion_id: int) -> MencionOut:
        """
        Obtener mención por ID.
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención
        
        Returns:
            MencionOut: Mención encontrada
        
        Raises:
            HTTPException 404: Si la mención no existe
        
        Example:
            >>> service.get_mencion(db, 1)
            MencionOut(id=1, programa_id=1, nombre="Ingeniería del Software", ...)
        """
        mencion = self.repo.get_by_id(db, mencion_id)
        
        if not mencion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        
        return MencionOut.model_validate(mencion)
    
    
    def get_menciones(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        programa_id: Optional[int] = None,
        activo: Optional[bool] = None
    ) -> MencionList:
        """
        Listar menciones con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a devolver
            programa_id: Filtrar por programa (None = todos)
            activo: Filtrar por estado (True=activo, False=inactivo, None=todos)
        
        Returns:
            MencionList: Lista paginada de menciones con metadata
        
        Example:
            >>> service.get_menciones(db, skip=0, limit=10, programa_id=1)
            MencionList(total=5, items=[...], page=1, size=10)
        """
        # Obtener menciones del repositorio
        menciones, total = self.repo.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            programa_id=programa_id,
            activo=activo
        )
        
        # Convertir modelos ORM a schemas Pydantic
        items = [MencionOut.model_validate(m) for m in menciones]
        
        # Calcular número de página
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return MencionList(
            total=total,
            items=items,
            page=page,
            size=limit
        )
    
    
    # ============================================================
    #  OPERACIONES DE ESCRITURA (CREATE/UPDATE/DELETE)
    # ============================================================
    
    def create_mencion(self, db: Session, mencion_in: MencionCreate) -> MencionOut:
        """
        Crear nueva mención.
        
        Validaciones:
        1. El programa debe existir
        2. La combinación (programa_id, nombre) debe ser única
        
        Args:
            db: Sesión de base de datos
            mencion_in: Datos de la mención a crear
        
        Returns:
            MencionOut: Mención creada con ID asignado
        
        Raises:
            HTTPException 404: Si el programa no existe
            HTTPException 409: Si ya existe mención con ese nombre en el programa
        
        Example:
            >>> data = MencionCreate(programa_id=1, nombre="IA", activo=True)
            >>> service.create_mencion(db, data)
            MencionOut(id=1, programa_id=1, nombre="IA", ...)
        """
        # Validación 1: El programa debe existir
        programa = self.programa_repo.get_by_id(db, mencion_in.programa_id)
        if not programa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Programa con ID {mencion_in.programa_id} no encontrado"
            )
        
        # Validación 2: Unicidad (programa_id, nombre)
        if self.repo.exists_by_programa_nombre(db, mencion_in.programa_id, mencion_in.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una mención con el nombre '{mencion_in.nombre}' en el programa '{programa.nombre}'"
            )
        
        # Crear mención
        mencion_data = mencion_in.model_dump()
        mencion = self.repo.create(db, mencion_data)
        
        return MencionOut.model_validate(mencion)
    
    
    def update_mencion(
        self,
        db: Session,
        mencion_id: int,
        mencion_in: MencionUpdate
    ) -> MencionOut:
        """
        Actualizar mención existente (actualización parcial).
        
        Validaciones:
        1. La mención debe existir
        2. Si se cambia el programa: el programa debe existir
        3. Si se cambia programa o nombre: la combinación debe ser única
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención a actualizar
            mencion_in: Datos a actualizar (solo campos proporcionados)
        
        Returns:
            MencionOut: Mención actualizada
        
        Raises:
            HTTPException 404: Si la mención o el programa no existen
            HTTPException 409: Si la nueva combinación (programa, nombre) ya existe
        
        Example:
            >>> data = MencionUpdate(nombre="Ingeniería del Software Avanzada")
            >>> service.update_mencion(db, 1, data)
            MencionOut(id=1, nombre="Ingeniería del Software Avanzada", ...)
        """
        # Validación 1: La mención debe existir
        mencion = self.repo.get_by_id(db, mencion_id)
        if not mencion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        
        # Validación 2: Si se cambia el programa, validar que existe
        if mencion_in.programa_id is not None and mencion_in.programa_id != mencion.programa_id:
            programa = self.programa_repo.get_by_id(db, mencion_in.programa_id)
            if not programa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Programa con ID {mencion_in.programa_id} no encontrado"
                )
        
        # Validación 3: Si cambia programa o nombre, validar unicidad
        # Usar valores nuevos si se proporcionan, si no mantener los actuales
        programa_id = mencion_in.programa_id if mencion_in.programa_id is not None else mencion.programa_id
        nombre = mencion_in.nombre if mencion_in.nombre is not None else mencion.nombre
        
        # Validar unicidad (excluyendo la mención actual)
        if self.repo.exists_by_programa_nombre(
            db,
            programa_id,
            nombre,
            exclude_id=mencion_id
        ):
            programa = self.programa_repo.get_by_id(db, programa_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una mención con el nombre '{nombre}' en el programa '{programa.nombre}'"
            )
        
        # Actualizar mención (solo campos no-None)
        update_data = mencion_in.model_dump(exclude_unset=True)
        updated_mencion = self.repo.update(db, mencion_id, update_data)
        
        return MencionOut.model_validate(updated_mencion)
    
    
    def delete_mencion(self, db: Session, mencion_id: int) -> dict:
        """
        Eliminar mención (soft delete: marcar como inactivo).
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención a eliminar
        
        Returns:
            dict: Mensaje de confirmación
        
        Raises:
            HTTPException 404: Si la mención no existe
        
        Example:
            >>> service.delete_mencion(db, 1)
            {"message": "Mención 'Ingeniería del Software' desactivada correctamente"}
        """
        # Validar que existe
        mencion = self.repo.get_by_id(db, mencion_id)
        if not mencion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mención con ID {mencion_id} no encontrada"
            )
        
        # Soft delete
        deleted = self.repo.delete(db, mencion_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al desactivar la mención"
            )
        
        return {
            "message": f"Mención '{mencion.nombre}' desactivada correctamente"
        }


# ============================================================
#  SINGLETON: Instancia única del service
# ============================================================

mencion_service = MencionService()