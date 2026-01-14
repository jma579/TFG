from __future__ import annotations

from typing import Dict, List, Optional, Union, Set, Tuple
from pathlib import Path
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

# Schemas
from modules.docencia.schemas.horarios import (
    HorarioTemporalOut, 
    HorarioTemporalConfirmIn, 
    HorarioConfirmResponse
)
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate,
    GrupoDocenteOut,
)
from modules.docencia.schemas.sesion import SesionCreate, SesionOut

# Servicios y Repositorios
from modules.docencia.services.grupo_docente_service import grupo_docente_service
from modules.docencia.services.sesion_service import sesion_service
from modules.docencia.repositories.grupo_docente_repo import grupo_docente_repository
from modules.recursos.repositories.aula_repo import aula_repository

# Modelos DB
from database.models import (
    Asignatura, 
    Aula, 
    Programa, 
    Mencion, 
    AsignaturaMencion, 
    GrupoDocente, 
    Sesion, 
    AsignaturaAlias
)

# Core Pipeline Components
from core.extraccion.horarios.extractor.extractor import HorarioExtractor
from core.extraccion.horarios.parser.parser import HorarioParser
from core.extraccion.horarios.normalizador.normalize import horario_data_normalizer
from modules.docencia.services.horarios_normalization_models import (
    build_parsing_result_for_normalization,
)

# Matchers (Importamos las CLASES para instanciar con la sesión actual)
from modules.catalogo.services.asignatura_matcher import AsignaturaMatcher
from modules.recursos.services.aula_matcher import AulaMatcher

# Enums
from constants.enums import TipoGrupoDocente, DiaSemana

logger = logging.getLogger(__name__)

# Mapeo estático para convertir texto español a Enum
TEXTO_A_DIA_ENUM = {
    "LUNES": DiaSemana.LUNES,
    "MARTES": DiaSemana.MARTES,
    "MIERCOLES": DiaSemana.MIERCOLES,
    "MIÉRCOLES": DiaSemana.MIERCOLES,
    "JUEVES": DiaSemana.JUEVES,
    "VIERNES": DiaSemana.VIERNES,
    "SABADO": DiaSemana.SABADO,
    "SÁBADO": DiaSemana.SABADO,
    "DOMINGO": DiaSemana.DOMINGO
}

