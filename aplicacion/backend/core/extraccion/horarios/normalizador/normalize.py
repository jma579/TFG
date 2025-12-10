"""
Normalización de datos extraídos de horarios académicos.
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple, Dict
from datetime import time

# Entidades del Pipeline
from core.extraccion.horarios.entities import (
    ParsingResult,
    Horario as ParsedHorario,
    Sesion as ParsedSesion,
    NormalizedHorarioTablaData,
    NormalizedSesionHorarioData,
)

# Enums del Dominio
from constants.enums import (
    DiaSemana,
    Periodo,
    TipoGrupoDocente,
    TipoAula,
    ModalidadSesion,
    TipoRecurrencia
)

# Reglas de normalización (Importadas)
from core.extraccion.horarios.normalizador.normalization_rules import (
    DIA_SEMANA_MAP,
    PERIODO_MAP,
    CURSO_MAP,
    KEYWORDS_AULA,
    CURSO_MIN,
    CURSO_MAX
)

logger = logging.getLogger(__name__)


class HorarioDataNormalizer:
    """
    Normalizador de datos de horarios.
    Convierte ParsingResult -> List[NormalizedHorarioTablaData].
    """

    def normalize_horarios(self, parsed: ParsingResult) -> List[NormalizedHorarioTablaData]:
        resultados: List[NormalizedHorarioTablaData] = []
        
        programa_global = self._normalize_nombre(parsed.titulo)
        periodo_global = self._infer_periodo_from_text(parsed.titulo)

        for horario in parsed.horarios:
            try:
                normalizado = self._normalize_tabla(horario, programa_global, periodo_global)
                
                if normalizado and normalizado.sesiones:
                    resultados.append(normalizado)
                else:
                    logger.warning(f"Tabla descartada (sin sesiones válidas): Pág {horario.pagina}")
                    
            except Exception as e:
                logger.error(f"Error normalizando tabla Pág {horario.pagina}: {e}")
                continue

        return resultados

    def _normalize_tabla(
        self, 
        horario: ParsedHorario, 
        programa_fallback: str, 
        periodo_fallback: Optional[Periodo]
    ) -> Optional[NormalizedHorarioTablaData]:
        
        # 1. Curso
        curso_int = self._parse_curso(horario.curso)
        if not curso_int:
            logger.warning(f"No se pudo determinar el curso para la tabla en pág {horario.pagina}")
            return None

        # 2. Periodo
        periodo_enum = periodo_fallback
        if horario.periodo:
            periodo_local = self._infer_periodo_from_text(horario.periodo)
            if periodo_local:
                periodo_enum = periodo_local
        
        if not periodo_enum:
            periodo_enum = Periodo.PRIMER_CUATRIMESTRE 
            logger.warning(f"Periodo no detectado en pág {horario.pagina}, usando default: {periodo_enum}")

        # 3. Mención
        mencion_norm = self._normalize_nombre(horario.mencion) if horario.mencion else None

        # 4. Sesiones
        sesiones_norm: List[NormalizedSesionHorarioData] = []
        for sesion in horario.sesiones:
            try:
                s_norm = self._normalize_sesion(sesion)
                if s_norm:
                    sesiones_norm.append(s_norm)
            except Exception as e:
                logger.debug(f"Sesión descartada en pág {horario.pagina}: {e}")
                continue

        return NormalizedHorarioTablaData(
            programa_nombre=programa_fallback,
            curso=curso_int,
            periodo=periodo_enum,
            mencion=mencion_norm,
            sesiones=sesiones_norm
        )

    def _normalize_sesion(self, sesion: ParsedSesion) -> Optional[NormalizedSesionHorarioData]:
        if not sesion.asignatura or sesion.asignatura == "DESCONOCIDA":
            return None
        if "(*)" in sesion.asignatura:
            return None

        asignatura_nom = self._normalize_nombre(sesion.asignatura)
        
        dia_enum = self._map_dia_semana(sesion.dia)
        if not dia_enum: return None

        aula_nom = self._normalize_aula(sesion.aula)
        aula_tipo = self._infer_aula_tipo(aula_nom)

        grupo_cod, tipo_grupo = self._infer_grupo_y_tipo(sesion.grupo, sesion.tipo, aula_nom)

        return NormalizedSesionHorarioData(
            asignatura_nombre=asignatura_nom,
            grupo_codigo=grupo_cod,
            tipo_grupo=tipo_grupo,
            dia_semana=dia_enum,
            hora_inicio=sesion.hora_inicio,
            hora_fin=sesion.hora_fin,
            aula_nombre=aula_nom,
            aula_tipo=aula_tipo,
            modalidad=ModalidadSesion.PRESENCIAL,
            tipo_recurrencia=TipoRecurrencia.SEMANAL
        )

    # --- Helpers ---

    def _normalize_nombre(self, text: str) -> str:
        if not text: return ""
        clean = re.sub(r'\s+', ' ', text).strip()
        return clean.title()

    def _normalize_aula(self, text: str) -> str:
        if not text or text == "POR DETERMINAR":
            return "POR DETERMINAR"
        clean = re.sub(r'\s+', ' ', text).strip().upper()
        return clean

    def _map_dia_semana(self, dia_str: str) -> Optional[DiaSemana]:
        if not dia_str: return None
        norm = dia_str.upper().replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O')
        return DIA_SEMANA_MAP.get(norm)

    def _infer_periodo_from_text(self, text: str) -> Optional[Periodo]:
        if not text: return None
        norm = text.upper()
        for key, val in PERIODO_MAP.items():
            if key in norm:
                return val
        return None

    def _parse_curso(self, curso_str: str) -> Optional[int]:
        if not curso_str: return None
        norm = curso_str.upper()
        for key, val in CURSO_MAP.items():
            if re.search(r'\b' + re.escape(key) + r'\b', norm) or key == norm:
                return val
        return None

    def _infer_aula_tipo(self, aula_nombre: str) -> TipoAula:
        if aula_nombre == "POR DETERMINAR":
            return TipoAula.TEORICA 
        
        target = aula_nombre.upper()
        for tipo, keywords in KEYWORDS_AULA.items():
            for kw in keywords:
                if kw in target:
                    return tipo
        return TipoAula.TEORICA

    def _infer_grupo_y_tipo(self, grupo_str: Optional[str], tipo_parsed: Optional[str], aula_str: str) -> Tuple[str, TipoGrupoDocente]:
        grupo_limpio = (grupo_str or "UNICO").strip().upper()
        tipo_final = TipoGrupoDocente.TEORIA
        
        es_practica = False
        es_lab = False
        
        if tipo_parsed == 'PRÁCTICA':
            es_practica = True
        
        if any(x in grupo_limpio for x in ['PL', 'LAB', 'PRACTICA']):
            es_practica = True
            if 'LAB' in grupo_limpio or 'PL' in grupo_limpio:
                es_lab = True
        elif 'PA' in grupo_limpio:
            es_practica = True

        if 'LAB' in aula_str or 'LSC' in aula_str:
            es_lab = True

        if es_lab:
            tipo_final = TipoGrupoDocente.LABORATORIO
        elif es_practica:
            tipo_final = TipoGrupoDocente.PRACTICA
            
        return grupo_limpio, tipo_final


# Instancia singleton
horario_data_normalizer = HorarioDataNormalizer()