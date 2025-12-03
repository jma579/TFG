"""
Service para la entidad Asignatura.

Capa de lógica de negocio (Business Logic Layer).
Responsable de:
- Validaciones de negocio (unicidad, reglas complejas)
- Orquestación de operaciones del Repository
- Manejo de excepciones HTTP (404, 409)
- Transformación entre Schemas Pydantic y modelos ORM
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from modules.catalogo.repositories.asignatura_repo import asignatura_repository
from modules.catalogo.repositories.programa_asignatura_repo import (
    programa_asignatura_repository,
)
from modules.recursos.repositories.profesor_asignatura_repo import (
    profesor_asignatura_repository,
)

from modules.catalogo.schemas.asignatura import (
    AsignaturaCreate,
    AsignaturaUpdate,
    AsignaturaOut,
    AsignaturaList,
    AsignaturaProgramaOut,
)
from modules.recursos.schemas.profesor import ProfesorOut
from constants.enums import Periodo, ModalidadAsignatura, Idioma


class AsignaturaService:
    """
    Service para lógica de negocio de Asignatura.
    
    Patrón: Singleton (una sola instancia compartida).
    """
    
    def __init__(self):
        """Inicializar service con instancia del repositorio."""
        self.repo = asignatura_repository
        self.programa_asignatura_repo = programa_asignatura_repository
        self.profesor_asignatura_repo = profesor_asignatura_repository
    
    
    # ============================================================
    #  OPERACIONES DE LECTURA (GET)
    # ============================================================
    
    def get_asignatura(self, db: Session, asignatura_id: int) -> AsignaturaOut:
        """
        Obtener asignatura por ID.
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
        
        Returns:
            AsignaturaOut: Asignatura encontrada
        
        Raises:
            HTTPException 404: Si la asignatura no existe
        
        Example:
            >>> service.get_asignatura(db, 1)
            AsignaturaOut(id=1, codigo_plan="MAT101", nombre="Matemáticas I", ...)
        """
        asignatura = self.repo.get_by_id(db, asignatura_id)
        
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con ID {asignatura_id} no encontrada"
            )
        
        return AsignaturaOut.model_validate(asignatura)
    
    
    def get_asignatura_by_codigo(self, db: Session, codigo_plan: str) -> AsignaturaOut:
        """
        Obtener asignatura por código de plan.
        
        Args:
            db: Sesión de base de datos
            codigo_plan: Código único de la asignatura
        
        Returns:
            AsignaturaOut: Asignatura encontrada
        
        Raises:
            HTTPException 404: Si la asignatura no existe
        
        Example:
            >>> service.get_asignatura_by_codigo(db, "MAT101")
            AsignaturaOut(id=1, codigo_plan="MAT101", ...)
        """
        asignatura = self.repo.get_by_codigo(db, codigo_plan)
        
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con código '{codigo_plan}' no encontrada"
            )
        
        return AsignaturaOut.model_validate(asignatura)
    
    
    def get_asignaturas(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        periodo: Optional[Periodo] = None,
        modalidad: Optional[ModalidadAsignatura] = None,
        idioma: Optional[Idioma] = None,
        activo: Optional[bool] = None
    ) -> AsignaturaList:
        """
        Listar asignaturas con filtros opcionales y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a devolver
            periodo: Filtrar por periodo (anual, cuatrimestral_1, cuatrimestral_2)
            modalidad: Filtrar por modalidad (presencial, online, semipresencial)
            idioma: Filtrar por idioma (español, inglés, catalán)
            activo: Filtrar por estado (True=activo, False=inactivo, None=todos)
        
        Returns:
            AsignaturaList: Lista paginada de asignaturas con metadata
        
        Example:
            >>> service.get_asignaturas(db, skip=0, limit=10, periodo=Periodo.CUATRIMESTRAL_1)
            AsignaturaList(total=5, items=[...], page=1, size=10)
        """
        # Obtener asignaturas del repositorio
        asignaturas, total = self.repo.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            periodo=periodo,
            modalidad=modalidad,
            idioma=idioma,
            activo=activo
        )
        
        # Convertir modelos ORM a schemas Pydantic
        items = [AsignaturaOut.model_validate(asig) for asig in asignaturas]
        
        # Calcular número de página
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return AsignaturaList(
            total=total,
            items=items,
            page=page,
            size=limit
        )
    
    def get_asignaturas_by_programa(
        self,
        db: Session,
        programa_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> AsignaturaList:
        """
        Listar asignaturas asociadas a un programa concreto.

        Usa la tabla de relación ProgramaAsignatura y devuelve
        un listado paginado con metadatos (total, page, size).
        """
        items, total = self.repo.get_by_programa(
            db=db,
            programa_id=programa_id,
            skip=skip,
            limit=limit,
        )

        items_out = [AsignaturaOut.model_validate(item) for item in items]
        page = (skip // limit) + 1 if limit > 0 else 1

        return AsignaturaList(
            total=total,
            items=items_out,
            page=page,
            size=limit,
        )
    
    def get_programas_de_asignatura(
        self,
        db: Session,
        asignatura_id: int,
    ) -> list[AsignaturaProgramaOut]:
        """
        Obtener los programas (titulaciones) asociados a una asignatura.

        Usa la tabla intermedia ProgramaAsignatura y devuelve
        una lista de relaciones enriquecidas con los datos del programa.
        """
        # 1. Validar que la asignatura existe
        asignatura = self.repo.get_by_id(db, asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con ID {asignatura_id} no encontrada",
            )

        # 2. Obtener relaciones Programa-Asignatura con el programa cargado (joinedload)
        relaciones = self.programa_asignatura_repo.get_by_asignatura(
            db=db,
            asignatura_id=asignatura_id,
        )

        # 3. Mapear a DTO
        return [
            AsignaturaProgramaOut(
                programa=rel.programa,
                curso=rel.curso,
                tipo_asignatura=rel.tipo_asignatura,
            )
            for rel in relaciones
        ]
    
    def get_profesores_de_asignatura(
        self,
        db: Session,
        asignatura_id: int,
    ) -> list[ProfesorOut]:
        """
        Obtener el profesorado asociado a una asignatura.

        Usa la tabla intermedia ProfesorAsignatura y devuelve
        una lista de profesores (ProfesorOut).
        """
        # 1. Validar que la asignatura existe
        asignatura = self.repo.get_by_id(db, asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con ID {asignatura_id} no encontrada",
            )

        # 2. Obtener relaciones Profesor-Asignatura con el profesor cargado (joinedload)
        relaciones = self.profesor_asignatura_repo.get_by_asignatura(
            db=db,
            asignatura_id=asignatura_id,
        )

        # 3. Mapear a DTO de salida
        return [
            ProfesorOut.model_validate(rel.profesor)
            for rel in relaciones
        ]
    
    
    # ============================================================
    #  OPERACIONES DE ESCRITURA (CREATE/UPDATE/DELETE)
    # ============================================================
    
    def create_asignatura(self, db: Session, asignatura_in: AsignaturaCreate) -> AsignaturaOut:
        """
        Crear nueva asignatura.
        
        Validaciones:
        1. El código de plan debe ser único
        2. El nombre debe ser único
        
        Args:
            db: Sesión de base de datos
            asignatura_in: Datos de la asignatura a crear
        
        Returns:
            AsignaturaOut: Asignatura creada con ID asignado
        
        Raises:
            HTTPException 409: Si el código o nombre ya existen
        
        Example:
            >>> data = AsignaturaCreate(codigo_plan="MAT101", nombre="Matemáticas I", ...)
            >>> service.create_asignatura(db, data)
            AsignaturaOut(id=1, codigo_plan="MAT101", ...)
        """
        # Validación 1: Código único
        if self.repo.exists_by_codigo(db, asignatura_in.codigo_plan):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una asignatura con el código '{asignatura_in.codigo_plan}'"
            )
        
        # Validación 2: Nombre único
        if self.repo.exists_by_nombre(db, asignatura_in.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una asignatura con el nombre '{asignatura_in.nombre}'"
            )
        
        # Crear asignatura
        asignatura_data = asignatura_in.model_dump()
        asignatura = self.repo.create(db, asignatura_data)
        
        return AsignaturaOut.model_validate(asignatura)
    
    
    def update_asignatura(
        self,
        db: Session,
        asignatura_id: int,
        asignatura_in: AsignaturaUpdate
    ) -> AsignaturaOut:
        """
        Actualizar asignatura existente (actualización parcial).
        
        Validaciones:
        1. La asignatura debe existir
        2. Si se cambia el código: debe ser único (excluyendo la asignatura actual)
        3. Si se cambia el nombre: debe ser único (excluyendo la asignatura actual)
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura a actualizar
            asignatura_in: Datos a actualizar (solo campos proporcionados)
        
        Returns:
            AsignaturaOut: Asignatura actualizada
        
        Raises:
            HTTPException 404: Si la asignatura no existe
            HTTPException 409: Si el nuevo código/nombre ya existe
        
        Example:
            >>> data = AsignaturaUpdate(ects=9)
            >>> service.update_asignatura(db, 1, data)
            AsignaturaOut(id=1, ects=9, ...)
        """
        # Validación 1: Asignatura existe
        asignatura = self.repo.get_by_id(db, asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con ID {asignatura_id} no encontrada"
            )
        
        # Validación 2: Si se cambia el código, debe ser único
        if asignatura_in.codigo_plan is not None:
            if self.repo.exists_by_codigo(
                db,
                asignatura_in.codigo_plan,
                exclude_id=asignatura_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una asignatura con el código '{asignatura_in.codigo_plan}'"
                )
        
        # Validación 3: Si se cambia el nombre, debe ser único
        if asignatura_in.nombre is not None:
            if self.repo.exists_by_nombre(
                db,
                asignatura_in.nombre,
                exclude_id=asignatura_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una asignatura con el nombre '{asignatura_in.nombre}'"
                )
        
        # Actualizar asignatura (solo campos no-None)
        update_data = asignatura_in.model_dump(exclude_unset=True)
        updated_asignatura = self.repo.update(db, asignatura_id, update_data)
        
        return AsignaturaOut.model_validate(updated_asignatura)
    
    
    def delete_asignatura(self, db: Session, asignatura_id: int) -> dict:
        """
        Eliminar asignatura (soft delete: marcar como inactivo).
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura a eliminar
        
        Returns:
            dict: Mensaje de confirmación
        
        Raises:
            HTTPException 404: Si la asignatura no existe
        
        Example:
            >>> service.delete_asignatura(db, 1)
            {"message": "Asignatura 'MAT101 - Matemáticas I' desactivada correctamente"}
        """
        # Validar que existe
        asignatura = self.repo.get_by_id(db, asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con ID {asignatura_id} no encontrada"
            )
        
        # Soft delete
        deleted = self.repo.delete(db, asignatura_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al desactivar la asignatura"
            )
        
        return {
            "message": f"Asignatura '{asignatura.codigo_plan} - {asignatura.nombre}' desactivada correctamente"
        }


# ============================================================
#  SINGLETON: Instancia única del service
# ============================================================

asignatura_service = AsignaturaService()