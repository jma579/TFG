"""
Servicio para el Dashboard de Docencia: Resumen de Horarios
Este servicio genera un resumen de tarjetas
para el dashboard de docencia, agrupando por programa, curso, periodo y mención.
Calcula la "salud" del horario basado en conflictos únicos detectados en las sesiones.
"""

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.models import (
    GrupoDocente,
    Asignatura,
    Sesion, 
    ProgramaAsignatura
)
from modules.docencia.schemas.dashboard import (
    ResumenHorarioOut,
    EstadoHorario,
    DashboardFiltros
)
from constants.enums import EstadoConflicto

class DashboardService:
    def get_resumen(self, db: Session, filtros: DashboardFiltros) -> List[ResumenHorarioOut]:
        """
        Genera el resumen de tarjetas para el dashboard separando por Cuatrimestre.
        Calcula la salud contando CONFLICTOS ÚNICOS (Hashes) por cada periodo.
        """
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programa_asignaturas)\
            .join(ProgramaAsignatura.programa)\
            .options(
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.programa_asignaturas)
                    .joinedload(ProgramaAsignatura.mencion),
                joinedload(GrupoDocente.sesiones)
                    .joinedload(Sesion.conflictos_sesion_1),
                joinedload(GrupoDocente.sesiones)
                    .joinedload(Sesion.conflictos_sesion_2)
            )

        if filtros.programa_id:
            query = query.filter(ProgramaAsignatura.programa_id == filtros.programa_id)
        if filtros.curso:
            query = query.filter(ProgramaAsignatura.curso == filtros.curso)

        grupos = query.all()

        agrupacion: Dict[tuple, Dict[str, Any]] = {}

        for gd in grupos:
            prog_id = filtros.programa_id or gd.asignatura.programa_asignaturas[0].programa_id
            pa_context = next((pa for pa in gd.asignatura.programa_asignaturas if pa.programa_id == prog_id), None)
            curso_context = pa_context.curso if pa_context else 1
            
            periodo_actual = gd.asignatura.periodo 
            
            mencion_str = ""
            if pa_context and pa_context.mencion:
                mencion_str = pa_context.mencion.nombre
            
            key = (prog_id, curso_context, periodo_actual, mencion_str)

            if key not in agrupacion:
                agrupacion[key] = {
                    "programa_id": prog_id,
                    "programa_nombre": pa_context.programa.nombre if pa_context else "Desconocido",
                    "curso": curso_context,
                    "cuatrimestre": periodo_actual,
                    "asignaturas_ids": set(),
                    "total_sesiones": 0,
                    "ultima_actualizacion": None,
                    "conflictos_hashes": set(),
                    "mencion_str": mencion_str
                }

            stats = agrupacion[key]
            stats["asignaturas_ids"].add(gd.asignatura_id)
            stats["total_sesiones"] += len(gd.sesiones)

            for sesion in gd.sesiones:
                todos_conflictos = sesion.conflictos_sesion_1 + sesion.conflictos_sesion_2
                for c in todos_conflictos:
                    if c.estado == EstadoConflicto.POR_REVISAR:
                        stats["conflictos_hashes"].add(c.hash_deteccion)

        resultados = []
        for stats in agrupacion.values():
            if stats["total_sesiones"] == 0:
                continue

            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []
            
            num_conflictos_reales = len(stats["conflictos_hashes"])
            estado_calculado = EstadoHorario.CONFLICTO if num_conflictos_reales > 0 else EstadoHorario.OK

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                periodo=stats["cuatrimestre"],
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=estado_calculado,
                conflictos_count=num_conflictos_reales,
                ultima_actualizacion=stats["ultima_actualizacion"] or datetime.now()
            )
            resultados.append(resumen)

        resultados.sort(key=lambda x: (
            x.programa_id, 
            x.curso, 
            x.periodo
        ))

        return resultados


dashboard_service = DashboardService()