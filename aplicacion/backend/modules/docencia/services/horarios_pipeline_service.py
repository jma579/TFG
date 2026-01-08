from __future__ import annotations

from typing import Dict, List, Optional, Union
from pathlib import Path
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import logging

from database.models import Asignatura, Aula
from modules.docencia.schemas.horarios import (
    HorarioTemporalOut, HorarioTemporalConfirmIn, HorarioConfirmResponse
)
from modules.docencia.schemas.grupo_docente import (
    GrupoDocenteCreate,
    GrupoDocenteOut,
)
from modules.docencia.schemas.sesion import SesionCreate, SesionOut
# ✅ USAMOS LOS SERVICIOS OFICIALES
from modules.docencia.services.grupo_docente_service import grupo_docente_service
from modules.docencia.services.sesion_service import sesion_service

from core.extraccion.horarios.extractor.extractor import HorarioExtractor
from core.extraccion.horarios.parser.parser import HorarioParser

from core.extraccion.horarios.normalizador.normalize import horario_data_normalizer
from modules.docencia.services.horarios_normalization_models import (
    build_parsing_result_for_normalization,
)

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

from modules.catalogo.services.asignatura_matcher import AsignaturaMatcher
from modules.recursos.services.aula_matcher import aula_matcher
# ✅ Importamos DiaSemana para el mapeo correcto
from constants.enums import TipoGrupoDocente, DiaSemana


logger = logging.getLogger(__name__)

