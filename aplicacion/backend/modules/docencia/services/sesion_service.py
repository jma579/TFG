"""
Capa de servicio para la entidad Sesion.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)
- Gestión de relación M:N con Profesor

Validaciones:
- FK grupo_docente_id debe existir
- FK aula_id debe existir
- FK profesor_id deben existir (todos los de la lista)
- Existencia de sesión antes de actualizar/eliminar

TODO (Fase 3.5 - Motor de Conflictos):
- Detectar conflictos de aula al crear/actualizar
- Detectar conflictos de profesor al crear/actualizar
- Detectar conflictos de grupo docente al crear/actualizar
- Persistir conflictos detectados
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.modules.docencia.repositories.sesion_repo import sesion_repository
from backend.modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, SesionOut, ProfesorSesionOut
)
from backend.constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana

# Importar repositories para validar FK
from backend.modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from backend.modules.recursos.repositories.aula_repo import aula_repository
from backend.modules.recursos.repositories.profesor_repo import profesor_repository


class SesionService:
    """
    Servicio para gestionar la lógica de negocio de Sesion.
    
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, sesion_in: SesionCreate) -> SesionOut:
        """
        Crear nueva sesión con profesores asignados.
        
        Validaciones:
        1. grupo_docente_id debe existir (FK)
        2. aula_id debe existir (FK)
        3. Todos los profesor_id en la lista deben existir (FK)
        
        TODO (Fase 3.5):
        4. Detectar conflictos de aula (solapamientos)
        5. Detectar conflictos de profesores (solapamientos)
        6. Detectar conflictos de grupo docente (solapamientos)
        7. Persistir conflictos detectados
        
        Args:
            db: Sesión de base de datos
            sesion_in: Datos de la sesión a crear (incluye profesores)
            
        Returns:
            SesionOut con la sesión creada (incluye ID y profesores)
            
        Raises:
            HTTPException 404: Si grupo_docente_id, aula_id o algún profesor_id no existe
            HTTPException 409: Si hay conflictos de horarios (TODO: Fase 3.5)
        """
        # Validar que el grupo docente existe
        grupo = grupo_docente_repository.get_by_id(db, sesion_in.grupo_docente_id)
        if not grupo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente con id {sesion_in.grupo_docente_id} no encontrado"
            )
        
        # Validar que el aula existe
        aula = aula_repository.get_by_id(db, sesion_in.aula_id)
        if not aula:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula con id {sesion_in.aula_id} no encontrada"
            )
        
        # Validar que todos los profesores existen
        for prof_data in sesion_in.profesores:
            profesor = profesor_repository.get_by_id(db, prof_data.profesor_id)
            if not profesor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Profesor con id {prof_data.profesor_id} no encontrado"
                )
        
        # TODO (Fase 3.5): Detectar conflictos ANTES de crear
        # from backend.modules.conflictos.services.conflict_engine import conflict_engine
        # 
        # conflictos_aula = conflict_engine.detect_aula_conflicts(db, sesion_in)
        # conflictos_profesor = conflict_engine.detect_profesor_conflicts(db, sesion_in)
        # conflictos_grupo = conflict_engine.detect_grupo_conflicts(db, sesion_in)
        # 
        # if conflictos_aula or conflictos_profesor or conflictos_grupo:
        #     raise HTTPException(
        #         status_code=status.HTTP_409_CONFLICT,
        #         detail={
        #             "message": "Se detectaron conflictos de horarios",
        #             "conflictos_aula": conflictos_aula,
        #             "conflictos_profesor": conflictos_profesor,
        #             "conflictos_grupo": conflictos_grupo
        #         }
        #     )
        
        # Crear sesión (sin profesores, se añaden después)
        sesion = sesion_repository.create(db, sesion_in)
        
        # Asignar profesores
        profesores_data = [
            {
                'profesor_id': p.profesor_id,
                'rol_en_sesion': p.rol_en_sesion
            }
            for p in sesion_in.profesores
        ]
        
        if profesores_data:
            sesion_repository.update_profesores(db, sesion.id, profesores_data)
        
        # Commit
        db.commit()
        db.refresh(sesion)
        
        # TODO (Fase 3.5): Persistir conflictos detectados
        # if conflictos_aula or conflictos_profesor or conflictos_grupo:
        #     conflict_engine.persist_conflicts(db, sesion.id, conflictos_aula + ...)
        
        # Convertir modelo SQLAlchemy a schema Pydantic
        return self._convert_to_out(sesion)
    
    
    def get_by_id(self, db: Session, id: int) -> SesionOut:
        """
        Obtener sesión por ID.
        
        Args:
            db: Sesión de base de datos
            id: ID de la sesión
            
        Returns:
            SesionOut con los datos de la sesión (incluye profesores)
            
        Raises:
            HTTPException 404: Si la sesión no existe
        """
        sesion = sesion_repository.get_by_id(db, id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con id {id} no encontrada"
            )
        
        return self._convert_to_out(sesion)
    
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        grupo_docente_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        modalidad: Optional[ModalidadSesion] = None,
        tipo_recurrencia: Optional[TipoRecurrencia] = None,
        dia_semana: Optional[DiaSemana] = None
    ) -> Tuple[List[SesionOut], int]:
        """
        Listar sesiones con filtros y paginación.
        
        Args:
            db: Sesión de base de datos
            skip: Offset para paginación
            limit: Límite de resultados
            grupo_docente_id: Filtrar por grupo docente
            aula_id: Filtrar por aula
            modalidad: Filtrar por modalidad
            tipo_recurrencia: Filtrar por tipo de recurrencia
            dia_semana: Filtrar por día de la semana
            
        Returns:
            Tupla (lista_sesiones_out, total)
        """
        # Obtener sesiones del repository
        items, total = sesion_repository.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            grupo_docente_id=grupo_docente_id,
            aula_id=aula_id,
            modalidad=modalidad,
            tipo_recurrencia=tipo_recurrencia,
            dia_semana=dia_semana
        )
        
        # Convertir modelos a schemas Pydantic
        items_out = [self._convert_to_out(item) for item in items]
        
        return items_out, total
    
    
    def update(
        self,
        db: Session,
        id: int,
        sesion_in: SesionUpdate
    ) -> SesionOut:
        """
        Actualizar sesión existente (actualización parcial).
        
        Validaciones:
        1. Sesión debe existir
        2. Si se actualiza grupo_docente_id, verificar que existe
        3. Si se actualiza aula_id, verificar que existe
        4. Si se actualizan profesores, verificar que todos existen
        
        TODO (Fase 3.5):
        5. Detectar conflictos si cambian horarios o recursos
        6. Actualizar conflictos persistidos
        
        Args:
            db: Sesión de base de datos
            id: ID de la sesión a actualizar
            sesion_in: Datos a actualizar (solo campos proporcionados)
            
        Returns:
            SesionOut con la sesión actualizada
            
        Raises:
            HTTPException 404: Si la sesión, grupo, aula o profesor no existen
            HTTPException 409: Si hay conflictos de horarios (TODO: Fase 3.5)
        """
        # Verificar que la sesión existe
        sesion = sesion_repository.get_by_id(db, id)
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con id {id} no encontrada"
            )
        
        # Si se actualiza grupo_docente_id, validar que existe
        if sesion_in.grupo_docente_id is not None:
            grupo = grupo_docente_repository.get_by_id(db, sesion_in.grupo_docente_id)
            if not grupo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Grupo docente con id {sesion_in.grupo_docente_id} no encontrado"
                )
        
        # Si se actualiza aula_id, validar que existe
        if sesion_in.aula_id is not None:
            aula = aula_repository.get_by_id(db, sesion_in.aula_id)
            if not aula:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Aula con id {sesion_in.aula_id} no encontrada"
                )
        
        # Si se actualizan profesores, validar que todos existen
        if sesion_in.profesores is not None:
            for prof_data in sesion_in.profesores:
                profesor = profesor_repository.get_by_id(db, prof_data.profesor_id)
                if not profesor:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Profesor con id {prof_data.profesor_id} no encontrado"
                    )
        
        # TODO (Fase 3.5): Detectar conflictos si cambian horarios o recursos
        # cambio_horario = (sesion_in.tipo_recurrencia or sesion_in.dia_semana or 
        #                   sesion_in.hora_inicio or sesion_in.inicio)
        # cambio_recursos = (sesion_in.aula_id or sesion_in.profesores)
        # 
        # if cambio_horario or cambio_recursos:
        #     conflictos = conflict_engine.detect_conflicts_for_update(db, id, sesion_in)
        #     if conflictos:
        #         raise HTTPException(409, detail=conflictos)
        
        # Actualizar sesión (sin profesores)
        sesion = sesion_repository.update(db, sesion, sesion_in)
        
        # Actualizar profesores si se proporcionan
        if sesion_in.profesores is not None:
            profesores_data = [
                {
                    'profesor_id': p.profesor_id,
                    'rol_en_sesion': p.rol_en_sesion
                }
                for p in sesion_in.profesores
            ]
            sesion_repository.update_profesores(db, id, profesores_data)
        
        # Commit
        db.commit()
        db.refresh(sesion)
        
        # TODO (Fase 3.5): Actualizar conflictos persistidos
        # conflict_engine.update_conflicts_for_session(db, id)
        
        # Convertir a schema Pydantic
        return self._convert_to_out(sesion)
    
    
    def delete(self, db: Session, id: int) -> None:
        """
        Eliminar sesión (DELETE físico).
        
        IMPORTANTE: Esta entidad NO tiene soft delete.
        Se elimina físicamente de la base de datos.
        
        Args:
            db: Sesión de base de datos
            id: ID de la sesión a eliminar
            
        Returns:
            None
            
        Raises:
            HTTPException 404: Si la sesión no existe
            
        TODO (Fase 3.5):
        - Eliminar conflictos asociados a esta sesión
        """
        # Verificar que la sesión existe
        sesion = sesion_repository.get_by_id(db, id)
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con id {id} no encontrada"
            )
        
        # TODO (Fase 3.5): Eliminar conflictos asociados
        # conflict_engine.delete_conflicts_for_session(db, id)
        
        # Eliminar sesión (DELETE físico)
        # Las asignaciones profesor-sesion se eliminan automáticamente (cascade)
        sesion_repository.delete(db, id)
        db.commit()
    
    
    # ============================================================
    #  MÉTODOS AUXILIARES
    # ============================================================
    
    def _convert_to_out(self, sesion) -> SesionOut:
        """
        Convertir modelo SQLAlchemy Sesion a schema Pydantic SesionOut.
        
        Incluye conversión de profesores con sus datos básicos.
        
        Args:
            sesion: Modelo SQLAlchemy Sesion (con profesores cargados)
            
        Returns:
            SesionOut con todos los datos
        """
        # Convertir sesión base
        sesion_dict = {
            'id': sesion.id,
            'grupo_docente_id': sesion.grupo_docente_id,
            'aula_id': sesion.aula_id,
            'modalidad': sesion.modalidad,
            'tipo_recurrencia': sesion.tipo_recurrencia,
            'dia_semana': sesion.dia_semana,
            'hora_inicio': sesion.hora_inicio,
            'hora_fin': sesion.hora_fin,
            'inicio': sesion.inicio,
            'fin': sesion.fin
        }
        
        # Convertir profesores
        profesores_out = []
        for profesor in sesion.profesores:
            # Buscar la relación ProfesorSesion para obtener el rol
            profesor_sesion = next(
                (ps for ps in sesion.profesores_sesiones if ps.profesor_id == profesor.id),
                None
            )
            
            profesores_out.append(ProfesorSesionOut(
                profesor_id=profesor.id,
                rol_en_sesion=profesor_sesion.rol_en_sesion if profesor_sesion else None,
                nombre=profesor.nombre,
                apellidos=profesor.apellidos
            ))
        
        sesion_dict['profesores'] = profesores_out
        
        return SesionOut(**sesion_dict)


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

sesion_service = SesionService()
"""
Instancia singleton del servicio de Sesion.

Uso:
    from backend.modules.docencia.services.sesion_service import sesion_service
    
    sesion = sesion_service.get_by_id(db, 1)
"""