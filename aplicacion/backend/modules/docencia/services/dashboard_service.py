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
        agrupacion: Dict[tuple, Dict[str, Any]] = {}
        now = datetime.now()

        for grupo in grupos_db:
            asignatura = grupo.asignatura
            
            # ✅ CORRECCIÓN: Guardamos tupla (nombre, programa_id_dueño)
            # En lugar de solo el nombre, guardamos a qué programa pertenece esa mención
            menciones_info = []
            if asignatura.asignatura_menciones:
                for am in asignatura.asignatura_menciones:
                    if am.mencion:
                        menciones_info.append({
                            "nombre": am.mencion.nombre,
                            "programa_id": am.mencion.programa_id # ID del grado dueño de la mención
                        })
            
            # Si no tiene menciones, es Troncal (None)
            if not menciones_info:
                menciones_info = [{"nombre": None, "programa_id": None}]

            # Iteramos sobre CADA mención (o None)
            for info in menciones_info:
                nombre_mencion = info["nombre"]
                owner_programa_id = info["programa_id"]
                
                for programa in asignatura.programas:
                    # Filtro de seguridad si se pidió un programa específico
                    if filtros.programa_id and programa.id != filtros.programa_id:
                        continue

                    # ✅ VALIDACIÓN CRÍTICA:
                    # Si estamos procesando una mención (no es None),
                    # SOLO debemos mostrarla si pertenece al programa actual.
                    # Esto evita que la mención de Matemáticas aparezca en el dashboard de Informática.
                    if nombre_mencion is not None and owner_programa_id != programa.id:
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
            menciones_out = [stats["mencion_str"]] if stats["mencion_str"] else []

            resumen = ResumenHorarioOut(
                programa_id=stats["programa_id"],
                programa_nombre=stats["programa_nombre"],
                curso=stats["curso"],
                cuatrimestre=stats["cuatrimestre"],
                menciones=menciones_out,
                total_asignaturas=len(stats["asignaturas_ids"]),
                total_sesiones=stats["total_sesiones"],
                estado=EstadoHorario.OK,
                conflictos_count=0,
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