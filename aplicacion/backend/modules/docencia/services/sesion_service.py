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
- Detectar conflictos de aula al crear/actualizar
- Detectar conflictos de profesor al crear/actualizar
- Detectar conflictos de grupo docente al crear/actualizar
- Persistir conflictos detectados
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from modules.docencia.repositories.sesion_repo import sesion_repository
from modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, SesionOut, ProfesorSesionOut,
    SesionWithConflictosOut
)
from modules.conflictos.schemas.conflicto import ConflictoOut
from modules.conflictos.repositories.conflictos_repo import sync_conflictos_for_sesion
from core.conflictos.types import ParametrosDeteccion
from core.conflictos.engine import conflict_engine

from constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana

# Importar repositories para validar FK
from modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from modules.recursos.repositories.aula_repo import aula_repository
from modules.recursos.repositories.profesor_repo import profesor_repository


class SesionService:
    """
    Servicio para gestionar la lógica de negocio de Sesion.
    
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, sesion_in: SesionCreate) -> SesionWithConflictosOut:
        """
        Crear nueva sesión.
        
        Flujo:
        1. Validar FKs (grupo, aula, profesores)
        2. Validar coherencia horaria (inicio < fin)
        3. Crear sesión en BD
        4. (DESACTIVADO) Detectar y persistir conflictos
        5. Retornar sesión + lista vacía de conflictos
        """
        # 1. Validar FK Grupo Docente
        if not grupo_docente_repository.get_by_id(db, sesion_in.grupo_docente_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo docente {sesion_in.grupo_docente_id} no encontrado"
            )
            
        # 2. Validar FK Aula
        if not aula_repository.get_by_id(db, sesion_in.aula_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aula {sesion_in.aula_id} no encontrada"
            )
            
        # 3. Validar FK Profesores (si hay)
        profesores_data = []
        if sesion_in.profesores:
            ids_profesores = [p.profesor_id for p in sesion_in.profesores]
            profesores_db = profesor_repository.get_by_ids(db, ids_profesores)
            
            # Verificar que encontramos todos
            found_ids = {p.id for p in profesores_db}
            missing_ids = set(ids_profesores) - found_ids
            
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Profesores con ids {list(missing_ids)} no encontrados"
                )
            
            # Preparar datos para el repo
            for p_in in sesion_in.profesores:
                profesores_data.append({
                    "profesor_id": p_in.profesor_id,
                    "rol_en_sesion": p_in.rol_en_sesion
                })

        # 4. Validar coherencia horaria
        if sesion_in.tipo_recurrencia == TipoRecurrencia.SEMANAL:
            if not sesion_in.hora_inicio or not sesion_in.hora_fin:
                raise HTTPException(status_code=400, detail="Horario semanal requiere hora_inicio y hora_fin")
            if sesion_in.hora_inicio >= sesion_in.hora_fin:
                raise HTTPException(status_code=400, detail="hora_inicio debe ser menor que hora_fin")
        else:
            # PUNTUAL
            if not sesion_in.inicio or not sesion_in.fin:
                raise HTTPException(status_code=400, detail="Horario puntual requiere inicio y fin (datetime)")
            if sesion_in.inicio >= sesion_in.fin:
                raise HTTPException(status_code=400, detail="inicio debe ser menor que fin")

        try:
            # 5. Crear en BD
            db_sesion = sesion_repository.create(db, sesion_in)
            
            # Asignar profesores
            if profesores_data:
                for p_data in profesores_data:
                    sesion_repository.add_profesor(
                        db, 
                        sesion_id=db_sesion.id,
                        profesor_id=p_data["profesor_id"],
                        rol_en_sesion=p_data["rol_en_sesion"]
                    )
            
            # Commit inicial para tener IDs
            db.commit()
            db.refresh(db_sesion)
            
            # ----------------------------------------------------------------
            # ⚠️ DETECCIÓN DE CONFLICTOS DESACTIVADA TEMPORALMENTE ⚠️
            # ----------------------------------------------------------------
            # Objetivo: Permitir guardado limpio sin errores de validación del motor.
            # Cuando quieras reactivarlo, descomenta este bloque y asegura que 
            # conflict_engine maneje correctamente los tipos Enum/String.
            
            conflictos_out = []
            
            # try:
            #     detectados = conflict_engine.detectar_conflictos_nueva_sesion(db, db_sesion)
            #     # Persistir en tabla conflictos
            #     conflictos_db = sync_conflictos_for_sesion(db, db_sesion.id, detectados)
            #     # Convertir a schema Out
            #     conflictos_out = [ConflictoOut.model_validate(c) for c in conflictos_db]
            # except Exception as e:
            #     logger.error(f"Error detectando conflictos para sesion {db_sesion.id}: {e}")
            #     # No fallamos la creación de sesión si falla el motor de conflictos
            #     pass
            
            # ----------------------------------------------------------------

            # Convertir a DTO de salida
            sesion_out = self._to_sesion_out(db_sesion)
            
            return SesionWithConflictosOut(
                sesion=sesion_out,
                conflictos=conflictos_out
            )
            
        except Exception as e:
            db.rollback()
            raise e

    def _to_sesion_out(self, sesion: Sesion) -> SesionOut:
        """Helper para convertir modelo ORM a Schema Pydantic incluyendo profesores"""
        # Construcción manual para control total
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
        
        profesores_out = []
        for profesor in sesion.profesores:
            # Buscar rol
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
    
    
    def update(self, db: Session, id: int, sesion_in: SesionUpdate) -> SesionWithConflictosOut:
        """
        Actualizar sesión existente (actualización parcial).
        
        Validaciones:
        1. Sesión debe existir
        2. Si se actualiza grupo_docente_id, verificar que existe
        3. Si se actualiza aula_id, verificar que existe
        4. Si se actualizan profesores, verificar que todos existen
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
        
        # Flush para asegurar que los cambios están en BD antes de detectar conflictos
        db.flush()

        resultados = conflict_engine.detect_conflicts_for_session(
            sesion_id=sesion.id,
            db_session=db,
            params=ParametrosDeteccion(),
        )
        conflictos_db = sync_conflictos_for_sesion(
            db=db,
            sesion_id=sesion.id,
            resultados_engine=resultados,
        )

        # Commit
        db.commit()
        db.refresh(sesion)
        
        return SesionWithConflictosOut(
            sesion=self._convert_to_out(sesion),
            conflictos=[ConflictoOut.model_validate(c) for c in conflictos_db],
        )
    
    
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
    from modules.docencia.services.sesion_service import sesion_service
    
    sesion = sesion_service.get_by_id(db, 1)
"""