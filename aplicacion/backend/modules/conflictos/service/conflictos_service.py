from datetime import datetime, timezone
from typing import List, Tuple, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.constants.enums import EstadoConflicto
from backend.modules.conflictos.schemas.conflicto import (
    ConflictoOut,
    ConflictoEstadoUpdateIn,
)
from backend.modules.conflictos.repositories.conflictos_repo import (
    search_conflictos,
    get_conflicto_by_id,
)


class ConflictoService:
    """Capa de servicio para la gestión de conflictos.

    Encapsula la lógica de lectura y actualización de conflictos persistidos.
    """

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        tipo=None,
        severidad=None,
        estado=None,
        profesor_id: Optional[int] = None,
        aula_id: Optional[int] = None,
        sesion_id: Optional[int] = None,
    ) -> Tuple[List[ConflictoOut], int]:
        """Listar conflictos con filtros y paginación.

        Devuelve los DTO de salida y el total antes de paginar.
        """

        conflictos, total = search_conflictos(
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

        items = [ConflictoOut.model_validate(c) for c in conflictos]
        return items, total

    def get_by_sesion(
        self,
        db: Session,
        *,
        sesion_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ConflictoOut], int]:
        """Listar conflictos asociados a una sesión concreta.

        Reutiliza search_conflictos para aplicar paginación de forma consistente.
        """

        conflictos, total = search_conflictos(
            db,
            skip=skip,
            limit=limit,
            sesion_id=sesion_id,
        )
        items = [ConflictoOut.model_validate(c) for c in conflictos]
        return items, total

    def update_estado(
        self,
        db: Session,
        *,
        conflicto_id: int,
        estado_in: ConflictoEstadoUpdateIn,
    ) -> ConflictoOut:
        """Actualiza el estado de un conflicto.

        Reglas básicas:
        - 404 si el conflicto no existe
        - Si el estado no cambia, devuelve el conflicto tal cual
        - Si pasa a RESUELTO, actualiza resuelto_en a now
        - Si pasa a ABIERTO, limpia resuelto_en
        - Si pasa a IGNORADO, mantiene resuelto_en tal cual (histórico)
        """

        conflicto = get_conflicto_by_id(db, conflicto_id)
        if not conflicto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflicto con id {conflicto_id} no encontrado",
            )

        nuevo_estado = estado_in.estado
        if conflicto.estado == nuevo_estado:
            # Nada que hacer
            return ConflictoOut.model_validate(conflicto)

        now = datetime.now(timezone.utc)

        conflicto.estado = nuevo_estado
        if nuevo_estado == EstadoConflicto.RESUELTO:
            conflicto.resuelto_en = now
        elif nuevo_estado == EstadoConflicto.ABIERTO:
            conflicto.resuelto_en = None
        # Para IGNORADO mantenemos resuelto_en como histórico (si lo hubiera)

        db.commit()
        db.refresh(conflicto)

        return ConflictoOut.model_validate(conflicto)


conflicto_service = ConflictoService()