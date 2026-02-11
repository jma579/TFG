from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.models import (
    GrupoDocente,
    Asignatura,
    Programa,
    AsignaturaMencion,
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
        # 1. Query Optimizada con JOIN a ProgramaAsignatura
        # Incluimos los joins necesarios para filtrar y obtener el contexto del curso
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programa_asignaturas)\
            .join(ProgramaAsignatura.programa)\
            .options(
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),
                joinedload(GrupoDocente.sesiones)
                    .joinedload(Sesion.conflictos_sesion_1),
                joinedload(GrupoDocente.sesiones)
                    .joinedload(Sesion.conflictos_sesion_2)
            )

        # Filtros de búsqueda desde la UI
        if filtros.programa_id:
            query = query.filter(ProgramaAsignatura.programa_id == filtros.programa_id)
        if filtros.curso:
            query = query.filter(ProgramaAsignatura.curso == filtros.curso)

        grupos = query.all()

        # 2. Agrupación por (Programa, Curso, Periodo)
        # La clave ahora incluye el periodo para evitar que 1C y 2C se mezclen en la misma tarjeta
        agrupacion: Dict[tuple, Dict[str, Any]] = {}

        for gd in grupos:
            # Determinamos el contexto (Programa y Curso)
            # Priorizamos el programa filtrado o el primero asociado a la asignatura
            prog_id = filtros.programa_id or gd.asignatura.programa_asignaturas[0].programa_id
            pa_context = next((pa for pa in gd.asignatura.programa_asignaturas if pa.programa_id == prog_id), None)
            curso_context = pa_context.curso if pa_context else 1
            
            # --- CAMBIO CRÍTICO: Identificar el periodo de la asignatura ---
            periodo_actual = gd.asignatura.periodo 
            
            # --- NUEVO: Extraemos la mención ANTES de generar la clave ---
            mencion_str = ""
            if gd.asignatura.asignatura_menciones:
                mencion_str = gd.asignatura.asignatura_menciones[0].mencion.nombre
            
            # --- CORRECCIÓN 1: La clave incluye la mención para que no se sobrescriban ---
            key = (prog_id, curso_context, periodo_actual, mencion_str)

            if key not in agrupacion:
                agrupacion[key] = {
                    "programa_id": prog_id,
                    "programa_nombre": pa_context.programa.nombre if pa_context else "Desconocido",
                    "curso": curso_context,
                    "cuatrimestre": periodo_actual, # Almacenamos el Enum para la salida
                    "asignaturas_ids": set(),
                    "total_sesiones": 0,
                    "ultima_actualizacion": None,
                    "conflictos_hashes": set(),
                    "mencion_str": mencion_str
                }

            stats = agrupacion[key]
            stats["asignaturas_ids"].add(gd.asignatura_id)
            stats["total_sesiones"] += len(gd.sesiones)

            # Gestión de menciones (si aplica)
            if not stats["mencion_str"] and gd.asignatura.asignatura_menciones:
                stats["mencion_str"] = gd.asignatura.asignatura_menciones[0].mencion.nombre

            # 3. Recolección de Conflictos Únicos del Periodo
            for sesion in gd.sesiones:
                # Unir conflictos de ambos lados de la relación (bidireccional)
                todos_conflictos = sesion.conflictos_sesion_1 + sesion.conflictos_sesion_2
                for c in todos_conflictos:
                    if c.estado == EstadoConflicto.POR_REVISAR:
                        # Usamos el hash para no contar dos veces el mismo solape
                        stats["conflictos_hashes"].add(c.hash_deteccion)

        # 4. Transformación a Objetos de Salida (Pydantic)
        resultados = []
        for stats in agrupacion.values():
            # Si el bloque académico no tiene sesiones reales, lo saltamos
            if stats["total_sesiones"] == 0:
                continue

            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []
            
            num_conflictos_reales = len(stats["conflictos_hashes"])
            estado_calculado = EstadoHorario.CONFLICTO if num_conflictos_reales > 0 else EstadoHorario.OK

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                periodo=stats["cuatrimestre"], # Valor real del Enum
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=estado_calculado,
                conflictos_count=num_conflictos_reales,
                ultima_actualizacion=stats["ultima_actualizacion"] or datetime.now()
            )
            resultados.append(resumen)

        # 5. Ordenación lógica: Programa -> Curso -> Cuatrimestre
        resultados.sort(key=lambda x: (
            x.programa_id, 
            x.curso, 
            x.periodo
        ))

        return resultados

dashboard_service = DashboardService()