"""
Capa de servicio para la entidad Sesion.

Responsabilidades:
- Lógica de negocio y validaciones
- Orquestación entre repository y schemas
- Manejo de transacciones (commit/rollback)
- Conversión modelo SQLAlchemy → Pydantic
- Manejo de excepciones HTTP (404, 409)
- Gestión de relación M:N con Profesor
- Integración con Motor de Conflictos (Detección y Persistencia)
"""

import logging
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

# Repositorios
from modules.docencia.repositories.sesion_repo import sesion_repository
from modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from modules.recursos.repositories.aula_repo import aula_repository
from modules.recursos.repositories.profesor_repo import profesor_repository

# Schemas
from modules.docencia.schemas.sesion import (
    SesionCreate, SesionUpdate, SesionOut, ProfesorSesionOut,
    SesionWithConflictosOut, SesionBatchRequest
)

# Conflictos (Core & Module)
from modules.conflictos.schemas.conflicto import ConflictoOut
from modules.conflictos.repositories.conflictos_repo import conflictos_repository
from core.conflictos.engine import conflict_engine
from core.conflictos.types import ParametrosDeteccion

# Enums y Modelos
from constants.enums import ModalidadSesion, TipoRecurrencia, DiaSemana, EstadoConflicto
from database.models import Sesion

logger = logging.getLogger(__name__)


