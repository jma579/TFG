"""
Repository para la entidad Asignatura.

Capa de acceso a datos (Data Access Layer).
Responsable de todas las operaciones de base de datos relacionadas con Asignaturas.

Patrón Singleton: Se exporta una única instancia (asignatura_repository)
que se comparte en toda la aplicación.

Responsabilidades:
- Ejecutar queries SQL a través de SQLAlchemy ORM
- Devolver modelos ORM (Asignatura) o None/listas vacías
- NO contiene lógica de negocio (eso va en Service)
- NO lanza excepciones HTTP (eso va en Service)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Tuple

from database.models import Asignatura, ProgramaAsignatura
from constants.enums import Periodo, ModalidadAsignatura, Idioma


class AsignaturaRepository:
    """
    Repository para operaciones CRUD de Asignatura.
    
    Métodos disponibles:
    - get_by_id: Buscar por ID
    - get_by_codigo: Buscar por código único
    - get_multi: Listar con filtros y paginación
    - create: Crear nueva asignatura
    - update: Actualizar asignatura (parcial)
    - delete: Soft delete (marcar como inactivo)
    - exists_by_codigo: Validar unicidad de código
    - exists_by_nombre: Validar unicidad de nombre
    """
    
    # ============================================================
    #  LECTURA (SELECT)
    # ============================================================
    
    def get_by_id(
        self,
        db: Session,
        asignatura_id: int
    ) -> Optional[Asignatura]:
        """
        Buscar asignatura por ID.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura a buscar
            
        Returns:
            Asignatura si existe, None si no existe
            
        Example:
            >>> asignatura = asignatura_repository.get_by_id(db, 1)
            >>> if asignatura:
            >>>     print(asignatura.nombre)
        """
        return db.query(Asignatura).filter(
            Asignatura.id == asignatura_id
        ).first()
    
    
    def get_by_codigo(
        self,
        db: Session,
        codigo_plan: str
    ) -> Optional[Asignatura]:
        """
        Buscar asignatura por código único.
        
        Útil para:
        - Importación de datos (buscar por código externo)
        - Búsquedas por código en lugar de ID
        - Validación de duplicados
        
        Args:
            db: Sesión de base de datos
            codigo_plan: Código único de la asignatura
            
        Returns:
            Asignatura si existe, None si no existe
            
        Example:
            >>> asignatura = asignatura_repository.get_by_codigo(db, "MAT101")
            >>> if asignatura:
            >>>     print(f"{asignatura.codigo_plan}: {asignatura.nombre}")
        """
        return db.query(Asignatura).filter(
            Asignatura.codigo_plan == codigo_plan
        ).first()
    
    def get_by_programa(
        self,
        db: Session,
        programa_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Asignatura], int]:
        """
        Obtener asignaturas asociadas a un programa concreto.

        Retorna (items, total) para poder construir listados paginados.
        """
        query = (
            db.query(Asignatura)
            .join(
                ProgramaAsignatura,
                ProgramaAsignatura.asignatura_id == Asignatura.id,
            )
            .filter(ProgramaAsignatura.programa_id == programa_id)
        )

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return items, total
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        periodo: Optional[Periodo] = None,
        modalidad: Optional[ModalidadAsignatura] = None,
        idioma: Optional[Idioma] = None,
        activo: Optional[bool] = None
    ) -> tuple[list[Asignatura], int]:
        """
        Listar asignaturas con filtros opcionales y paginación.
        
        Filtros disponibles:
        - periodo: Filtrar por periodo (anual, cuatrimestral_1, cuatrimestral_2)
        - modalidad: Filtrar por modalidad (presencial, online, semipresencial)
        - idioma: Filtrar por idioma (español, inglés, catalán, etc.)
        - activo: Filtrar por estado (True=activas, False=inactivas, None=todas)
        
        Ordenamiento: Por código de asignatura (ascendente)
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a devolver
            periodo: Filtro opcional por periodo
            modalidad: Filtro opcional por modalidad
            idioma: Filtro opcional por idioma
            activo: Filtro opcional por estado
            
        Returns:
            Tupla (lista_asignaturas, total_registros)
            
        Example:
            >>> # Todas las asignaturas activas del primer cuatrimestre
            >>> asignaturas, total = asignatura_repository.get_multi(
            ...     db,
            ...     periodo=Periodo.PRIMER_CUATRIMESTRE,
            ...     activo=True,
            ...     skip=0,
            ...     limit=10
            ... )
            >>> print(f"Encontradas {total} asignaturas, mostrando {len(asignaturas)}")
        """
        # Query base
        query = db.query(Asignatura)
        
        # Aplicar filtros opcionales
        if periodo is not None:
            query = query.filter(Asignatura.periodo == periodo)
        
        if modalidad is not None:
            query = query.filter(Asignatura.modalidad == modalidad)
        
        if idioma is not None:
            query = query.filter(Asignatura.idioma == idioma)
        
        if activo is not None:
            query = query.filter(Asignatura.activo == activo)
        
        # Contar total (antes de paginación)
        total = query.count()
        
        # Ordenar por código (ascendente, secuencial)
        query = query.order_by(Asignatura.codigo_plan.asc())
        
        # Paginación
        asignaturas = query.offset(skip).limit(limit).all()
        
        return asignaturas, total
    
    
    # ============================================================
    #  ESCRITURA (INSERT/UPDATE/DELETE)
    # ============================================================
    
    def create(
        self,
        db: Session,
        asignatura_data: dict
    ) -> Asignatura:
        """
        Crear una nueva asignatura.
        
        IMPORTANTE: Este método NO valida unicidad de código/nombre.
        La validación de negocio debe hacerse en el Service.
        
        Args:
            db: Sesión de base de datos
            asignatura_data: Diccionario con los datos de la asignatura
                           (debe coincidir con campos del modelo)
            
        Returns:
            Asignatura creada con ID autogenerado
            
        Example:
            >>> data = {
            ...     "codigo_plan": "MAT101",
            ...     "nombre": "Matemáticas I",
            ...     "periodo": Periodo.PRIMER_CUATRIMESTRE,
            ...     "ects": 6,
            ...     "modalidad": ModalidadAsignatura.PRESENCIAL,
            ...     "idioma": Idioma.ESPAÑOL,
            ...     "english_friendly": False,
            ...     "activo": True
            ... }
            >>> asignatura = asignatura_repository.create(db, data)
            >>> print(f"Creada asignatura ID={asignatura.id}")
        """
        db_asignatura = Asignatura(**asignatura_data)
        db.add(db_asignatura)
        db.commit()
        db.refresh(db_asignatura)
        return db_asignatura
    
    
    def update(
        self,
        db: Session,
        asignatura_id: int,
        asignatura_data: dict
    ) -> Optional[Asignatura]:
        """
        Actualizar una asignatura existente (update parcial).
        
        Solo actualiza los campos proporcionados en asignatura_data.
        Los campos no incluidos permanecen sin cambios.
        
        IMPORTANTE: Este método NO valida unicidad de código/nombre.
        La validación de negocio debe hacerse en el Service.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura a actualizar
            asignatura_data: Diccionario con campos a actualizar
                           (solo incluir campos que cambian)
            
        Returns:
            Asignatura actualizada si existe, None si no existe
            
        Example:
            >>> # Actualizar solo nombre y ECTS
            >>> data = {"nombre": "Matemáticas Avanzadas I", "ects": 9}
            >>> asignatura = asignatura_repository.update(db, 1, data)
            >>> if asignatura:
            >>>     print(f"Actualizada: {asignatura.nombre}, {asignatura.ects} ECTS")
        """
        db_asignatura = self.get_by_id(db, asignatura_id)
        
        if not db_asignatura:
            return None
        
        # Actualizar solo campos proporcionados
        for field, value in asignatura_data.items():
            setattr(db_asignatura, field, value)
        
        db.commit()
        db.refresh(db_asignatura)
        return db_asignatura
    
    
    def delete(
        self,
        db: Session,
        asignatura_id: int
    ) -> bool:
        """
        Eliminar asignatura (soft delete).
        
        No elimina el registro de la base de datos,
        solo marca el campo 'activo' como False.
        
        Ventajas del soft delete:
        - Preserva integridad referencial
        - Permite auditoría histórica
        - Se puede reactivar fácilmente
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura a eliminar
            
        Returns:
            True si se eliminó correctamente,
            False si no existe la asignatura
            
        Example:
            >>> success = asignatura_repository.delete(db, 1)
            >>> if success:
            >>>     print("Asignatura eliminada (marcada como inactiva)")
        """
        db_asignatura = self.get_by_id(db, asignatura_id)
        
        if not db_asignatura:
            return False
        
        # Soft delete: marcar como inactivo
        db_asignatura.activo = False
        db.commit()
        return True
    
    
    # ============================================================
    #  VALIDACIÓN (EXISTS)
    # ============================================================
    
    def exists_by_codigo(
        self,
        db: Session,
        codigo_plan: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe una asignatura con el código dado.
        
        Útil para validar unicidad antes de crear/actualizar.
        
        Args:
            db: Sesión de base de datos
            codigo_plan: Código a verificar
            exclude_id: ID de asignatura a excluir de la búsqueda
                       (útil en updates para no comparar consigo mismo)
            
        Returns:
            True si existe otra asignatura con ese código,
            False si no existe
            
        Example:
            >>> # Al crear (no excluir ningún ID)
            >>> if asignatura_repository.exists_by_codigo(db, "MAT101"):
            >>>     print("Error: Código ya existe")
            
            >>> # Al actualizar (excluir ID actual)
            >>> if asignatura_repository.exists_by_codigo(db, "MAT101", exclude_id=5):
            >>>     print("Error: Código ya usado por otra asignatura")
        """
        query = db.query(Asignatura).filter(
            Asignatura.codigo_plan == codigo_plan
        )
        
        # Excluir ID si se proporciona (para updates)
        if exclude_id is not None:
            query = query.filter(Asignatura.id != exclude_id)
        
        return db.query(query.exists()).scalar()
    
    
    def exists_by_nombre(
        self,
        db: Session,
        nombre: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Verificar si existe una asignatura con el nombre dado.
        
        Útil para validar unicidad antes de crear/actualizar.
        
        Args:
            db: Sesión de base de datos
            nombre: Nombre a verificar
            exclude_id: ID de asignatura a excluir de la búsqueda
                       (útil en updates para no comparar consigo mismo)
            
        Returns:
            True si existe otra asignatura con ese nombre,
            False si no existe
            
        Example:
            >>> # Al crear (no excluir ningún ID)
            >>> if asignatura_repository.exists_by_nombre(db, "Matemáticas I"):
            >>>     print("Error: Nombre ya existe")
            
            >>> # Al actualizar (excluir ID actual)
            >>> if asignatura_repository.exists_by_nombre(db, "Matemáticas I", exclude_id=5):
            >>>     print("Error: Nombre ya usado por otra asignatura")
        """
        query = db.query(Asignatura).filter(
            Asignatura.nombre == nombre
        )
        
        # Excluir ID si se proporciona (para updates)
        if exclude_id is not None:
            query = query.filter(Asignatura.id != exclude_id)
        
        return db.query(query.exists()).scalar()


# ============================================================
#  SINGLETON: Instancia única compartida
# ============================================================

asignatura_repository = AsignaturaRepository()
"""
Instancia singleton del repository.

Usar esta instancia en toda la aplicación:
    from modules.catalogo.repositories.asignatura_repo import asignatura_repository
    
    asignatura = asignatura_repository.get_by_id(db, 1)
"""
