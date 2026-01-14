from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from database.models import (
    GrupoDocente,
    Asignatura,
    Programa,
    AsignaturaMencion
)
from modules.docencia.schemas.dashboard import (
    ResumenHorarioOut,
    EstadoHorario,
    DashboardFiltros
)

class DashboardService:
    def get_resumen(self, db: Session, filtros: DashboardFiltros) -> List[ResumenHorarioOut]:
        """
        Genera el resumen de tarjetas para el dashboard.
        Optimizado para Mención Única y sin cálculo de conflictos.
        """
        # 1. Query Optimizada (Eager Loading)
        # Traemos solo lo necesario para evitar N+1 queries
        query = db.query(GrupoDocente)\
            .join(GrupoDocente.asignatura)\
            .join(Asignatura.programas)\
            .options(
                joinedload(GrupoDocente.sesiones),
                joinedload(GrupoDocente.asignatura)
                    .joinedload(Asignatura.asignatura_menciones)
                    .joinedload(AsignaturaMencion.mencion),
                joinedload(GrupoDocente.asignatura).joinedload(Asignatura.programas)
            )

        # 2. Aplicar Filtros Básicos en BD
        if filtros.programa_id:
            query = query.filter(Programa.id == filtros.programa_id)
        if filtros.curso:
            query = query.filter(GrupoDocente.curso == filtros.curso)

        # Ejecutamos consulta
        grupos_db = query.all()

        # 3. Agregación en Memoria
        # Estructura Clave -> Datos Agregados
        # Clave: (programa_id, curso, cuatrimestre, nombre_mencion_o_none)
        agrupacion: Dict[tuple, Dict[str, Any]] = {}
        now = datetime.now()

        for grupo in grupos_db:
            asignatura = grupo.asignatura
            
            nombres_menciones = []
            if asignatura.asignatura_menciones:
                for am in asignatura.asignatura_menciones:
                    if am.mencion:
                        nombres_menciones.append(am.mencion.nombre)
            
            # Si no tiene menciones, es Troncal (None)
            if not nombres_menciones:
                nombres_menciones = [None]

            # Iteramos sobre CADA mención (o None) para asignar el grupo a la tarjeta correcta
            for nombre_mencion in nombres_menciones:
                
                for programa in asignatura.programas:
                    if filtros.programa_id and programa.id != filtros.programa_id:
                        continue

                    cuatrimestre = getattr(asignatura, 'cuatrimestre', 1) or 1
                    
                    # La clave incluye el nombre de la mención específica
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
                            "ultima_actualizacion": now
                        }

                    stats = agrupacion[key]
                    stats["asignaturas_ids"].add(asignatura.id)
                    stats["total_sesiones"] += len(grupo.sesiones)

        # 4. Transformación a Esquema de Salida
        resultados = []
        for stats in agrupacion.values():
            # Formateo de mención para el frontend (Lista de strings)
            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                cuatrimestre=stats["cuatrimestre"],
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=EstadoHorario.OK, # Siempre OK por ahora
                conflictos_count=0,      # Siempre 0 por ahora
                ultima_actualizacion=stats["ultima_actualizacion"]
            )
            resultados.append(resumen)

        # 5. Ordenación (Programa -> Curso -> Cuatrimestre -> Troncales primero -> Menciones A-Z)
        resultados.sort(key=lambda x: (
            x.programa_id, 
            x.curso, 
            x.cuatrimestre, 
            0 if not x.menciones else 1, # Troncales (0) antes que menciones (1)
            x.menciones[0] if x.menciones else ""
        ))
        
        return resultados

dashboard_service = DashboardService()