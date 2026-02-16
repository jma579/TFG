"""
Servicio para la entidad Profesor (API).

Reglas de Negocio:
1. La creación de profesores es exclusiva del Pipeline de Ingesta (Fichas).
2. Se permite la edición manual de datos.
3. Se soporta borrado lógico (default) y físico (admin).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from modules.recursos.repositories.profesor_repo import profesor_repository
from modules.recursos.schemas.profesor import ProfesorUpdate, ProfesorOut, ProfesorList

class ProfesorService:
    """Service para lógica de negocio de Profesor."""

    def __init__(self):
        """Inicializa el servicio con el repositorio de profesores."""
        self.repo = profesor_repository


    def get_profesores(
        self, db: Session, skip: int, limit: int, activo: Optional[bool]
    ) -> ProfesorList:
        """Lista profesores con paginación incluyendo el conteo de restricciones."""
        items, total = self.repo.get_multi(db, skip, limit, activo)
        profesores_out = []
        for p in items:
            p_data = ProfesorOut.model_validate(p)
            p_data.total_restricciones = len(p.restricciones) if hasattr(p, 'restricciones') else 0
            profesores_out.append(p_data)

        return ProfesorList(
            total=total, 
            items=profesores_out, 
            page=(skip // limit) + 1, 
            size=limit
        )

    def get_profesor(self, db: Session, profesor_id: int) -> ProfesorOut:
        """Obtiene detalle de un profesor."""
        prof = self.repo.get_by_id(db, profesor_id)
        if not prof:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado")
        return ProfesorOut.model_validate(prof)


    def update_profesor(
        self, db: Session, profesor_id: int, prof_in: ProfesorUpdate
    ) -> ProfesorOut:
        """
        Actualiza manualmente los datos de un profesor.
        Permite corregir información o añadir datos de contacto.
        """
        prof = self.repo.get_by_id(db, profesor_id)
        if not prof: 
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado")
        
        updated = self.repo.update(db, profesor_id, prof_in.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(updated)
        return ProfesorOut.model_validate(updated)

    def delete_profesor(self, db: Session, profesor_id: int, physical: bool) -> dict:
        """Elimina un profesor."""
        if not self.repo.get_by_id(db, profesor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado")
        
        if physical:
            self.repo.delete_physical(db, profesor_id)
            msg = "Profesor eliminado físicamente"
        else:
            self.repo.delete(db, profesor_id)
            msg = "Profesor desactivado"
            
        db.commit()
        return {"message": msg}


profesor_service = ProfesorService()