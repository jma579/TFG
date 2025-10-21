"""
Repository para la entidad Mencion.

Capa de acceso a datos (Data Access Layer).
Responsable de todas las operaciones de base de datos.

Patrón: Singleton (una sola instancia compartida)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional

from database.models import Mencion


class MencionRepository:
    """
    Repository para operaciones CRUD de Mencion.
    
    Gestiona:
    - Consultas a base de datos
    - Filtrado y paginación
    - Validaciones de existencia
    - Soft delete
    
    NO gestiona:
    - Lógica de negocio (eso va en Service)
    - Excepciones HTTP (eso va en Service)
    """
    
    
    # ============================================================
    #  MÉTODOS DE LECTURA (SELECT)
    # ============================================================
    
    def get_by_id(self, db: Session, mencion_id: int) -> Optional[Mencion]:
        """
        Obtener mención por ID.
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención
        
        Returns:
            Mencion si existe, None si no
        
        Example:
            >>> repo.get_by_id(db, 1)
            <Mencion id=1 nombre="Ingeniería del Software">
        """
        return db.query(Mencion).filter(Mencion.id == mencion_id).first()
    
    
    def get_by_programa_nombre(
        self,
        db: Session,
        programa_id: int,
        nombre: str
    ) -> Optional[Mencion]:
        """
        Buscar mención por programa + nombre (constraint de unicidad).
        
        Útil para:
        - Validar duplicados antes de crear
        - Buscar mención específica de un programa
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            nombre: Nombre de la mención (normalizado)
        
        Returns:
            Mencion si existe, None si no
        
        Example:
            >>> repo.get_by_programa_nombre(db, 1, "Ingeniería del Software")
            <Mencion id=5 programa_id=1 nombre="Ingeniería del Software">
        """
        return db.query(Mencion).filter(
            and_(
                Mencion.programa_id == programa_id,
                Mencion.nombre == nombre
            )
        ).first()
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        programa_id: Optional[int] = None,
        activo: Optional[bool] = None
    ) -> tuple[list[Mencion], int]:
        """
        Listar menciones con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a devolver
            programa_id: Filtrar por programa (None = todos)
            activo: Filtrar por estado (True/False/None)
        
        Returns:
            Tupla (lista de menciones, total de registros)
        
        Example:
            >>> menciones, total = repo.get_multi(db, skip=0, limit=10, programa_id=1)
            >>> print(f"Encontradas {total} menciones del programa 1")
        """
        # Query base
        query = db.query(Mencion)
        
        # Aplicar filtros opcionales
        if programa_id is not None:
            query = query.filter(Mencion.programa_id == programa_id)
        
        if activo is not None:
            query = query.filter(Mencion.activo == activo)
        
        # Obtener total antes de paginar
        total = query.count()
        
        # Ordenar por programa y nombre
        query = query.order_by(Mencion.programa_id.asc(), Mencion.nombre.asc())
        
        # Aplicar paginación
        menciones = query.offset(skip).limit(limit).all()
        
        return menciones, total
    
    
    # ============================================================
    #  MÉTODOS DE ESCRITURA (INSERT/UPDATE/DELETE)
    # ============================================================
    
    def create(self, db: Session, mencion_data: dict) -> Mencion:
        """
        Crear nueva mención.
        
        Args:
            db: Sesión de base de datos
            mencion_data: Diccionario con datos de la mención
        
        Returns:
            Mencion creada con ID asignado
        
        Example:
            >>> data = {"programa_id": 1, "nombre": "IA", "activo": True}
            >>> mencion = repo.create(db, data)
            >>> print(mencion.id)  # 1
        """
        mencion = Mencion(**mencion_data)
        db.add(mencion)
        db.commit()
        db.refresh(mencion)
        return mencion
    
    
    def update(
        self,
        db: Session,
        mencion_id: int,
        mencion_data: dict
    ) -> Optional[Mencion]:
        """
        Actualizar mención existente.
        
        Solo actualiza los campos proporcionados en mencion_data.
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención a actualizar
            mencion_data: Diccionario con campos a actualizar
        
        Returns:
            Mencion actualizada si existe, None si no
        
        Example:
            >>> data = {"nombre": "Ingeniería del Software Avanzada"}
            >>> mencion = repo.update(db, 1, data)
        """
        mencion = self.get_by_id(db, mencion_id)
        
        if not mencion:
            return None
        
        # Actualizar solo campos proporcionados
        for field, value in mencion_data.items():
            setattr(mencion, field, value)
        
        db.commit()
        db.refresh(mencion)
        return mencion
    
    
    def delete(self, db: Session, mencion_id: int) -> bool:
        """
        Soft delete: marcar mención como inactiva.
        
        NO elimina el registro de la base de datos.
        Solo cambia activo a False.
        
        Args:
            db: Sesión de base de datos
            mencion_id: ID de la mención a desactivar
        
        Returns:
            True si se desactivó, False si no existe
        
        Example:
            >>> success = repo.delete(db, 1)
            >>> print(success)  # True
        """
        mencion = self.get_by_id(db, mencion_id)
        
        if not mencion:
            return False
        
        mencion.activo = False
        db.commit()
        return True
    
    
    # ============================================================
    #  MÉTODOS DE VALIDACIÓN (EXISTS)
    # ============================================================
    
    def exists_by_programa_nombre(
        self,
        db: Session,
        programa_id: int,
        nombre: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe mención con ese programa + nombre.
        
        Útil para validar unicidad antes de crear/actualizar.
        
        Args:
            db: Sesión de base de datos
            programa_id: ID del programa
            nombre: Nombre de la mención
            exclude_id: ID de mención a excluir (para updates)
        
        Returns:
            True si existe, False si no
        
        Example (crear):
            >>> if repo.exists_by_programa_nombre(db, 1, "IA"):
            >>>     raise HTTPException(409, "Ya existe esa mención")
        
        Example (update):
            >>> # Permitir mantener el mismo nombre en la misma mención
            >>> if repo.exists_by_programa_nombre(db, 1, "IA", exclude_id=5):
            >>>     raise HTTPException(409, "Ya existe esa mención")
        """
        query = db.query(Mencion).filter(
            and_(
                Mencion.programa_id == programa_id,
                Mencion.nombre == nombre
            )
        )
        
        # Excluir la mención actual en updates
        if exclude_id is not None:
            query = query.filter(Mencion.id != exclude_id)
        
        return db.query(query.exists()).scalar()


# ============================================================
#  SINGLETON: Instancia única del repository
# ============================================================

mencion_repository = MencionRepository()