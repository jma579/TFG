from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.models import (
    GrupoDocente,
    Asignatura,
    Programa,
    AsignaturaMencion,
    Sesion,
    ProgramaAsignatura  # <--- 1. IMPORTANTE: AÑADIDO
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
        # 1. Query Optimizada con JOIN a ProgramaAsignatura
        #    Esto es vital para poder filtrar por el curso "contextual" (del plan)
        #    y no por el curso "absoluto" (del grupo).
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programa_asignaturas)\
            .join(ProgramaAsignatura.programa)\
            .options(
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),
                
                # Cargamos la relación intermedia para leer el curso correcto en el bucle
                joinedload(GrupoDocente.asignatura).joinedload(Asignatura.programa_asignaturas).joinedload(ProgramaAsignatura.programa),
                
                # Carga de sesiones y sus conflictos (ambos lados)
                joinedload(GrupoDocente.sesiones).joinedload(Sesion.conflictos_sesion_1),
                joinedload(GrupoDocente.sesiones).joinedload(Sesion.conflictos_sesion_2)
            )

        # 2. Filtros BD (Aplicados sobre el CONTEXTO, no sobre el GRUPO)
        if filtros.programa_id:
            query = query.filter(ProgramaAsignatura.programa_id == filtros.programa_id)
        
        if filtros.curso:
            # CORRECCIÓN CLAVE: Filtramos por el curso del PLAN DE ESTUDIOS, no del grupo.
            query = query.filter(ProgramaAsignatura.curso == filtros.curso)

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
                mencion_programa_id = info["programa_id"]
                
                # CORRECCIÓN CLAVE: Iteramos sobre 'programa_asignaturas' para obtener el curso correcto
                for pa in asignatura.programa_asignaturas:
                    programa = pa.programa
                    curso_contextual = pa.curso  # <--- AQUÍ ESTÁ LA MAGIA (ej: 4º para Mates)

                    # Filtros de lógica de negocio
                    if filtros.programa_id and programa.id != filtros.programa_id:
                        continue
                    
                    # Si filtramos por curso, debe coincidir con el curso CONTEXTUAL
                    if filtros.curso and curso_contextual != filtros.curso:
                        continue

                    # Si la mención pertenece a un programa específico, solo mostramos ahí
                    if nombre_mencion is not None and mencion_programa_id != programa.id:
                        continue

                    cuatrimestre = getattr(asignatura, 'cuatrimestre', 1) or 1
                    
                    # Usamos 'curso_contextual' para la clave de agrupación
                    key = (programa.id, curso_contextual, cuatrimestre, nombre_mencion)

                    if key not in agrupacion:
                        agrupacion[key] = {
                            "programa_id": programa.id,
                            "programa_nombre": programa.nombre,
                            "curso": curso_contextual, # Guardamos 4º, no 2º
                            "cuatrimestre": cuatrimestre,
                            "mencion_str": nombre_mencion,
                            "asignaturas_ids": set(),
                            "total_sesiones": 0,
                            "conflictos_hashes": set(), 
                            "ultima_actualizacion": now
                        }

                    stats = agrupacion[key]
                    stats["asignaturas_ids"].add(asignatura.id)
                    stats["total_sesiones"] += len(grupo.sesiones)

                    # --- LÓGICA DE CONTEO DE CONFLICTOS ---
                    for sesion in grupo.sesiones:
                        for c in sesion.conflictos_sesion_1:
                            if c.estado == EstadoConflicto.POR_REVISAR:
                                stats["conflictos_hashes"].add(c.hash_deteccion)
                        
                        for c in sesion.conflictos_sesion_2:
                            if c.estado == EstadoConflicto.POR_REVISAR:
                                stats["conflictos_hashes"].add(c.hash_deteccion)

        # 4. Transformación
        resultados = []
        for stats in agrupacion.values():
            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []
            
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