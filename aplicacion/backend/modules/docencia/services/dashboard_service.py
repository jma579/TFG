from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.models import (
    GrupoDocente,
    Asignatura,
    Programa,
    AsignaturaMencion,
    Sesion
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
        Genera el resumen de tarjetas para el dashboard.
        Calcula la salud contando CONFLICTOS ÚNICOS (Hashes), no sesiones.
        """
        # 1. Query Optimizada
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programas)\
            .options(
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),
                joinedload(GrupoDocente.asignatura).joinedload(Asignatura.programas),
                
                # Carga de sesiones y sus conflictos (ambos lados)
                joinedload(GrupoDocente.sesiones).joinedload(Sesion.conflictos_sesion_1),
                joinedload(GrupoDocente.sesiones).joinedload(Sesion.conflictos_sesion_2)
            )

        # 2. Filtros BD
        if filtros.programa_id:
            query = query.filter(Programa.id == filtros.programa_id)
        if filtros.curso:
            query = query.filter(GrupoDocente.curso == filtros.curso)

        grupos_db = query.all()

        # 3. Agregación en Memoria
        agrupacion: Dict[tuple, Dict[str, Any]] = {}
        now = datetime.now()

        for grupo in grupos_db:
            asignatura = grupo.asignatura
            
            # Gestión de menciones
            menciones_info = []
            if asignatura.asignatura_menciones:
                for am in asignatura.asignatura_menciones:
                    if am.mencion:
                        menciones_info.append({
                            "nombre": am.mencion.nombre,
                            "programa_id": am.mencion.programa_id
                        })
            
            if not menciones_info:
                menciones_info = [{"nombre": None, "programa_id": None}]

            for info in menciones_info:
                nombre_mencion = info["nombre"]
                owner_programa_id = info["programa_id"]
                
                for programa in asignatura.programas:
                    if filtros.programa_id and programa.id != filtros.programa_id:
                        continue

                    if nombre_mencion is not None and owner_programa_id != programa.id:
                        continue

                    cuatrimestre = getattr(asignatura, 'cuatrimestre', 1) or 1
                    
                    key = (programa.id, grupo.curso, cuatrimestre, nombre_mencion)

                    if key not in agrupacion:
                        agrupacion[key] = {
                            "programa_id": programa.id,
                            "programa_nombre": programa.nombre,
                            "curso": grupo.curso,
                            "cuatrimestre": cuatrimestre,
                            "mencion_str": nombre_mencion,
                            "asignaturas_ids": set(),
                            "total_sesiones": 0,
                            # CAMBIO: Usamos un set de strings para los HASHES de conflicto
                            "conflictos_hashes": set(), 
                            "ultima_actualizacion": now
                        }

                    stats = agrupacion[key]
                    stats["asignaturas_ids"].add(asignatura.id)
                    stats["total_sesiones"] += len(grupo.sesiones)

                    # --- LÓGICA DE CONTEO DE CONFLICTOS (DEDUPLICADA) ---
                    for sesion in grupo.sesiones:
                        # Revisamos conflictos donde esta sesión es la "Principal" (1)
                        for c in sesion.conflictos_sesion_1:
                            if c.estado == EstadoConflicto.POR_REVISAR:
                                stats["conflictos_hashes"].add(c.hash_deteccion)
                        
                        # Revisamos conflictos donde esta sesión es la "Secundaria" (2)
                        # Importante: Si dos sesiones del mismo grupo chocan, ambas tendrán
                        # el mismo hash_deteccion. Al ser un set, solo cuenta como 1.
                        for c in sesion.conflictos_sesion_2:
                            if c.estado == EstadoConflicto.POR_REVISAR:
                                stats["conflictos_hashes"].add(c.hash_deteccion)

        # 4. Transformación
        resultados = []
        for stats in agrupacion.values():
            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []
            
            # El número real de incidencias únicas a resolver
            num_conflictos_reales = len(stats["conflictos_hashes"])
            
            estado_calculado = EstadoHorario.CONFLICTO if num_conflictos_reales > 0 else EstadoHorario.OK

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                cuatrimestre=stats["cuatrimestre"],
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=estado_calculado,
                # Ahora enviamos el número de problemas únicos
                conflictos_count=num_conflictos_reales,
                ultima_actualizacion=stats["ultima_actualizacion"]
            )
            resultados.append(resumen)

        # 5. Ordenación
        resultados.sort(key=lambda x: (
            x.programa_id, 
            x.curso, 
            x.cuatrimestre, 
            0 if not x.menciones else 1,
            x.menciones[0] if x.menciones else ""
        ))
        
        return resultados

dashboard_service = DashboardService()