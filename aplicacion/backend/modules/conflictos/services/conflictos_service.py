"""
Capa de servicio para la gestión de conflictos.
"""

from datetime import datetime, timezone
from typing import List, Tuple, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from constants.enums import EstadoConflicto, TipoConflicto, SeveridadConflicto
from modules.conflictos.schemas.conflicto import (
    ConflictoOut,
    ConflictoEstadoUpdateIn,
)
from modules.conflictos.repositories.conflictos_repo import conflictos_repository


class ConflictoService:
    """
    Servicio para gestionar la lógica de negocio de Conflictos existentes.
    """

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        tipo: Optional[TipoConflicto] = None,
        severidad: Optional[SeveridadConflicto] = None,
        estado: Optional[EstadoConflicto] = None,
        profesor_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        sesion_id: Optional[int] = None,
    ) -> Tuple[List[ConflictoOut], int]:
        """
        Listar conflictos para la "Tabla Global".
        """
        items_db, total = conflictos_repository.search(
            db,
            skip=skip,
            limit=limit,
            tipo=tipo,
            severidad=severidad,
            estado=estado,
            profesor_id=profesor_id,
            aula_id=aula_id,
            sesion_id=sesion_id,
        )
        return [ConflictoOut.model_validate(item) for item in items_db], total

    def get_by_sesion(self, db: Session, sesion_id: int) -> List[ConflictoOut]:
        """
        Obtener conflictos de una sesión para el "Tooltip Rojo" en el calendario.
        """
        items_db, _ = conflictos_repository.search(db, limit=1000, sesion_id=sesion_id)
        return [ConflictoOut.model_validate(item) for item in items_db]

    def update_estado(
        self,
        db: Session,
        conflicto_id: int,
        estado_in: ConflictoEstadoUpdateIn,
    ) -> ConflictoOut:
        """
        Gestión Manual: Cambiar estado a IGNORADO o RESUELTO.
        
        Nota: Esto NO elimina el conflicto, solo cambia su estado.
        La eliminación automática ocurre cuando se edita la sesión y se corrige el horario.
        """
        conflicto = conflictos_repository.get_by_id(db, conflicto_id)
        if not conflicto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflicto {conflicto_id} no encontrado",
            )

        nuevo_estado = estado_in.estado
        if conflicto.estado == nuevo_estado:
            return ConflictoOut.model_validate(conflicto)

        now = datetime.now(timezone.utc)

        if nuevo_estado == EstadoConflicto.SOLUCIONADO:
            conflicto.resuelto_en = now
        elif nuevo_estado == EstadoConflicto.POR_REVISAR:
            conflicto.resuelto_en = None
        
        conflicto.estado = nuevo_estado
        
        db.commit()
        db.refresh(conflicto)
        return ConflictoOut.model_validate(conflicto)

    def delete(self, db: Session, conflicto_id: int) -> None:
        """
        Eliminación Manual (Admin/Mantenimiento).
        
        Permite borrar un conflicto de la base de datos explícitamente.
        Normalmente el sistema gestiona esto, pero el usuario solicitó poder hacerlo si fuese necesario.
        """
        exito = conflictos_repository.delete(db, id=conflicto_id)
        if not exito:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflicto {conflicto_id} no encontrado",
            )
        db.commit()


conflicto_service = ConflictoService()