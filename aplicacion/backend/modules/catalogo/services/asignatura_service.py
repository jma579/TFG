"""
Servicio para la entidad Asignatura (API).

Reglas de Negocio:
1. La creación y edición de asignaturas está restringida al Pipeline de Ingesta de PDFs.
2. La API solo permite lectura y borrado (Soft/Hard).
3. Se mantienen todos los métodos de recuperación de datos relacionados.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from modules.catalogo.repositories.asignatura_repo import asignatura_repository
from modules.catalogo.repositories.programa_asignatura_repo import programa_asignatura_repository
from modules.recursos.repositories.profesor_asignatura_repo import profesor_asignatura_repository

from modules.catalogo.schemas.asignatura import (
    AsignaturaOut, AsignaturaList, AsignaturaProgramaOut
)
from modules.recursos.schemas.profesor import ProfesorOut

class AsignaturaService:
    def __init__(self):
        self.repo = asignatura_repository
        self.programa_asignatura_repo = programa_asignatura_repository
        self.profesor_asignatura_repo = profesor_asignatura_repository

    # ==========================
    # LECTURA (Consultas)
    # ==========================

    def get_asignatura(self, db: Session, asignatura_id: int) -> AsignaturaOut:
        """Obtiene el detalle completo de una asignatura."""
        asignatura = self.repo.get_by_id(db, asignatura_id)
        if not asignatura:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asignatura no encontrada")
        return self._map_to_out(asignatura)

    def get_asignatura_by_codigo(self, db: Session, codigo_plan: str) -> AsignaturaOut:
        """Obtiene una asignatura por su código de plan."""
        asignatura = self.repo.get_by_codigo(db, codigo_plan)
        if not asignatura:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Asignatura con código '{codigo_plan}' no encontrada")
        return self._map_to_out(asignatura)

    def get_asignaturas(self, db: Session, skip: int = 0, limit: int = 100, **kwargs) -> AsignaturaList:
        """Lista asignaturas paginadas con filtros."""
        items, total = self.repo.get_multi(db, skip, limit, **kwargs)
        return AsignaturaList(
            total=total,
            items=[self._map_to_out(item) for item in items],
            page=(skip // limit) + 1,
            size=limit
        )

    def get_asignaturas_by_programa(
        self, db: Session, programa_id: int, skip: int = 0, limit: int = 100
    ) -> AsignaturaList:
        """Devuelve las asignaturas de un programa específico."""
        items, total = self.repo.get_by_programa(db, programa_id, skip, limit)
        return AsignaturaList(
            total=total,
            items=[self._map_to_out(item) for item in items],
            page=(skip // limit) + 1,
            size=limit
        )

    def get_programas_de_asignatura(self, db: Session, asignatura_id: int) -> List[AsignaturaProgramaOut]:
        """Obtiene las titulaciones/programas asociados a una asignatura."""
        if not self.repo.get_by_id(db, asignatura_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asignatura no encontrada")
        
        rels = self.programa_asignatura_repo.get_by_asignatura(db, asignatura_id)
        return [
            AsignaturaProgramaOut(
                programa=r.programa, 
                curso=r.curso, 
                tipo_asignatura=r.tipo_asignatura
            ) for r in rels
        ]

    def get_profesores_de_asignatura(self, db: Session, asignatura_id: int) -> List[ProfesorOut]:
        """Obtiene los profesores asignados a una asignatura."""
        if not self.repo.get_by_id(db, asignatura_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asignatura no encontrada")
            
        rels = self.profesor_asignatura_repo.get_by_asignatura(db, asignatura_id)
        return [ProfesorOut.model_validate(r.profesor) for r in rels]

    # ==========================
    # ESCRITURA (Restringida)
    # ==========================

    def delete_asignatura(self, db: Session, asignatura_id: int, physical: bool = False) -> dict:
        """
        Elimina una asignatura.
        
        Args:
            physical (bool): Si es True, realiza un borrado físico (SQL DELETE).
                             Si es False, realiza un borrado lógico (activo=False).
        """
        if not self.repo.get_by_id(db, asignatura_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asignatura no encontrada")
        
        if physical:
            self.repo.delete_physical(db, asignatura_id)
            msg = "Asignatura eliminada físicamente (Irreversible)"
        else:
            self.repo.delete(db, asignatura_id)
            msg = "Asignatura desactivada (Soft Delete)"
            
        db.commit() # Commit explícito para la API
        return {"message": msg}

    # ==========================
    # HELPERS
    # ==========================

    def _map_to_out(self, asignatura) -> AsignaturaOut:
        """Helper para mapear ORM a Schema incluyendo conteos calculados."""
        out = AsignaturaOut.model_validate(asignatura)
        out.num_profesores = len(asignatura.profesores_asignaturas)
        out.num_titulaciones = len(asignatura.programa_asignaturas)
        out.titulaciones = [
            AsignaturaProgramaOut.model_validate(pa) for pa in asignatura.programa_asignaturas
        ]
        return out

asignatura_service = AsignaturaService()