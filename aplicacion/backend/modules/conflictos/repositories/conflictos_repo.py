from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.core.conflictos.types import ResultadoDeteccion

from backend.constants.enums import EstadoConflicto
from database.models import Conflicto


def get_conflictos_for_sesion(db: Session, sesion_id: int) -> List[Conflicto]:
    """Devuelve todos los conflictos asociados a una sesión.

    Un conflicto está asociado a una sesión si aparece como sesion_id o sesion_2_id.
    """
    return (
        db.query(Conflicto)
        .filter(
            or_(
                Conflicto.sesion_id == sesion_id,
                Conflicto.sesion_2_id == sesion_id,
            )
        )
        .all()
    )


def _apply_resultado_to_conflicto(
    conflicto: Conflicto,
    resultado: ResultadoDeteccion,
    preserve_ignored: bool = True,
) -> None:
    """Actualiza los campos de un conflicto a partir de un ResultadoDeteccion.

    - Mantiene el estado IGNORADO si preserve_ignored=True.
    - Para otros estados, reabre el conflicto como ABIERTO.
    """

    conflicto.tipo = resultado.tipo
    conflicto.severidad = resultado.severidad
    conflicto.descripcion = resultado.descripcion
    conflicto.sesion_id = resultado.sesion_id
    conflicto.sesion_2_id = resultado.sesion_2_id
    conflicto.profesor_id = resultado.profesor_id
    conflicto.aula_id = resultado.aula_id
    conflicto.restriccion_id = resultado.restriccion_id

    # Reapertura de conflictos, respetando IGNORADO
    if preserve_ignored and conflicto.estado == EstadoConflicto.IGNORADO:
        # No tocar estado ni resuelto_en
        return

    # Para cualquier otro estado, el conflicto vuelve a estar activo
    conflicto.estado = EstadoConflicto.ABIERTO
    conflicto.resuelto_en = None


def sync_conflictos_for_sesion(
    db: Session,
    sesion_id: int,
    resultados_engine: Iterable[ResultadoDeteccion],
) -> List[Conflicto]:
    """Sincroniza los conflictos de la BD para una sesión con los resultados del engine.

    Reglas:
    - Se consideran solo conflictos donde la sesión aparece como sesion_id o sesion_2_id.
    - Cada conflicto se identifica de forma canónica por hash_deteccion (único en BD).
    - Si el motor devuelve un conflicto cuyo hash ya existe:
      - Se actualizan sus datos (tipo, severidad, descripción, refs...),
      - Se mantiene el estado IGNORADO si ya lo estaba,
      - En otros estados, se marca como ABIERTO y resuelto_en = None.
    - Si el motor devuelve un conflicto nuevo (hash no existente):
      - Se crea un nuevo registro con estado ABIERTO.
    - Si existe en BD un conflicto asociado a la sesión cuyo hash ya no aparece:
      - Se marca como RESUELTO y se rellena resuelto_en (si no estaba ya resuelto/ignorado).

    IMPORTANTE: esta función NO hace commit. El commit debe realizarse en la capa de servicio.
    """


    resultados_list = list(resultados_engine)
    hashes_nuevos = {r.hash_deteccion for r in resultados_list}

    # 1) Cargar conflictos actuales asociados a la sesión
    conflictos_existentes: List[Conflicto] = get_conflictos_for_sesion(db, sesion_id)
    conflictos_por_hash = {c.hash_deteccion: c for c in conflictos_existentes}

    # 2) Upsert de conflictos detectados por el engine
    for resultado in resultados_list:
        h = resultado.hash_deteccion
        conflicto_existente = conflictos_por_hash.get(h)

        if conflicto_existente is not None:
            # Actualizamos el conflicto existente respetando IGNORADO
            _apply_resultado_to_conflicto(conflicto_existente, resultado)
        else:
            # Crear nuevo conflicto en estado ABIERTO
            conflicto_nuevo = Conflicto(
                tipo=resultado.tipo,
                severidad=resultado.severidad,
                estado=EstadoConflicto.ABIERTO,
                sesion_id=resultado.sesion_id,
                sesion_2_id=resultado.sesion_2_id,
                profesor_id=resultado.profesor_id,
                aula_id=resultado.aula_id,
                restriccion_id=resultado.restriccion_id,
                descripcion=resultado.descripcion,
                hash_deteccion=resultado.hash_deteccion,
            )
            db.add(conflicto_nuevo)
            conflictos_existentes.append(conflicto_nuevo)
            conflictos_por_hash[h] = conflicto_nuevo

    # 3) Marcar como RESUELTO los conflictos que ya no aparecen en la detección
    now = datetime.now(timezone.utc)
    for conflicto in conflictos_existentes:
        if conflicto.hash_deteccion not in hashes_nuevos:
            if conflicto.estado not in (EstadoConflicto.RESUELTO, EstadoConflicto.IGNORADO):
                conflicto.estado = EstadoConflicto.RESUELTO
                conflicto.resuelto_en = now

    return conflictos_existentes
