from typing import List, Dict, Optional
from datetime import datetime, timedelta, time as dt_time
import logging
import re

from core.extraccion.horarios.entities import (
    HorarioExtractionResult, ParsingResult, Horario, Sesion, ParsingMetadata
)
from core.extraccion.horarios.extractor.constants import DIAS_SEMANA
from core.extraccion.horarios.parser.cell_parser import CellParser, ParsedCellData, clean_subject_name

class HorarioParser:
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logging.getLogger(__name__)
        self.cell_parser = CellParser()
        self.warnings = []
        self.errors = []

    def parse(self, extraction_result: HorarioExtractionResult) -> ParsingResult:
        start_time = datetime.now()
        horarios_parsed = []

        for tabla in extraction_result.tablas:
            try:
                horario = self._process_table(tabla)
                if horario.sesiones:
                    horarios_parsed.append(horario)
            except Exception as e:
                self.logger.error(f"Error parseando tabla pág {tabla.pagina}: {e}")
                self.errors.append(f"Error en tabla {tabla.pagina}: {str(e)}")

        parsing_meta = ParsingMetadata(
            parser_name="GridParserV2.1",
            parser_version="2.1.0",
            parse_timestamp=datetime.now(),
            parse_duration=(datetime.now() - start_time).total_seconds(),
            warnings=self.warnings,
            errors=self.errors
        )

        return self._to_normalize(
            ParsingResult(
                titulo=extraction_result.titulo,
                horarios=horarios_parsed,
                extraction_metadata=extraction_result.metadata,
                parsing_metadata=parsing_meta
            )
        )

    def _process_table(self, tabla) -> Horario:
        sesiones: List[Sesion] = []
        col_day_map = {idx: d for idx, d in enumerate(tabla.day_columns) if d in DIAS_SEMANA}
        
        # Estado de sesión activa por columna: { col_idx: { 'data': ParsedData, 'hora_inicio': ..., 'hora_fin': ... } }
        active_sessions: Dict[int, Dict] = {}

        for r_idx, hora_inicio_str in enumerate(tabla.time_rows):
            if not hora_inicio_str: continue
            
            hora_inicio = self._parse_time(hora_inicio_str)
            hora_fin_estimada = self._calculate_end_time(tabla.time_rows, r_idx, hora_inicio)
            
            row_cells = tabla.celdas[r_idx]

            for c_idx, cell_text in enumerate(row_cells):
                if c_idx not in col_day_map: continue
                
                day_name = col_day_map[c_idx]
                parsed_data = self.cell_parser.parse(cell_text)
                
                if c_idx in active_sessions:
                    prev = active_sessions[c_idx]
                    
                    # --- LÓGICA DE FUSIÓN SEMÁNTICA ---
                    # Comprobamos si la celda actual es la continuación ("cola") de la anterior ("cabeza")
                    continuation_type = self._check_continuation(prev['data'], parsed_data)
                    
                    if continuation_type != "NONE":
                        # Extender hora fin
                        prev['hora_fin'] = hora_fin_estimada
                        
                        # Si es una continuación de texto ("n empresa"), concatenamos el nombre
                        if continuation_type == "TEXT_TAIL":
                            new_name = f"{prev['data'].asignatura} {parsed_data.asignatura or ''}".strip()
                            prev['data'].asignatura = clean_subject_name(new_name)
                        
                        # Mezclar otros datos (aula, grupo) si aparecieron ahora
                        self._merge_data(prev['data'], parsed_data)
                    
                    else:
                        # Cerrar sesión anterior
                        sesiones.append(self._build_sesion(prev, day_name))
                        del active_sessions[c_idx]
                        
                        # Iniciar nueva si aplica
                        if parsed_data.asignatura:
                            active_sessions[c_idx] = {
                                'hora_inicio': hora_inicio,
                                'hora_fin': hora_fin_estimada,
                                'data': parsed_data
                            }
                else:
                    if parsed_data.asignatura:
                        active_sessions[c_idx] = {
                            'hora_inicio': hora_inicio,
                            'hora_fin': hora_fin_estimada,
                            'data': parsed_data
                        }

        # Cerrar remanentes
        for c_idx, session_info in active_sessions.items():
            sesiones.append(self._build_sesion(session_info, col_day_map[c_idx]))

        return Horario(
            curso=tabla.curso,
            periodo=None,
            sesiones=sesiones,
            mencion=tabla.mencion,
            pagina=tabla.pagina
        )

    def _check_continuation(self, prev: ParsedCellData, curr: ParsedCellData) -> str:
        """
        Analiza si 'curr' es continuación de 'prev'.
        Retorna: "NONE", "SAME_BLOCK" (misma clase), "TEXT_TAIL" (nombre partido).
        """
        # 1. Si la celda actual está vacía visualmente -> NO es continuación (es un hueco libre)
        if not curr.raw_text:
            return "NONE"

        # 2. Mismo texto exacto -> SAME_BLOCK (Celda fusionada en PDF)
        if prev.raw_text == curr.raw_text:
            return "SAME_BLOCK"

        # 3. Detección de "Cola de Texto" (Nombre partido)
        # Si la celda actual empieza con minúscula (y tiene texto), es muy probable que sea cola.
        if curr.raw_text and curr.raw_text[0].islower():
            return "TEXT_TAIL"
        
        # Si la anterior terminó en conector (de, a, y...)
        if prev.asignatura and re.search(r'\b(de|a|y|en|con|del|la|los|las)\s*$', prev.asignatura, re.IGNORECASE):
            return "TEXT_TAIL"

        # 4. Herencia de Aula (Sin asignatura nueva)
        # Si actual no tiene asignatura pero tiene aula/grupo -> SAME_BLOCK (es la misma clase definiendo aula)
        if not curr.asignatura and (curr.aula or curr.grupo):
            return "SAME_BLOCK"

        return "NONE"

    def _merge_data(self, target: ParsedCellData, source: ParsedCellData):
        if not target.aula and source.aula: target.aula = source.aula
        if not target.grupo and source.grupo: target.grupo = source.grupo
        # Si la actual definió un tipo más específico (ej: PRACTICA), actualizar
        if target.tipo == 'CLASE' and source.tipo != 'CLASE':
            target.tipo = source.tipo

    def _build_sesion(self, info: Dict, dia: str) -> Sesion:
        data: ParsedCellData = info['data']
        return Sesion(
            asignatura=data.asignatura or "DESCONOCIDA",
            aula=data.aula or "POR DETERMINAR",
            dia=dia,
            hora_inicio=info['hora_inicio'],
            hora_fin=info['hora_fin'],
            tipo=data.tipo,
            grupo=data.grupo
        )

    def _calculate_end_time(self, time_rows, current_idx, current_start):
        if current_idx + 1 < len(time_rows):
            next_time_str = time_rows[current_idx + 1]
            if next_time_str:
                return self._parse_time(next_time_str)
        dt = datetime.combine(datetime.today(), current_start) + timedelta(minutes=60)
        return dt.time()

    def _parse_time(self, t_str: str) -> dt_time:
        try:
            parts = t_str.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except: return dt_time(0, 0)

    def _to_normalize(self, parsed_result: ParsingResult) -> Dict:
        return {
            "titulo": parsed_result.titulo,
            "horarios": [
                {
                    "curso": h.curso,
                    "mencion": h.mencion,
                    "sesiones": [
                        {
                            "asignatura": s.asignatura,
                            "aula": s.aula,
                            "dia": s.dia,
                            "hora_inicio": s.hora_inicio.strftime("%H:%M"),
                            "hora_fin": s.hora_fin.strftime("%H:%M"),
                            "tipo": s.tipo,
                            "grupo": s.grupo
                        } for s in h.sesiones
                    ]
                } for h in parsed_result.horarios
            ],
            "metadata": parsed_result.parsing_metadata.__dict__ if parsed_result.parsing_metadata else {}
        }