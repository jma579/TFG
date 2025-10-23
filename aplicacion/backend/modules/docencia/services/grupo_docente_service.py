"""
Capa de servicio para la entidad GrupoDocente.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)

Validaciones:
- FK asignatura_id debe existir
- Unicidad compuesta (asignatura_id, codigo) case-insensitive
- Existencia de grupo antes de actualizar/eliminar
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from backend.modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate, GrupoDocenteUpdate, GrupoDocenteOut
)
from backend.constants.enums import TipoGrupoDocente

# Importar repository de asignatura para validar FK
from backend.modules.catalogo.repositories.asignatura_repo import asignatura_repository


class GrupoDocenteService:
    """
    Servicio para gestionar la lógica de negocio de GrupoDocente.
    
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, grupo_in: GrupoDocenteCreate) -> GrupoDocenteOut:
        """
        Crear nuevo grupo docente.
        
        Validaciones:
        1. asignatura_id debe existir (FK)
        2. (asignatura_id, codigo) debe ser único (case-insensitive)
        
        Args:
            db: Sesión de base de datos
            grupo_in: Datos del grupo a crear
            
        Returns:
            GrupoDocenteOut con el grupo creado (incluye ID)
            
        Raises:
            HTTPException 404: Si la asignatura no existe
            HTTPException 409: Si el código ya existe para esa asignatura
            
        Ejemplo:
            >>> grupo_data = GrupoDocenteCreate(
            ...     asignatura_id=42,
            ...     codigo="T1",
            ...     tipo=TipoGrupoDocente.TEORIA,
            ...     curso=3,
            ...     turno="mañana"
            ... )
            >>> grupo = grupo_service.create(db, grupo_data)
        """
        # Validar que la asignatura existe
        asignatura = asignatura_repository.get_by_id(db, grupo_in.asignatura_id)
        if not asignatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asignatura con id {grupo_in.asignatura_id} no encontrada"
            )
        
        # Validar unicidad compuesta (asignatura_id, codigo)
        if grupo_docente_repository.exists_by_asignatura_codigo(
            db, grupo_in.asignatura_id, grupo_in.codigo
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ya existe un grupo con código '{grupo_in.codigo}' "
                    f"para la asignatura con id {grupo_in.asignatura_id}"
                )
            )
        
        # Crear grupo
        grupo = grupo_docente_repository.create(db, grupo_in)
        
        # Commit
        db.commit()
        db.refresh(grupo)
        
        # Convertir modelo SQLAlchemy a schema Pydantic
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_by_id(self, db: Session, id: int) -> GrupoDocenteOut:
        """
        Obtener grupo docente por ID.
        
        Args:
            db: Sesión de base de datos
            id: ID del grupo
            
        Returns:
            GrupoDocenteOut con los datos del grupo
            
        Raises:
            HTTPException 404: Si el grupo no existe
        """
        grupo = grupo_docente_repository.get_by_id(db, id)
        
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_by_asignatura_codigo(
        self,
        db: Session,
        asignatura_id: int,
        codigo: str
    ) -> GrupoDocenteOut:
        """
        Obtener grupo por constraint único (asignatura_id, codigo).
        
        Args:
            db: Sesión de base de datos
            asignatura_id: ID de la asignatura
            codigo: Código del grupo
            
        Returns:
            GrupoDocenteOut con los datos del grupo
            
        Raises:
            HTTPException 404: Si el grupo no existe
        """
        grupo = grupo_docente_repository.get_by_asignatura_codigo(
            db, asignatura_id, codigo
        )
        
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Grupo con código '{codigo}' no encontrado "
                    f"para la asignatura con id {asignatura_id}"
                )
            )
        
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        asignatura_id: Optional[int] = None,
        tipo: Optional[TipoGrupoDocente] = None,
        curso: Optional[int] = None,
        turno: Optional[str] = None
    ) -> Tuple[List[GrupoDocenteOut], int]:
        """
        Listar grupos docentes con filtros y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Offset para paginación
            limit: Límite de resultados
            asignatura_id: Filtrar por asignatura
            tipo: Filtrar por tipo de grupo
            curso: Filtrar por curso académico
            turno: Filtrar por turno
            
        Returns:
            Tupla (lista_grupos_out, total)
            
        Ejemplo:
            >>> items, total = grupo_service.get_multi(
            ...     db, skip=0, limit=10,
            ...     asignatura_id=42,
            ...     tipo=TipoGrupoDocente.TEORIA
            ... )
        """
        # Obtener grupos del repository
        items, total = grupo_docente_repository.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            asignatura_id=asignatura_id,
            tipo=tipo,
            curso=curso,
            turno=turno
        )
        
        # Convertir modelos a schemas Pydantic
        items_out = [GrupoDocenteOut.model_validate(item) for item in items]
        
        return items_out, total
    
    
    def update(
        self,
        db: Session,
        id: int,
        grupo_in: GrupoDocenteUpdate
    ) -> GrupoDocenteOut:
        """
        Actualizar grupo docente existente (actualización parcial).
        
        Validaciones:
        1. Grupo debe existir
        2. Si se actualiza asignatura_id, verificar que existe
        3. Si se actualiza asignatura_id O codigo, validar unicidad compuesta
        
        Args:
            db: Sesión de base de datos
            id: ID del grupo a actualizar
            grupo_in: Datos a actualizar (solo campos proporcionados)
            
        Returns:
            GrupoDocenteOut con el grupo actualizado
            
        Raises:
            HTTPException 404: Si el grupo o la nueva asignatura no existen
            HTTPException 409: Si la nueva combinación (asignatura_id, codigo) ya existe
            
        Ejemplo:
            >>> # Actualizar solo el turno
            >>> update_data = GrupoDocenteUpdate(turno="tarde")
            >>> grupo = grupo_service.update(db, id=1, grupo_in=update_data)
        """
        # Verificar que el grupo existe
        grupo = grupo_docente_repository.get_by_id(db, id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        
        # Si se actualiza asignatura_id, validar que existe
        if grupo_in.asignatura_id is not None:
            asignatura = asignatura_repository.get_by_id(db, grupo_in.asignatura_id)
            if not asignatura:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Asignatura con id {grupo_in.asignatura_id} no encontrada"
                )
        
        # Determinar asignatura_id y codigo finales para validar unicidad
        final_asignatura_id = (
            grupo_in.asignatura_id if grupo_in.asignatura_id is not None
            else grupo.asignatura_id
        )
        final_codigo = (
            grupo_in.codigo if grupo_in.codigo is not None
            else grupo.codigo
        )
        
        # Si se cambia asignatura_id O codigo, validar unicidad compuesta
        cambio_asignatura = (
            grupo_in.asignatura_id is not None and
            grupo_in.asignatura_id != grupo.asignatura_id
        )
        cambio_codigo = (
            grupo_in.codigo is not None and
            grupo_in.codigo.lower() != grupo.codigo.lower()
        )
        
        if cambio_asignatura or cambio_codigo:
            if grupo_docente_repository.exists_by_asignatura_codigo(
                db, final_asignatura_id, final_codigo, exclude_id=id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Ya existe otro grupo con código '{final_codigo}' "
                        f"para la asignatura con id {final_asignatura_id}"
                    )
                )
        
        # Actualizar grupo
        grupo = grupo_docente_repository.update(db, grupo, grupo_in)
        
        # Commit
        db.commit()
        db.refresh(grupo)
        
        # Convertir a schema Pydantic
        return GrupoDocenteOut.model_validate(grupo)
    
    
    def delete(self, db: Session, id: int) -> None:
        """
        Eliminar grupo docente (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene soft delete.
        Se elimina físicamente de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID del grupo a eliminar
            
        Returns:
            None
            
        Raises:
            HTTPException 404: Si el grupo no existe
            HTTPException 409: Si hay sesiones asociadas (IntegrityError)
            
        Ejemplo:
            >>> grupo_service.delete(db, id=1)
            >>> # El grupo se elimina de la DB
        """
        # Verificar que el grupo existe
        grupo = grupo_docente_repository.get_by_id(db, id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {id} no encontrado"
            )
        
        try:
            # Eliminar grupo (DELETE físico)
            grupo_docente_repository.delete(db, id)
            db.commit()
            
        except Exception as e:
            db.rollback()
            # Si hay IntegrityError (FK constraint con sesiones), lanzar 409
            if "FOREIGN KEY constraint failed" in str(e) or "foreign key constraint" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"No se puede eliminar el grupo con id {id} porque tiene "
                        "sesiones asociadas"
                    )
                )
            # Otro error, re-lanzar
            raise


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

grupo_docente_service = GrupoDocenteService()
"""
Instancia singleton del servicio de GrupoDocente.

Uso:
    from backend.modules.docencia.services.grupo_docente_service import grupo_docente_service
    
    grupo = grupo_docente_service.get_by_id(db, 1)
"""