"""
Normalización de datos extraídos de horarios académicos.
"""

import re
import logging
from typing import List, Optional, Tuple
import copy

from core.extraccion.horarios.entities import (
    ParsingResult,
    Horario as ParsedHorario,
    Sesion as ParsedSesion,
    NormalizedHorarioTablaData,
    NormalizedSesionHorarioData,
)

from constants.enums import (
    DiaSemana,
    Periodo,
    TipoGrupoDocente,
    TipoAula,
    ModalidadSesion,
    TipoRecurrencia
)

from core.extraccion.horarios.normalizador.normalization_rules import (
    DIA_SEMANA_MAP,
    PERIODO_MAP,
    CURSO_MAP,
    KEYWORDS_AULA,
)

logger = logging.getLogger(__name__)


class HorarioDataNormalizer:
    """
    Normalizador de datos de horarios.
    Toma los datos parseados (ParsingResult) y los transforma en estructuras normalizadas"""

    def normalize_horarios(self, parsed: ParsingResult) -> List[NormalizedHorarioTablaData]:
        """Normaliza el resultado completo de la extracción de horarios."""
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
                pag = getattr(horario, 'pagina', '?')
                logger.error(f"Error normalizando tabla Pág {pag}: {e}")
                continue

        return resultados

    def _normalize_tabla(
        self, 
        horario: ParsedHorario, 
        programa_fallback: str, 
        periodo_fallback: Optional[Periodo]
    ) -> Optional[NormalizedHorarioTablaData]:
        """Normaliza una tabla de horario individual."""
        curso_int = self._parse_curso(horario.curso)
        
        periodo_enum = periodo_fallback
        if horario.periodo:
            periodo_local = self._infer_periodo_from_text(horario.periodo)
            if periodo_local:
                periodo_enum = periodo_local
        
        if not periodo_enum:
            periodo_enum = Periodo.PRIMER_CUATRIMESTRE 

        mencion_norm = self._normalize_nombre(horario.mencion) if horario.mencion else None

        sesiones_norm: List[NormalizedSesionHorarioData] = []
        for sesion in horario.sesiones:
            try:
                grupos_detectados = self.detectar_y_dividir_grupos(sesion.grupo)
                
                for grupo_individual in grupos_detectados:
                    sesion_clonada = copy.deepcopy(sesion)
                    sesion_clonada.grupo = grupo_individual
                    
                    s_norm = self._normalize_sesion(sesion_clonada)
                    if s_norm:
                        sesiones_norm.append(s_norm)
                        
            except Exception as e:
                pag = getattr(horario, 'pagina', '?')
                logger.debug(f"Sesión descartada en pág {pag}: {e}")
                continue

        return NormalizedHorarioTablaData(
            programa_nombre=programa_fallback,
            curso=curso_int,
            periodo=periodo_enum,
            mencion=mencion_norm,
            sesiones=sesiones_norm
        )

    def _normalize_sesion(self, sesion: ParsedSesion) -> Optional[NormalizedSesionHorarioData]:
        """Normaliza una sesión de horario individual respetando ediciones manuales."""
        if not sesion.asignatura or sesion.asignatura == "DESCONOCIDA":
            return None
        if "(*)" in sesion.asignatura:
            return None

        asignatura_nom = self._normalize_nombre(sesion.asignatura)
        
        dia_enum = self._map_dia_semana(sesion.dia)
        if not dia_enum: return None

        aula_nom = self._normalize_aula(sesion.aula)
        aula_tipo = self._infer_aula_tipo(aula_nom)

        tipo_manual_str = getattr(sesion, 'tipo', None) or getattr(sesion, 'tipo_grupo', None)
        tipo_manual_enum = self._parse_tipo_manual(tipo_manual_str)

        if tipo_manual_enum:
            grupo_cod = self._limpiar_codigo_grupo(sesion.grupo)
            tipo_grupo = tipo_manual_enum
        else:
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


    def _parse_tipo_manual(self, tipo_str: Optional[str]) -> Optional[TipoGrupoDocente]:
        """Traduce el string del frontend (ej. 'PRÁCTICAS DE LABORATORIO') al Enum interno."""
        if not tipo_str:
            return None
            
        tipo_upper = tipo_str.upper()
        if "LABORATORIO" in tipo_upper:
            return TipoGrupoDocente.LABORATORIO
        if "AULA" in tipo_upper or "PRACTICA" in tipo_upper or "PRÁCTICA" in tipo_upper:
            return TipoGrupoDocente.PRACTICA
        if "TEOR" in tipo_upper:
            return TipoGrupoDocente.TEORIA
            
        return None

    def _limpiar_codigo_grupo(self, grupo_str: Optional[str]) -> str:
        """Limpia el código de grupo (ej. 'Grupo 1' -> '1') sin inferir su tipo."""
        grupo_raw = (grupo_str or "").strip()
        grupo_limpio = re.sub(r'^(GRUPO|GR\.|G\.)\s*', '', grupo_raw, flags=re.IGNORECASE)
        return grupo_limpio.replace(" ", "").strip()

    def _normalize_nombre(self, text: str) -> str:
        """Normaliza un nombre de asignatura o programa."""
        if not text: return ""
        clean = re.sub(r'\s+', ' ', text).strip()
        return clean.title()

    def _normalize_aula(self, text: str) -> str:
        """Normaliza un nombre de aula."""
        if not text or text == "POR DETERMINAR":
            return "POR DETERMINAR"
        clean = re.sub(r'\s+', ' ', text).strip().upper()
        return clean

    def _map_dia_semana(self, dia_str: str) -> Optional[DiaSemana]:
        """Mapea un string a un valor de DiaSemana."""
        if not dia_str: return None
        norm = dia_str.upper().replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O')
        return DIA_SEMANA_MAP.get(norm)

    def _infer_periodo_from_text(self, text: str) -> Optional[Periodo]:
        """Intenta inferir el periodo académico a partir de un texto dado."""
        if not text: return None
        norm = text.upper()
        for key, val in PERIODO_MAP.items():
            if key in norm:
                return val
        return None

    def _parse_curso(self, curso_str: str) -> Optional[int]:
        """Intenta parsear el curso a un entero, usando reglas de normalización."""
        if not curso_str: return None
        norm = curso_str.upper()
        for key, val in CURSO_MAP.items():
            if re.search(r'\b' + re.escape(key) + r'\b', norm) or key == norm:
                return val
        return None

    def _infer_aula_tipo(self, aula_nombre: str) -> TipoAula:
        """Intenta inferir el tipo de aula a partir del nombre del aula."""
        if aula_nombre == "POR DETERMINAR":
            return TipoAula.TEORICA 
        
        target = aula_nombre.upper()
        for tipo, keywords in KEYWORDS_AULA.items():
            for kw in keywords:
                if kw in target:
                    return tipo
        return TipoAula.TEORICA

    def detectar_y_dividir_grupos(self, grupo_raw: Optional[str]) -> List[str]:
        """Divide un string de grupo compuesto en una lista de grupos individuales."""
        if not grupo_raw:
            return [""]

        text = grupo_raw.strip()
        pattern = r'\s*[,/&+]\s*|\s+(?:y|e)\s+|y(?=(?:PA|PL|GR|G\.|[0-9]))'
        partes = re.split(pattern, text, flags=re.IGNORECASE)
        
        return [p.strip() for p in partes if p.strip()]

    def infer_grupo_y_tipo(self, grupo_str: Optional[str], aula_str: str) -> Tuple[str, TipoGrupoDocente]:
        """Deduce el tipo y limpia el código de un UNICO grupo."""
        grupo_raw = (grupo_str or "").strip()
        
        grupo_limpio = re.sub(r'^(GRUPO|GR\.|G\.)\s*', '', grupo_raw, flags=re.IGNORECASE)
        grupo_limpio = grupo_limpio.replace(" ", "").strip()
        
        grupo_upper = grupo_limpio.upper()
        aula_upper = (aula_str or "").strip().upper()
        
        if not grupo_limpio:
            return "", TipoGrupoDocente.TEORIA

        if "PA" in grupo_upper:
            return grupo_limpio, TipoGrupoDocente.PRACTICA

        keywords_lab = KEYWORDS_AULA.get(TipoAula.LABORATORIO, []) + KEYWORDS_AULA.get(TipoAula.INFORMATICA, [])
        es_entorno_lab = any(kw in aula_upper for kw in keywords_lab)

        if es_entorno_lab:
            return grupo_limpio, TipoGrupoDocente.LABORATORIO
        
        if "PL" in grupo_upper:
            return grupo_limpio, TipoGrupoDocente.LABORATORIO

        return grupo_limpio, TipoGrupoDocente.TEORIA


horario_data_normalizer = HorarioDataNormalizer()