# =============================================================================
# MAPEO ESTÁTICO DE TEXTO -> ENUM
# Soluciona el error "unable to parse string as an integer" asegurando que
# al servicio le llega el objeto Enum correcto, no un string.
# =============================================================================
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
    """Servicio de orquestación del flujo de horarios."""

    def __init__(self) -> None:
        self._extractor = HorarioExtractor()
        self._parser = HorarioParser()

    def extraer_horario(self, db: Session, pdf_path: Union[str, Path]) -> HorarioTemporalOut:
        # 1) Extracción y Parsing
        path_str = str(pdf_path)
        extraction_result = self._extractor.extract(path_str)
        parsed_dict = self._parser.parse(extraction_result)
        horario_out = HorarioTemporalOut(**parsed_dict)

        # 2) Enriquecimiento
        matcher = AsignaturaMatcher(db)
        contexto_plan = horario_out.plan or horario_out.titulo or ""
        texto_para_periodo = f"{horario_out.periodo or ''} {horario_out.titulo or ''}"

        for tabla in horario_out.horarios:
            contexto_curso = tabla.curso or ""
            nuevas_sesiones = []
            
            for sesion in tabla.sesiones:
                # A) Match de Asignatura
                if sesion.asignatura:
                    asig_obj, metodo, score = matcher.match(
                        texto_sucio=sesion.asignatura, 
                        plan_context=contexto_plan,
                        periodo_context=texto_para_periodo,
                        curso_context=contexto_curso
                    )
                    sesion.match_confidence = score
                    sesion.match_status = metodo
                    if asig_obj:
                        sesion.asignatura_sugerida = asig_obj.nombre

                # B) División de Grupos
                grupos_detectados = horario_data_normalizer.detectar_y_dividir_grupos(sesion.grupo)
                
                for grupo_item in grupos_detectados:
                    sesion_clonada = sesion.model_copy()
                    
                    # C) Match de Aula (Extractor)
                    texto_aula_original = sesion_clonada.aula or ""
                    match_aula = aula_matcher.match(db, texto_aula_original)
                    
                    if match_aula:
                        sesion_clonada.aula = match_aula.nombre
                    else:
                        sesion_clonada.aula = "POR DETERMINAR"

                    # D) Inferencia de Tipo
                    aula_para_inferencia = sesion_clonada.aula
                    aula_norm = horario_data_normalizer._normalize_aula(aula_para_inferencia)
                    
                    grupo_limpio, tipo_detectado = horario_data_normalizer.infer_grupo_y_tipo(grupo_item, aula_norm)
                    
                    sesion_clonada.grupo = grupo_limpio
                    
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
        matcher = AsignaturaMatcher(db)
        contexto_plan = horario.plan or horario.titulo or ""
        texto_para_periodo = f"{horario.periodo or ''} {horario.titulo or ''}"

        for tabla in horario.horarios:
            contexto_curso = tabla.curso or ""
            for sesion in tabla.sesiones:
                if not sesion.asignatura:
                    continue
                asig_obj, metodo, score = matcher.match(
                    texto_sucio=sesion.asignatura, 
                    plan_context=contexto_plan,      
                    periodo_context=texto_para_periodo,
                    curso_context=contexto_curso
                )
                sesion.match_confidence = score
                sesion.match_status = metodo
                if asig_obj:
                    sesion.asignatura_sugerida = asig_obj.nombre
                else:
                    sesion.asignatura_sugerida = None
        return horario

    def confirmar_horario(
        self,
        db: Session,
        data: HorarioTemporalConfirmIn,
    ) -> HorarioConfirmResponse:
        
        # --- 1. GATEKEEPER Y VALIDACIONES INICIALES ---
        nombre_plan = (data.plan or "").strip()
        if not nombre_plan and data.titulo:
            parts = data.titulo.split('-')
            if len(parts) > 0:
                nombre_plan = parts[0].strip()

        programa_db = db.query(Programa).filter(Programa.nombre.ilike(nombre_plan)).first()
        if not programa_db:
            raise HTTPException(
                status_code=400, 
                detail=f"ERROR BLOQUEANTE: El plan de estudios '{nombre_plan}' no existe en la base de datos."
            )

        # --- 2. AUTO-APRENDIZAJE DE ALIASES (Auto-Learning) ---
        aliases_procesados_request = set()
        for tabla in data.horarios:
            for sesion in tabla.sesiones:
                texto_original = (sesion.asignatura or "").strip()
                texto_sugerido = (sesion.asignatura_sugerida or "").strip()

                if texto_sugerido and texto_original and texto_original != texto_sugerido:
                    clave_unica = (texto_original, texto_sugerido)
                    if clave_unica in aliases_procesados_request: continue 

                    asig_padre = db.query(Asignatura).filter(Asignatura.nombre == texto_sugerido).first()
                    if asig_padre:
                        alias_existente = db.query(AsignaturaAlias).filter_by(alias=texto_original, asignatura_id=asig_padre.id).first()
                        if not alias_existente:
                            nuevo_alias = AsignaturaAlias(
                                asignatura_id=asig_padre.id,
                                alias=texto_original,
                                origen="AUTO_CONFIRMACION",
                                veces_usado=1
                            )
                            db.add(nuevo_alias)
                            logger.info(f"🎓 APRENDIZAJE: Nuevo alias creado: '{texto_original}' -> '{texto_sugerido}'")
                        else:
                            alias_existente.veces_usado += 1
                            db.add(alias_existente)
                    aliases_procesados_request.add(clave_unica)
        
        db.flush()

        # --- 3. APLICAR SUGERENCIAS (CORRECCIÓN DE DATOS) ---
        for tabla in data.horarios:
            for sesion in tabla.sesiones:
                if sesion.asignatura_sugerida:
                    sesion.asignatura = sesion.asignatura_sugerida

        # --- 4. NORMALIZACIÓN ---
        parsed_for_normalizer = build_parsing_result_for_normalization(data)
        normalized_tablas = horario_data_normalizer.normalize_horarios(parsed_for_normalizer)
        
        # Validaciones de integridad antes de intentar guardar
        for idx_t, tabla in enumerate(normalized_tablas):
            for idx_s, ses in enumerate(tabla.sesiones or []):
                nombre_sesion = ses.asignatura_nombre or f"Sesión {idx_s+1}"
                if not ses.asignatura_nombre:
                    raise HTTPException(status_code=400, detail=f"ERROR BLOQUEANTE: Sesión sin asignatura en {ses.dia_semana}.")
                if not ses.aula_nombre or ses.aula_nombre == "POR DETERMINAR":
                    raise HTTPException(status_code=400, detail=f"ERROR BLOQUEANTE: Asignatura '{nombre_sesion}' tiene aula 'POR DETERMINAR'.")

        # --- 5. PERSISTENCIA USANDO SERVICIOS (CORE LOGIC) ---
        grupos_resultado: Dict[int, GrupoDocenteOut] = {}
        sesiones_resultado: List[SesionOut] = []
        
        grupos_creados = 0
        grupos_reutilizados = 0
        sesiones_creadas = 0
        
        asignatura_cache: Dict[str, Asignatura] = {}
        aula_cache: Dict[str, Aula] = {}
        mencion_cache: Dict[str, Optional[Mencion]] = {}

        # Precarga de menciones del programa para evitar queries repetidas
        for m in programa_db.menciones:
            mencion_cache[m.nombre.upper()] = m

        try:
            for tabla in normalized_tablas:
                
                # Gestión de Mención del Bloque
                mencion_bloque_db: Optional[Mencion] = None
                if tabla.mencion:
                    m_limpia = tabla.mencion.strip().upper().replace("MENCIÓN EN ", "").replace("MENCION EN ", "").strip()
                    if m_limpia in mencion_cache:
                        mencion_bloque_db = mencion_cache[m_limpia]

                for sesion_norm in (tabla.sesiones or []):
                    
                    # 5.1 Asignatura
                    asig_name = sesion_norm.asignatura_nombre.strip()
                    if asig_name in asignatura_cache:
                        asignatura = asignatura_cache[asig_name]
                    else:
                        asignatura = db.query(Asignatura).filter(Asignatura.nombre.ilike(asig_name)).first()
                        if not asignatura:
                            raise HTTPException(status_code=400, detail=f"Asignatura no encontrada en BD: {asig_name}")
                        asignatura_cache[asig_name] = asignatura

                    # Vincular Mención (si aplica)
                    if mencion_bloque_db:
                        exists_rel = db.query(AsignaturaMencion).filter_by(
                            asignatura_id=asignatura.id,
                            mencion_id=mencion_bloque_db.id
                        ).first()
                        if not exists_rel:
                            new_rel = AsignaturaMencion(
                                asignatura_id=asignatura.id,
                                mencion_id=mencion_bloque_db.id
                            )
                            db.add(new_rel)
                            db.flush()

                    # 5.2 Grupo Docente (Usando Service)
                    grupo_cod = sesion_norm.grupo_codigo.strip().upper() or "UNICO"
                    
                    # Verificar existencia para evitar error 409 del service si ya existe
                    grupo_db = db.query(GrupoDocente).filter_by(
                        asignatura_id=asignatura.id, 
                        codigo=grupo_cod
                    ).first()

                    if not grupo_db:
                        grupo_in = GrupoDocenteCreate(
                            asignatura_id=asignatura.id,
                            codigo=grupo_cod,
                            tipo=sesion_norm.tipo_grupo,
                            curso=tabla.curso,
                            turno=None
                        )
                        # Usamos el servicio oficial para crear
                        grupo_out = grupo_docente_service.create(db, grupo_in)
                        
                        # Recuperamos el objeto ORM fresco
                        grupo_db = db.query(GrupoDocente).filter(GrupoDocente.id == grupo_out.id).first()
                        
                        grupos_creados += 1
                        if grupo_db.id not in grupos_resultado:
                            grupos_resultado[grupo_db.id] = grupo_out
                    else:
                        grupos_reutilizados += 1
                        if grupo_db.id not in grupos_resultado:
                            grupos_resultado[grupo_db.id] = GrupoDocenteOut.model_validate(grupo_db)

                    # 5.3 Aula (Con Fuzzy Matcher)
                    aula_name = sesion_norm.aula_nombre.strip()
                    if aula_name in aula_cache:
                        aula = aula_cache[aula_name]
                    else:
                        aula = db.query(Aula).filter(Aula.nombre.ilike(aula_name)).first()
                        if not aula:
                            aula = aula_matcher.match(db, aula_name)

                        if not aula:
                            raise HTTPException(status_code=400, detail=f"Aula no encontrada en BD: {aula_name}")
                        
                        aula_cache[aula_name] = aula

                    # 5.4 Crear Sesión USANDO SERVICIO
                    # CORRECCIÓN DE TIPOS: Convertir string a Enum explícitamente
                    dia_limpio = sesion_norm.dia_semana.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
                    dia_enum = TEXTO_A_DIA_ENUM.get(dia_limpio)

                    if not dia_enum:
                        logger.error(f"Error convirtiendo día: '{sesion_norm.dia_semana}' no es válido.")
                        raise HTTPException(status_code=400, detail=f"Día de la semana inválido: {sesion_norm.dia_semana}")

                    # DTO para el servicio
                    sesion_in = SesionCreate(
                        grupo_docente_id=grupo_db.id,
                        aula_id=aula.id,
                        modalidad=sesion_norm.modalidad,
                        tipo_recurrencia=sesion_norm.tipo_recurrencia,
                        dia_semana=dia_enum,  # ✅ Pasamos el Enum, no el string
                        hora_inicio=sesion_norm.hora_inicio,
                        hora_fin=sesion_norm.hora_fin,
                        profesores=[]
                    )
                    
                    # Llamada al servicio
                    # Devuelve SesionWithConflictosOut (sesion + conflictos)
                    resultado_servicio = sesion_service.create(db, sesion_in)
                    
                    # Extraemos la sesión limpia para la respuesta
                    sesiones_resultado.append(resultado_servicio.sesion)
                    sesiones_creadas += 1

            # Commit final de todas las operaciones
            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Error confirmando horario: {e}")
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=500, detail=f"Error interno guardando horario: {str(e)}")

        return HorarioConfirmResponse(
            grupos=list(grupos_resultado.values()),
            sesiones=sesiones_resultado,
            created_entities={
                "grupos_creados": grupos_creados,
                "grupos_reutilizados": grupos_reutilizados,
                "sesiones_creadas": sesiones_creadas,
            },
            warnings=[],
            errors=[]
        )