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
        
        # 2. Periodo
        periodo_enum = periodo_fallback
        if horario.periodo:
            periodo_local = self._infer_periodo_from_text(horario.periodo)
            if periodo_local:
                periodo_enum = periodo_local
        
        if not periodo_enum:
            periodo_enum = Periodo.PRIMER_CUATRIMESTRE 

        # 3. Mención
        mencion_norm = self._normalize_nombre(horario.mencion) if horario.mencion else None

        # 4. Sesiones (EXPANSIÓN DE GRUPOS)
        # Aquí también aplicamos la división para el guardado en BD
        sesiones_norm: List[NormalizedSesionHorarioData] = []
        for sesion in horario.sesiones:
            try:
                # Paso previo: Detectar si hay múltiples grupos
                grupos_detectados = self.detectar_y_dividir_grupos(sesion.grupo)
                
                for grupo_individual in grupos_detectados:
                    # Creamos una copia virtual de la sesión para cada grupo
                    # Ojo: Parseamos la sesión original pero inyectando el grupo individual
                    sesion_clonada = sesion.model_copy(update={"grupo": grupo_individual})
                    
                    s_norm = self._normalize_sesion(sesion_clonada)
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

        # Inferencia
        grupo_cod, tipo_grupo = self.infer_grupo_y_tipo(sesion.grupo, aula_nom)

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

    def detectar_y_dividir_grupos(self, grupo_raw: Optional[str]) -> List[str]:
        """
        Divide un string de grupo compuesto en una lista de grupos individuales.
        Ejemplos:
        - "PA1yPA2" -> ["PA1", "PA2"]
        - "Grupo 1 y 2" -> ["Grupo 1", "2"]
        - "PL1, PL2" -> ["PL1", "PL2"]
        - "AULA 14" -> ["AULA 14"]
        """
        if not grupo_raw:
            return [""] # Retornamos uno vacío para que el bucle procese la sesión sin grupo

        text = grupo_raw.strip()
        
        # Regex Explicación:
        # 1. \s*[,/&+]\s* -> Separadores explícitos: coma, barra, ampersand, más (+).
        # 2. \s+(?:y|e)\s+     -> Conjunción separada por espacios: " y ", " e ".
        # 3. y(?=(?:PA|PL|Gr|G\.|[0-9])) -> La "y" pegada (caso PA1yPA2).
        #    Solo separa si lo que sigue parece un inicio de grupo (PA, PL, Gr, G., o un número).
        
        pattern = r'\s*[,/&+]\s*|\s+(?:y|e)\s+|y(?=(?:PA|PL|GR|G\.|[0-9]))'
        
        partes = re.split(pattern, text, flags=re.IGNORECASE)
        
        # Filtramos vacíos y limpiamos espacios
        return [p.strip() for p in partes if p.strip()]

    def infer_grupo_y_tipo(self, grupo_str: Optional[str], aula_str: str) -> Tuple[str, TipoGrupoDocente]:
        """
        Deduce el tipo y limpia el código de un UNICO grupo.
        """
        grupo_raw = (grupo_str or "").strip()
        
        # 1. LIMPIEZA: "Grupo PL 3" -> "PL3"
        grupo_limpio = re.sub(r'^(GRUPO|GR\.|G\.)\s*', '', grupo_raw, flags=re.IGNORECASE)
        grupo_limpio = grupo_limpio.replace(" ", "").strip()
        
        grupo_upper = grupo_limpio.upper()
        aula_upper = (aula_str or "").strip().upper()
        
        # CASO 0: Sin grupo
        if not grupo_limpio:
            return "", TipoGrupoDocente.TEORIA

        # CASO 1: PA
        if "PA" in grupo_upper:
            return grupo_limpio, TipoGrupoDocente.PRACTICA

        # Preparar entorno Lab
        keywords_lab = KEYWORDS_AULA.get(TipoAula.LABORATORIO, []) + KEYWORDS_AULA.get(TipoAula.INFORMATICA, [])
        es_entorno_lab = any(kw in aula_upper for kw in keywords_lab)

        # CASO 2: Entorno Lab
        if es_entorno_lab:
            return grupo_limpio, TipoGrupoDocente.LABORATORIO
        
        # CASO 3: Entorno Normal + PL
        if "PL" in grupo_upper:
            return grupo_limpio, TipoGrupoDocente.LABORATORIO

        # CASO 4: Teoría
        return grupo_limpio, TipoGrupoDocente.TEORIA


# Instancia singleton
horario_data_normalizer = HorarioDataNormalizer()