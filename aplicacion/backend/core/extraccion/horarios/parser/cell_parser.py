from dataclasses import dataclass
from typing import Optional
import re
from core.extraccion.horarios.parser.parser_rules import (
    RE_AULA, RE_GRUPO, TIPO_PRACTICA, TIPO_TEORIA, TIPO_GENERICO, 
    clean_subject_name, apply_ocr_corrections
)

@dataclass
class ParsedCellData:
    asignatura: Optional[str] = None
    aula: Optional[str] = None
    grupo: Optional[str] = None
    tipo: str = TIPO_GENERICO
    raw_text: str = ""

class CellParser:
    """Tokenizador de celdas con corrección de OCR."""

    def parse(self, text: Optional[str]) -> ParsedCellData:
        if not text or not text.strip():
            return ParsedCellData()

        if text.strip().startswith('(*)'):
            return ParsedCellData(raw_text=text) 

        clean_text = text.replace('\n', ' ').strip()
        clean_text = apply_ocr_corrections(clean_text)
        
        aula = None
        match_aula = RE_AULA.search(clean_text)
        if match_aula:
            aula = match_aula.group(0).strip()
            clean_text = clean_text[:match_aula.start()] + " " + clean_text[match_aula.end():]

        grupo = None
        match_grupo = RE_GRUPO.search(clean_text)
        if match_grupo:
            grupo = match_grupo.group(0).strip()
            clean_text = clean_text[:match_grupo.start()] + " " + clean_text[match_grupo.end():]

        tipo = TIPO_GENERICO
        if grupo:
            grupo_upper = grupo.upper()
            aula_upper = (aula or "").upper()
            
            if 'PL' in grupo_upper or 'LAB' in aula_upper or 'LSC' in aula_upper or 'LATC' in aula_upper:
                tipo = TIPO_PRACTICA
            elif 'PA' in grupo_upper:
                tipo = TIPO_PRACTICA
            else:
                tipo = TIPO_TEORIA
        
        asignatura = clean_subject_name(clean_text)
        
        if len(asignatura) < 3:
            asignatura = None

        return ParsedCellData(
            asignatura=asignatura,
            aula=aula,
            grupo=grupo,
            tipo=tipo,
            raw_text=text
        )