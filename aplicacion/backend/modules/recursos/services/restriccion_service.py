"""
Servicio para la entidad Restriccion.
Contiene la lógica de negocio, validaciones y orquesta la importación de Excel.
"""

import os
import tempfile
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from typing import List

from modules.recursos.repositories.restriccion_repo import restriccion_repository
from modules.recursos.repositories.profesor_repo import ProfesorRepository

from modules.recursos.schemas.restriccion import (
    RestriccionCreate, RestriccionUpdate, RestriccionResponse, 
    ImportacionRestriccionesResponse
)

from core.extraccion.restricciones.extractor import get_restricciones_extractor
from core.extraccion.restricciones.parser import get_restricciones_parser
from core.extraccion.restricciones.normalize import get_restricciones_normalizer

from database.models import Restriccion


class RestriccionService:
    def __init__(self):
        self.repo = restriccion_repository
        self.profesor_repo = ProfesorRepository()
        
        self.extractor = get_restricciones_extractor()
        self.parser = get_restricciones_parser()
        self.normalizer = get_restricciones_normalizer()


    # Gestion manual (CRUD)

    def get_restricciones_profesor(self, db: Session, profesor_id: int) -> List[RestriccionResponse]:
        """Obtiene las restricciones de un profesor."""
        if not self.profesor_repo.get_by_id(db, profesor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado.")
        return self.repo.get_by_profesor(db, profesor_id)

    def crear_restriccion_manual(
        self, db: Session, profesor_id: int, restriccion_in: RestriccionCreate
    ) -> RestriccionResponse:
        """Crea una restricción validando la regla de negocio de horarios."""
        if restriccion_in.hora_inicio >= restriccion_in.hora_fin:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, 
                detail="La hora de inicio debe ser anterior a la hora de fin."
            )
        if not self.profesor_repo.get_by_id(db, profesor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Profesor no encontrado.")

        db_obj = self.repo.create(db, profesor_id, restriccion_in)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def actualizar_restriccion(
        self, db: Session, restriccion_id: int, restriccion_in: RestriccionUpdate
    ) -> RestriccionResponse:
        """Actualiza validando que la combinación final de horas sea correcta."""
        db_obj = self.repo.get_by_id(db, restriccion_id)
        if not db_obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Restricción no encontrada.")

        h_inicio_final = restriccion_in.hora_inicio if restriccion_in.hora_inicio else db_obj.hora_inicio
        h_fin_final = restriccion_in.hora_fin if restriccion_in.hora_fin else db_obj.hora_fin

        if h_inicio_final >= h_fin_final:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, 
                detail="La combinación de horas resultante es inválida (inicio >= fin)."
            )

        updated_obj = self.repo.update(db, db_obj, restriccion_in)
        db.commit()
        db.refresh(updated_obj)
        return updated_obj

    def eliminar_restriccion(self, db: Session, restriccion_id: int) -> dict:
        """Elimina una restricción por su ID."""
        db_obj = self.repo.get_by_id(db, restriccion_id)
        if not db_obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Restricción no encontrada.")
            
        self.repo.delete(db, db_obj)
        db.commit()
        return {"message": "Restricción eliminada correctamente."}


    # Importacion masiva (DROP & LOAD)

    def importar_excel(self, db: Session, file: UploadFile) -> ImportacionRestriccionesResponse:
        """
        Orquesta el flujo: 
        1. FASE 2 (Extractor -> Parser -> Normalizer)
        2. FASE 3 (Emparejamiento de profesores)
        3. Borrado total y guardado masivo en BD.
        """
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                file_bytes = file.file.read()
                tmp.write(file_bytes)
                tmp_path = tmp.name

            # 1. Pipeline de Extracción
            ext_result = self.extractor.extract_from_excel(tmp_path)
            if not ext_result.success:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ext_result.error_message)

            parsed_rows, metadata = self.parser.parse_rows(ext_result)
            normalized_data = self.normalizer.normalize_rows(parsed_rows, metadata)

            # 2. Caché de profesores para emparejamiento rápido
            profesores_db, _ = self.profesor_repo.get_multi(db, limit=10000, activo=True)
            mapa_profesores = {}
            for p in profesores_db:
                nombre_completo = f"{p.nombre} {p.apellidos}".strip().lower()
                nombre_completo = " ".join(nombre_completo.split()) 
                mapa_profesores[nombre_completo] = p.id

            # 3. Fase de Validación (Strict Match)
            restricciones_a_insertar: List[Restriccion] = []
            errores = metadata.errors.copy()
            warnings = [w.message for w in metadata.warnings]

            for data in normalized_data:
                nombre_buscar = data.profesor_nombre_completo.lower()
                prof_id = mapa_profesores.get(nombre_buscar)

                if not prof_id:
                    errores.append(f"Fila {data.fila_origen}: Profesor '{data.profesor_nombre_completo}' no encontrado en BD.")
                else:
                    restricciones_a_insertar.append(
                        Restriccion(
                            profesor_id=prof_id,
                            dia_semana=data.dia_semana,
                            hora_inicio=data.hora_inicio,
                            hora_fin=data.hora_fin
                        )
                    )

            # 4. Si hay errores, abortamos antes de tocar la BD
            if errores:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "La importación ha sido cancelada por errores de validación.",
                        "errores": errores,
                        "warnings": warnings
                    }
                )

            # 5. Ejecución (Solo llegamos aquí si el Excel es perfecto)
            registros_eliminados = self.repo.delete_all(db)
            self.repo.bulk_create(db, restricciones_a_insertar)
            db.commit()

            return ImportacionRestriccionesResponse(
                registros_creados=len(restricciones_a_insertar),
                registros_eliminados=registros_eliminados,
                errores=[],
                warnings=warnings
            )

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


restriccion_service = RestriccionService()