from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database.models import (
    GrupoDocente,
    Asignatura,
    Programa,
    AsignaturaMencion,
    Mencion,
    Conflicto
)
from modules.docencia.schemas.dashboard import (
    ResumenHorarioOut,
    EstadoHorario,
    DashboardFiltros
)

class DashboardService:
    def get_resumen(self, db: Session, filtros: DashboardFiltros) -> List[ResumenHorarioOut]:
        # 1. Query Base
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.sesiones)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programas)\
            .options(
                joinedload(GrupoDocente.sesiones),
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),
                joinedload(GrupoDocente.asignatura).joinedload(Asignatura.programas)
            )

        # 2. Aplicar Filtros
        if filtros.programa_id:
            query = query.filter(Programa.id == filtros.programa_id)
        if filtros.curso:
            query = query.filter(GrupoDocente.curso == filtros.curso)

        raw_rows = query.all()

        # Deduplicación
        grupos_unicos_map = {grupo.id: grupo for grupo in raw_rows}
        grupos_activos = list(grupos_unicos_map.values())

        agrupacion: Dict[tuple, Dict[str, Any]] = {}
        now = datetime.now()

        print(f"\n--- [DEBUG] INICIO PROCESAMIENTO DASHBOARD ({len(grupos_activos)} grupos) ---")

        for grupo in grupos_activos:
            lista_programas = grupo.asignatura.programas

            # DEBUG: Imprimir info de asignaturas de 4º curso para ver si detecta menciones
            if grupo.curso == 4:
                print(f"[DEBUG] Analizando Grupo ID {grupo.id} - Asignatura: {grupo.asignatura.nombre}")

            for programa in lista_programas:
                if filtros.programa_id and programa.id != filtros.programa_id:
                    continue

                curso = grupo.curso
                cuatrimestre = getattr(grupo.asignatura, 'cuatrimestre', 1) 
                
                # Obtener menciones explícitas
                mencion_nombres = []
                asoc_menciones = grupo.asignatura.asignatura_menciones
                
                if asoc_menciones:
                    for assoc in asoc_menciones:
                        if assoc.mencion:
                            mencion_nombres.append(assoc.mencion.nombre)
                
                # DEBUG: Ver qué encontró
                if grupo.curso == 4:
                    print(f"   -> Menciones encontradas en DB: {mencion_nombres}")

                iterador_menciones = mencion_nombres if mencion_nombres else [None]

                for nombre_mencion in iterador_menciones:
                    key = (programa.id, curso, cuatrimestre, nombre_mencion)

                    if key not in agrupacion:
                        agrupacion[key] = {
                            "programa_id": programa.id,
                            "programa_nombre": programa.nombre,
                            "curso": curso,
                            "cuatrimestre": cuatrimestre,
                            "mencion_str": nombre_mencion,
                            "asignaturas_ids": set(),
                            "total_sesiones": 0,
                            "conflictos_count": 0,
                            "ultima_actualizacion": now
                        }

                    stats = agrupacion[key]
                    stats["asignaturas_ids"].add(grupo.asignatura_id)
                    stats["total_sesiones"] += len(grupo.sesiones)

        print("--- [DEBUG] FIN PROCESAMIENTO ---\n")

        # 4. Convertir a Lista
        resultados = []
        for key, stats in agrupacion.items():
            c_count = stats["conflictos_count"]
            estado = EstadoHorario.CONFLICTO if c_count > 0 else EstadoHorario.OK
            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                cuatrimestre=stats["cuatrimestre"],
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=estado,
                conflictos_count=c_count,
                ultima_actualizacion=stats["ultima_actualizacion"]
            )
            resultados.append(resumen)

        resultados.sort(key=lambda x: (
            x.programa_id, 
            x.curso, 
            x.cuatrimestre, 
            0 if not x.menciones else 1, 
            x.menciones[0] if x.menciones else ""
        ))
        
        return resultados

dashboard_service = DashboardService()