class SesionService:
    """
    Servicio para gestionar la lógica de negocio de Sesion.
    Patrón Service: Encapsula lógica de negocio y orquesta repositories.
    """
    
    def create(self, db: Session, sesion_in: SesionCreate, detect_conflicts: bool = True) -> SesionWithConflictosOut:
        """
        Crea una nueva sesión y sus relaciones.
        
        Args:
            db: Sesión de base de datos
            sesion_in: Datos de la sesión
            detect_conflicts: Si es True, ejecuta el motor de conflictos inmediatamente.
                              Si es False, guarda sin validar (útil para cargas masivas).
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
            
        # 3. Validar FK Profesores
        profesores_data = []
        if sesion_in.profesores:
            ids_profesores = [p.profesor_id for p in sesion_in.profesores]
            profesores_db = profesor_repository.get_by_ids(db, ids_profesores)
            
            found_ids = {p.id for p in profesores_db}
            missing_ids = set(ids_profesores) - found_ids
            
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Profesores con ids {list(missing_ids)} no encontrados"
                )
            
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
            
            # FLUSH CRÍTICO: Genera ID y persiste relaciones para que el Engine las lea
            db.flush()
            
            # ----------------------------------------------------------------
            # 🛡️ HOOK DE DETECCIÓN DE CONFLICTOS
            # ----------------------------------------------------------------
            conflictos_out = []
            if detect_conflicts:
                try:
                    # 1. Detectar choques usando el motor
                    resultados = conflict_engine.detect_conflicts_for_session(
                        sesion_id=db_sesion.id,
                        db=db
                    )
                    # 2. Sincronizar (guardar/borrar) conflictos en BD
                    conflictos_db = conflictos_repository.sync_conflictos_for_sesion(
                        db, db_sesion.id, resultados
                    )
                    db.flush()
                    for c in conflictos_db:
                        if not c.creado_en:
                            c.creado_en = datetime.now()
                    # 3. Convertir a Schema para devolver
                    conflictos_out = [ConflictoOut.model_validate(c) for c in conflictos_db]
                    
                except Exception as e:
                    # No bloqueamos la creación si falla el motor, pero logueamos el error
                    # logger.error(...) podría ir aquí
                    print(f"[WARNING] Fallo en detección de conflictos para sesión {db_sesion.id}: {e}")

            # 6. Commit Final
            db.commit()
            db.refresh(db_sesion)
            
            return SesionWithConflictosOut(
                sesion=self._to_sesion_out(db_sesion),
                conflictos=conflictos_out
            )
            
        except Exception as e:
            db.rollback()
            raise e

    def update(self, db: Session, id: int, sesion_in: SesionUpdate) -> SesionWithConflictosOut:
        """
        Actualizar sesión existente.
        
        Flujo:
        1. Validar existencia y FKs opcionales.
        2. Actualizar datos en BD (flush).
        3. Recalcular conflictos (Wipe & Replace).
        4. Commit final.
        """
        # Verificar que la sesión existe
        sesion = sesion_repository.get_by_id(db, id)
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con id {id} no encontrada"
            )
        
        # Validar FKs si vienen en el update
        if sesion_in.grupo_docente_id is not None:
            if not grupo_docente_repository.get_by_id(db, sesion_in.grupo_docente_id):
                raise HTTPException(status_code=404, detail=f"Grupo {sesion_in.grupo_docente_id} no encontrado")
        
        if sesion_in.aula_id is not None:
            if not aula_repository.get_by_id(db, sesion_in.aula_id):
                raise HTTPException(status_code=404, detail=f"Aula {sesion_in.aula_id} no encontrada")
        
        if sesion_in.profesores is not None:
            for prof_data in sesion_in.profesores:
                if not profesor_repository.get_by_id(db, prof_data.profesor_id):
                    raise HTTPException(status_code=404, detail=f"Profesor {prof_data.profesor_id} no encontrado")
        
        # Actualizar campos básicos
        sesion = sesion_repository.update(db, sesion, sesion_in)
        
        # Actualizar profesores (reemplazo completo)
        if sesion_in.profesores is not None:
            profesores_data = [
                {'profesor_id': p.profesor_id, 'rol_en_sesion': p.rol_en_sesion}
                for p in sesion_in.profesores
            ]
            sesion_repository.update_profesores(db, id, profesores_data)
        
        # FLUSH antes de recalcular
        db.flush()

        # ----------------------------------------------------------------
        # 🛡️ RECALCULO DE CONFLICTOS
        # ----------------------------------------------------------------
        conflictos_out = []
        try:
            # 1. Detectar
            resultados = conflict_engine.detect_conflicts_for_session(
                sesion_id=sesion.id,
                db=db
            )
            
            # 2. Sincronizar (Wipe & Replace)
            # Si el usuario corrigió el horario, sync borrará los conflictos viejos automáticamente.
            conflictos_db = conflictos_repository.sync_conflictos_for_sesion(
                db, sesion.id, resultados
            )
            db.flush()
            for c in conflictos_db:
                        if not c.creado_en:
                            c.creado_en = datetime.now()
            conflictos_out = [ConflictoOut.model_validate(c) for c in conflictos_db]
            
        except Exception as e:
            logger.error(f"[ERROR] Motor conflictos falló en UPDATE sesion {sesion.id}: {e}")

        # Commit
        db.commit()
        db.refresh(sesion)
        
        return SesionWithConflictosOut(
            sesion=self._to_sesion_out(sesion),
            conflictos=conflictos_out,
        )
    
    def simulate_batch(self, db: Session, payload: SesionBatchRequest) -> List[ConflictoOut]:
        """
        Simula un lote de cambios (Crear/Actualizar/Borrar) y devuelve 
        TODOS los conflictos resultantes del horario completo.
        
        NO persiste cambios (hace ROLLBACK).
        """
        # Mapa para rastrear IDs reales generados -> IDs temporales del frontend
        id_map = {}

        db.begin_nested()
        try:
            # 1. Eliminar
            for id_sesion in payload.deleted:
                if sesion_repository.get_by_id(db, id_sesion):
                    sesion_repository.delete(db, id_sesion)

            # 2. Actualizar
            for item in payload.updated:
                db_sesion = sesion_repository.get_by_id(db, item.id)
                if db_sesion:
                    update_data = item.model_dump(exclude={'id'}, exclude_unset=True)
                    if update_data:
                        schema_update = SesionUpdate(**update_data)
                        sesion_repository.update(db, db_sesion, schema_update)
                        if schema_update.profesores is not None:
                             p_data = [{'profesor_id': p.profesor_id, 'rol_en_sesion': p.rol_en_sesion} for p in schema_update.profesores]
                             sesion_repository.update_profesores(db, item.id, p_data)

            # 3. Crear
            for create_item in payload.created:
                new_sesion = sesion_repository.create(db, create_item)
                if create_item.profesores:
                    for p in create_item.profesores:
                        sesion_repository.add_profesor(db, new_sesion.id, p.profesor_id, p.rol_en_sesion)
                if create_item.temp_id is not None:
                    id_map[new_sesion.id] = create_item.temp_id

            db.flush() 

            # 4. Detectar conflictos GLOBALES
            resultados = conflict_engine.detect_conflicts_for_range(db)
            
            # 5. Convertir a Schema y ajustar IDs
            conflictos_out = []
            
            # --- CORRECCIÓN AQUI: Usamos enumerate para generar IDs falsos ---
            for i, res in enumerate(resultados):
                
                # Reemplazar IDs reales por temporales si corresponde (para lógica interna)
                s1_id = id_map.get(res.sesion_id, res.sesion_id)
                s2_id = id_map.get(res.sesion_2_id, res.sesion_2_id)

                conf_out = ConflictoOut(
                    # --- CAMPOS FALSIFICADOS PARA VALIDACIÓN ---
                    id=-1 * (i + 1),          # ID negativo único temporal
                    creado_en=datetime.now(), # Timestamp actual
                    # -------------------------------------------
                    tipo=res.tipo,
                    severidad=res.severidad,
                    descripcion=res.descripcion,
                    sesion_id=s1_id,
                    sesion_2_id=s2_id,
                    profesor_id=res.profesor_id,
                    aula_id=res.aula_id,
                    hash_deteccion=res.hash_deteccion,
                    estado=EstadoConflicto.POR_REVISAR
                )
                
                conflictos_out.append(conf_out)

            return conflictos_out

        except Exception as e:
            # logger.error(f"Error en simulación: {e}") # Descomentar para debug
            raise e
        finally:
            db.rollback()

    def delete(self, db: Session, id: int) -> None:
        """
        Eliminar sesión (DELETE físico).
        """
        if not sesion_repository.get_by_id(db, id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sesión con id {id} no encontrada"
            )
        
        # Limpieza explícita de conflictos
        conflictos_repository.delete_by_sesion_fisico(db, id)
        
        sesion_repository.delete(db, id)
        db.commit()

    def get_by_id(self, db: Session, id: int) -> SesionOut:
        sesion = sesion_repository.get_by_id(db, id)
        if not sesion:
            raise HTTPException(status_code=404, detail=f"Sesión {id} no encontrada")
        return self._to_sesion_out(sesion)
    
    def get_multi(self, db: Session, **kwargs) -> Tuple[List[SesionOut], int]:
        items, total = sesion_repository.get_multi(db, **kwargs)
        return [self._to_sesion_out(i) for i in items], total
    
    # ============================================================
    #  MÉTODOS AUXILIARES
    # ============================================================
    
    def _to_sesion_out(self, sesion: Sesion) -> SesionOut:
        """Helper para convertir modelo ORM a Schema Pydantic incluyendo profesores y CONFLICTOS"""
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
        
        # Profesores
        profesores_out = []
        for profesor in sesion.profesores:
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

        # --- Conflictos Activos ---
        # Recolectamos conflictos donde la sesión participa como s1 o s2
        active_conflictos = []
        
        # Conflictos donde es Sesión 1
        for c in sesion.conflictos_sesion_1:
            if c.estado == EstadoConflicto.POR_REVISAR:
                active_conflictos.append(c)
        
        # Conflictos donde es Sesión 2
        for c in sesion.conflictos_sesion_2:
            if c.estado == EstadoConflicto.POR_REVISAR:
                active_conflictos.append(c)
        
        # Convertimos a esquema
        sesion_dict['conflictos'] = [ConflictoOut.model_validate(c) for c in active_conflictos]

        return SesionOut(**sesion_dict)


# ============================================================
#  INSTANCIA SINGLETON
# ============================================================

sesion_service = SesionService()