class HorariosPipelineService:
    """
    Servicio de orquestación del flujo de horarios.
    Coordina Extracción -> Revisión -> Confirmación (Persistencia).
    """

    def __init__(self) -> None:
        """Inicializa los componentes del pipeline."""
        self._extractor = HorarioExtractor()
        self._parser = HorarioParser()

    def extraer_horario(self, db: Session, pdf_path: Union[str, Path]) -> HorarioTemporalOut:
        """
        Procesa el PDF y utiliza el matcher inteligente para contextualizar los resultados.
        """
        # 1. Extracción y Parsing
        path_str = str(pdf_path)
        extraction_result = self._extractor.extract(path_str)
        parsed_dict = self._parser.parse(extraction_result)
        horario_out = HorarioTemporalOut(**parsed_dict)

        # 2. Inicializar Matchers
        asig_matcher = AsignaturaMatcher(db)
        aula_matcher_srv = AulaMatcher(db) 

        # Delegamos en el matcher la detección del Programa (usando caché y fuzzy)
        prog_id = asig_matcher.infer_program_id(horario_out.plan or horario_out.titulo)

        for tabla in horario_out.horarios:
            # Obtener curso numérico
            curso_int = 0
            if tabla.curso:
                digits = "".join(filter(str.isdigit, str(tabla.curso)))
                if digits:
                    curso_int = int(digits)

            nuevas_sesiones = []
            
            for sesion in tabla.sesiones:
                sesion.texto_original = sesion.asignatura

                # A. Match Asignatura
                if sesion.asignatura:
                    asig_obj, metodo, score = asig_matcher.match(
                        texto_raw=sesion.asignatura, 
                        prog_id=prog_id,  # Contexto inyectado
                        curso=curso_int
                    )
                    
                    sesion.match_confidence = score
                    sesion.match_status = metodo
                    if asig_obj:
                        sesion.asignatura_id = asig_obj.id
                        sesion.asignatura_sugerida = asig_obj.nombre

                # B. División de Grupos (Negocio)
                grupos_detectados = horario_data_normalizer.detectar_y_dividir_grupos(sesion.grupo)
                
                for grupo_item in grupos_detectados:
                    sesion_clonada = sesion.model_copy()
                    texto_aula_original = sesion_clonada.aula or ""
                    
                    # C. Match Aula
                    texto_aula = sesion_clonada.aula or ""
                    match_aula = aula_matcher_srv.match(texto_aula)
                    
                    if match_aula:
                        sesion_clonada.aula_id = match_aula.id
                        sesion_clonada.aula_nombre = match_aula.nombre
                        sesion_clonada.aula = match_aula.nombre
                    else:
                        sesion_clonada.aula_nombre = texto_aula or "POR DETERMINAR"

                    # D. Inferencia Tipo
                    nombre_para_inferencia = sesion_clonada.aula_nombre if match_aula else texto_aula_original
                    aula_norm = horario_data_normalizer._normalize_aula(nombre_para_inferencia)
                    grupo_limpio, tipo_detectado = horario_data_normalizer.infer_grupo_y_tipo(grupo_item, aula_norm)
                    
                    sesion_clonada.grupo_codigo = grupo_limpio
                    if tipo_detectado:
                        sesion_clonada.tipo_grupo = tipo_detectado.value 
                        if tipo_detectado == TipoGrupoDocente.LABORATORIO:
                            sesion_clonada.tipo = "PRÁCTICAS DE LABORATORIO"
                        elif tipo_detectado == TipoGrupoDocente.PRACTICA:
                            sesion_clonada.tipo = "PRÁCTICAS DE AULA"
                        else:
                            sesion_clonada.tipo = "TEORÍA"
                    
                    nuevas_sesiones.append(sesion_clonada)
            
            tabla.sesiones = nuevas_sesiones

        return horario_out

    def refinar_matching(self, db: Session, horario: HorarioTemporalOut) -> HorarioTemporalOut:
        """
        Solo actualiza los matches de asignaturas usando el nuevo motor.
        """
        asig_matcher = AsignaturaMatcher(db)
        
        # También usamos la inferencia inteligente aquí
        prog_id = asig_matcher.infer_program_id(horario.plan)

        for tabla in horario.horarios:
            curso_int = 0
            if tabla.curso:
                digits = "".join(filter(str.isdigit, str(tabla.curso)))
                if digits: curso_int = int(digits)

            for sesion in tabla.sesiones:
                if not sesion.asignatura: continue
                
                asig_obj, metodo, score = asig_matcher.match(
                    texto_raw=sesion.asignatura, 
                    prog_id=prog_id,      
                    curso=curso_int
                )
                
                sesion.match_confidence = score
                sesion.match_status = metodo
                if asig_obj:
                    sesion.asignatura_id = asig_obj.id
                    sesion.asignatura_sugerida = asig_obj.nombre
                else:
                    sesion.asignatura_sugerida = None
                    sesion.asignatura_id = None
                    
        return horario
    
    def confirmar_horario(
        self,
        db: Session,
        data: HorarioTemporalConfirmIn,
    ) -> HorarioConfirmResponse:
        """
        Persiste el horario validado usando estrategia 'Wipe & Replace'.
        
        Garantiza la integridad de los datos mediante:
        1. Transacción Atómica: Un único commit al final.
        2. Limpieza Profunda (Wipe): Borra grupos previos de las asignaturas afectadas para evitar "zombis".
        3. Reemplazo (Replace): Crea la nueva estructura de grupos y sesiones.
        """
        
        # --- 1. VALIDACIÓN DE CONTEXTO ---
        nombre_plan = (data.plan or "").strip()
        if not nombre_plan and data.titulo:
            nombre_plan = data.titulo.split('-')[0].strip()

        programa_db = db.query(Programa).filter(Programa.nombre.ilike(nombre_plan)).first()
        if not programa_db:
            raise HTTPException(
                status_code=400, 
                detail=f"ERROR: El plan de estudios '{nombre_plan}' no existe en la base de datos."
            )

        # --- 2. APRENDIZAJE DE ALIAS ---
        # Registramos nuevos alias detectados (sin hacer commit aún)
        self._procesar_aprendizaje_alias(db, data)

        # --- 3. NORMALIZACIÓN ---
        # Convertimos el input del frontend a estructuras normalizadas
        parsed_for_normalizer = build_parsing_result_for_normalization(data)
        
        # Parche de seguridad: asegurar que 'pagina' existe
        if hasattr(parsed_for_normalizer, 'horarios'):
            for idx, h_tabla in enumerate(parsed_for_normalizer.horarios):
                if not hasattr(h_tabla, 'pagina'):
                    setattr(h_tabla, 'pagina', idx + 1)
        
        normalized_tablas = horario_data_normalizer.normalize_horarios(parsed_for_normalizer)
        
        # --- 4. TRANSACCIÓN PRINCIPAL (WIPE & REPLACE) ---
        stats = {"grupos_creados": 0, "sesiones_creadas": 0}
        grupos_resultado_map: Dict[int, GrupoDocenteOut] = {}
        sesiones_resultado: List[SesionOut] = []
        
        # Caches locales para optimizar la transacción
        asignatura_cache: Dict[str, Asignatura] = {}
        mencion_cache: Dict[str, Mencion] = {}
        
        # Cache de Grupos Creados EN ESTA TRANSACCIÓN para evitar duplicados
        # Clave: (asignatura_id, codigo_grupo) -> Objeto GrupoDocente
        grupos_nuevos_cache: Dict[Tuple[int, str], GrupoDocente] = {}
        
        # Set para controlar qué asignaturas ya han sido limpiadas (Wiped)
        asignaturas_limpiadas: Set[int] = set()

        # Instancia del matcher para aulas desconocidas
        aula_matcher_srv = AulaMatcher(db)

        try:
            for tabla in normalized_tablas:
                
                # 4.1 Gestión de Mención (Get or Create)
                mencion_db: Optional[Mencion] = None
                if tabla.mencion:
                    m_nombre = tabla.mencion.replace("Mención en ", "").replace("MENCION EN ", "").strip()
                    
                    if m_nombre in mencion_cache:
                        mencion_db = mencion_cache[m_nombre]
                    else:
                        mencion_db = db.query(Mencion).filter(
                            Mencion.programa_id == programa_db.id,
                            Mencion.nombre.ilike(m_nombre)
                        ).first()
                        
                        if not mencion_db:
                            mencion_db = Mencion(programa_id=programa_db.id, nombre=m_nombre, activo=True)
                            db.add(mencion_db)
                            db.flush() # Necesario para obtener ID, pero no commitea
                        
                        mencion_cache[m_nombre] = mencion_db

                for sesion_norm in (tabla.sesiones or []):
                    
                    # 4.2 Resolver Asignatura
                    nombre_asig = sesion_norm.asignatura_nombre.strip()
                    if not nombre_asig: continue

                    if nombre_asig in asignatura_cache:
                        asignatura = asignatura_cache[nombre_asig]
                    else:
                        # Búsqueda robusta: Nombre exacto o Alias
                        asignatura = db.query(Asignatura).filter(Asignatura.nombre.ilike(nombre_asig)).first()
                        if not asignatura:
                            alias_db = db.query(AsignaturaAlias).filter(AsignaturaAlias.alias.ilike(nombre_asig)).first()
                            if alias_db:
                                asignatura = alias_db.asignatura
                        
                        if not asignatura:
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Asignatura desconocida: '{nombre_asig}'. Verifica el catálogo."
                            )
                        asignatura_cache[nombre_asig] = asignatura

                    # 4.3 ESTRATEGIA WIPE: Limpieza preventiva
                    # Si es la primera vez que vemos esta asignatura en este proceso, borramos sus datos viejos.
                    if asignatura.id not in asignaturas_limpiadas:
                        #
                        grupo_docente_repository.delete_by_asignatura(db, asignatura.id)
                        asignaturas_limpiadas.add(asignatura.id)
                        logger.info(f"🧹 WIPE: Eliminados grupos previos de Asignatura ID {asignatura.id}")

                    # 4.4 Vincular Mención (si aplica)
                    if mencion_db:
                        link_existe = db.query(AsignaturaMencion).filter_by(
                            asignatura_id=asignatura.id, mencion_id=mencion_db.id
                        ).first()
                        if not link_existe:
                            db.add(AsignaturaMencion(asignatura_id=asignatura.id, mencion_id=mencion_db.id))
                            # No flush necesario aquí, se guardará al final

                    # 4.5 Gestión de Grupo (REPLACE)
                    codigo_grupo = sesion_norm.grupo_codigo.strip().upper() or "UNICO"
                    grupo_key = (asignatura.id, codigo_grupo)
                    
                    # Verificamos si ya hemos creado este grupo EN ESTA CARGA
                    if grupo_key in grupos_nuevos_cache:
                        grupo_db = grupos_nuevos_cache[grupo_key]
                    else:
                        # Creamos el grupo nuevo (ya que hicimos Wipe, no existen colisiones en BD)
                        grupo_in = GrupoDocenteCreate(
                            asignatura_id=asignatura.id,
                            codigo=codigo_grupo,
                            tipo=sesion_norm.tipo_grupo,
                            curso=tabla.curso,
                            turno=None
                        )
                        grupo_out = grupo_docente_service.create(db, grupo_in)
                        
                        # Recargamos el objeto ORM para tenerlo disponible en la sesión
                        grupo_db = db.query(GrupoDocente).filter(GrupoDocente.id == grupo_out.id).first()
                        grupos_nuevos_cache[grupo_key] = grupo_db
                        stats["grupos_creados"] += 1

                    if grupo_db.id not in grupos_resultado_map:
                        grupos_resultado_map[grupo_db.id] = GrupoDocenteOut.model_validate(grupo_db)

                    # 4.6 Resolver Aula
                    nombre_aula = sesion_norm.aula_nombre.strip()
                    # Intento 1: Búsqueda directa (rápida)
                    aula_db = aula_repository.get_by_nombre(db, nombre_aula) or \
                              aula_repository.get_by_codigo(db, nombre_aula)
                    
                    if not aula_db:
                        # Intento 2: Matcher inteligente
                        aula_db = aula_matcher_srv.match(nombre_aula)
                        
                        if not aula_db:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Aula no encontrada: '{nombre_aula}'."
                            )

                    # 4.7 Crear Sesión
                    dia_str_norm = sesion_norm.dia_semana.upper().replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
                    dia_enum = TEXTO_A_DIA_ENUM.get(dia_str_norm)
                    if not dia_enum: continue

                    sesion_in = SesionCreate(
                        grupo_docente_id=grupo_db.id,
                        aula_id=aula_db.id,
                        modalidad=sesion_norm.modalidad,
                        tipo_recurrencia=sesion_norm.tipo_recurrencia,
                        dia_semana=dia_enum,
                        hora_inicio=sesion_norm.hora_inicio,
                        hora_fin=sesion_norm.hora_fin,
                        profesores=[]
                    )
                    
                    # Delegamos la creación al servicio de sesión
                    try:
                        res_servicio = sesion_service.create(db, sesion_in)
                        sesiones_resultado.append(res_servicio.sesion)
                        stats["sesiones_creadas"] += 1
                    except Exception as e:
                        logger.error(f"Error creando sesión: {e}")
                        raise HTTPException(status_code=500, detail=f"Error interno al guardar sesión: {str(e)}")

            # --- 5. COMMIT FINAL (Todo o Nada) ---
            db.commit()
            logger.info(f"✅ Transacción completada exitosamente. Stats: {stats}")

        except Exception as e:
            # En caso de cualquier error, revertimos TODO (grupos borrados, menciones, etc.)
            db.rollback()
            if isinstance(e, HTTPException): raise e
            logger.error(f"❌ Error fatal en persistencia (Rollback ejecutado): {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error guardando horario: {str(e)}")

        return HorarioConfirmResponse(
            grupos=list(grupos_resultado_map.values()),
            sesiones=sesiones_resultado,
            created_entities=stats,
            warnings=[],
            errors=[]
        )

    def _procesar_aprendizaje_alias(self, db: Session, data: HorarioTemporalConfirmIn):
        """
        Detecta correcciones manuales del usuario y registra nuevos alias.
        Se ejecuta dentro de la transacción principal (sin commit propio).
        """
        aliases_to_create: Dict[str, int] = {}
        
        for tabla in data.horarios:
            for sesion in tabla.sesiones:
                texto_original = (sesion.texto_original or sesion.asignatura or "").strip()
                # Usamos el ID de la asignatura confirmada (bien sea por match automático o selección manual)
                asignatura_id = sesion.asignatura_id
                
                if asignatura_id and texto_original:
                    # Validar si el texto original ya es el nombre oficial
                    asig_db = db.query(Asignatura).get(asignatura_id)
                    if asig_db and asig_db.nombre.upper() == texto_original.upper():
                        continue

                    # Preparamos para creación si no existe
                    aliases_to_create[texto_original] = asignatura_id

        # Upsert manual de alias
        for alias_texto, asig_id in aliases_to_create.items():
            alias_existe = db.query(AsignaturaAlias).filter_by(
                asignatura_id=asig_id, 
                alias=alias_texto
            ).first()
            
            if not alias_existe:
                logger.info(f"🧠 APRENDIENDO: '{alias_texto}' es alias de ID {asig_id}")
                nuevo_alias = AsignaturaAlias(
                    asignatura_id=asig_id,
                    alias=alias_texto,
                    origen="AUTO_CONFIRMACION",
                    veces_usado=1
                )
                db.add(nuevo_alias)
        
        # Flush para que los alias estén disponibles en la misma transacción si fuera necesario
        db.flush()