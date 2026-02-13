"""
Normalización de datos extraídos de fichas académicas.

Transforma datos crudos del PDF a datos limpios listos para BD:
limpia nombres, mapea strings a enums, valida formatos.
"""

import re
from typing import Optional, List

from core.extraccion.fichas.entities import (
    SubjectSheet, Titulacion, Teacher,
    NormalizedAsignaturaData, NormalizedTitulacionData,
    NormalizedProfesorData, NormalizedFichaData
)
from constants.enums import Periodo, TipoAsignatura, ModalidadAsignatura, Idioma


class DataNormalizer:
    """
    Normaliza datos extraídos de fichas académicas.
    
    Transforma datos crudos del PDF a datos limpios listos para BD:
    - Limpia y capitaliza nombres
    - Mapea strings a enums
    - Parsea formatos diversos a tipos consistentes
    - Valida rangos y formatos
    """
    
    def normalize_ficha(self, ficha: SubjectSheet) -> NormalizedFichaData:
        """
        Normalizar ficha académica completa.
        
        Args:
            ficha: SubjectSheet parseado del PDF
            
        Returns:
            NormalizedFichaData con todos los datos normalizados y listos para BD
        """
        asignatura = self._normalize_asignatura(ficha)
        titulaciones = self._normalize_titulaciones(ficha.titulaciones)
        profesores = self._normalize_profesores(ficha.profesores)

        return NormalizedFichaData(
            asignatura=asignatura,
            titulaciones=titulaciones,
            profesores=profesores
        )
    
    def _normalize_asignatura(self, ficha: SubjectSheet) -> NormalizedAsignaturaData:
        """Normalizar datos de asignatura."""
        codigo_plan = self._normalize_codigo(ficha.codigo_plan)
        nombre = self._normalize_nombre(ficha.nombre)
        periodo = self._map_periodo(ficha.periodo, ficha.num_periodo)
        modalidad = self._map_modalidad(ficha.modalidad)
        idioma = self._map_idioma(ficha.idioma)
        
        return NormalizedAsignaturaData(
            codigo_plan=codigo_plan,
            nombre=nombre,
            periodo=periodo,
            ects=ficha.ects,
            modalidad=modalidad,
            idioma=idioma,
            english_friendly=ficha.english_friendly or False,
        )
    
    def _normalize_titulaciones(
        self, 
        titulaciones: List[Titulacion]
    ) -> List[NormalizedTitulacionData]:
        """Normalizar lista de titulaciones."""
        normalized_list = []
        
        for tit in titulaciones:
            programa_nombre = self._normalize_nombre(tit.programa_nombre)
            tipo_asignatura = self._map_tipo_asignatura(tit.tipo_asignatura)
            curso = self._parse_curso(tit.curso)
            
            normalized_list.append(
                NormalizedTitulacionData(
                    programa_nombre=programa_nombre,
                    tipo_asignatura=tipo_asignatura,
                    curso=curso,
                )
            )
        
        return normalized_list
    
    def _normalize_profesores(
        self,
        profesores: List[Teacher]
    ) -> List[NormalizedProfesorData]:
        """Normalizar lista de profesores."""
        normalized_list = []
        
        for prof in profesores:
            nombre = self._normalize_nombre(prof.nombre)
            apellidos = self._normalize_nombre(prof.apellidos)

            normalized_list.append(
                NormalizedProfesorData(
                    nombre=nombre,
                    apellidos=apellidos,
                )
            )
        
        return normalized_list

    def _normalize_codigo(self, codigo: str) -> str:
        """
        Normalizar código de asignatura: strip y uppercase.
        
        Example: "g652  " → "G652"
        """
        return codigo.strip().upper()
    
    def _normalize_nombre(self, nombre: str) -> str:
        """
        Normalizar nombre: strip, colapsar espacios, title case, corregir romanos.
        
        Example: "  CÁLCULO   I  " → "Cálculo I"
        """
        nombre = nombre.strip()
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.title()
        
        # Corregir números romanos
        nombre = re.sub(r'\bIi\b', 'II', nombre)
        nombre = re.sub(r'\bIii\b', 'III', nombre)
        nombre = re.sub(r'\bIv\b', 'IV', nombre)
        nombre = re.sub(r'\bVi\b', 'VI', nombre)
        nombre = re.sub(r'\bVii\b', 'VII', nombre)
        nombre = re.sub(r'\bViii\b', 'VIII', nombre)
        
        return nombre
    
    def _map_periodo(self, periodo: str, num_periodo: int) -> Periodo:
        """Mapear periodo a enum Periodo."""
        periodo_lower = periodo.lower().strip()
        
        if periodo_lower in ("anual", "annual"):
            return Periodo.ANUAL
        elif periodo_lower in ("cuatrimestral", "quarterly", "semestral", "semester"):
            if num_periodo == 1:
                return Periodo.PRIMER_CUATRIMESTRE
            elif num_periodo == 2:
                return Periodo.SEGUNDO_CUATRIMESTRE
            else:
                raise ValueError(
                    f"num_periodo inválido: {num_periodo} (debe ser 1 o 2 para periodo cuatrimestral)"
                )
        else:
            raise ValueError(f"periodo desconocido: '{periodo}' (esperado: 'Cuatrimestral' o 'Anual')")
    
    def _map_tipo_asignatura(self, tipo: str) -> TipoAsignatura:
        """Mapear tipo de asignatura a enum TipoAsignatura."""
        tipo_lower = tipo.lower().strip()
        
        if "básica" in tipo_lower or "basica" in tipo_lower:
            return TipoAsignatura.BASICA
        elif "obligatoria" in tipo_lower:
            return TipoAsignatura.OBLIGATORIA
        elif "optativa" in tipo_lower:
            return TipoAsignatura.OPTATIVA
        else:
            raise ValueError(
                f"tipo_asignatura desconocido: '{tipo}' "
                f"(esperado: 'Básica', 'Obligatoria' o 'Optativa')"
            )
    
    def _map_modalidad(self, modalidad: Optional[str]) -> ModalidadAsignatura:
        """Mapear modalidad a enum ModalidadAsignatura. Default: PRESENCIAL."""
        if not modalidad:
            return ModalidadAsignatura.PRESENCIAL
        
        modalidad_lower = modalidad.lower().strip()
        
        if "presencial" in modalidad_lower and "semi" not in modalidad_lower:
            return ModalidadAsignatura.PRESENCIAL
        elif "online" in modalidad_lower or "virtual" in modalidad_lower:
            return ModalidadAsignatura.ONLINE
        elif "semi" in modalidad_lower or "hibrida" in modalidad_lower or "híbrida" in modalidad_lower:
            return ModalidadAsignatura.SEMIPRESENCIAL
        else:
            return ModalidadAsignatura.PRESENCIAL
    
    def _map_idioma(self, idioma: Optional[str]) -> Idioma:
        """Mapear idioma a enum Idioma. Default: ESPAÑOL."""
        if not idioma:
            return Idioma.ESPAÑOL
        
        idioma_lower = idioma.lower().strip()
        
        if "español" in idioma_lower or "castellano" in idioma_lower or "spanish" in idioma_lower:
            return Idioma.ESPAÑOL
        elif "inglés" in idioma_lower or "ingles" in idioma_lower or "english" in idioma_lower:
            return Idioma.INGLES
        else:
            return Idioma.ESPAÑOL
    
    def _parse_curso(self, curso_str: str) -> int:
        """
        Parsear curso de string a int (1-6).
        
        Soporta: "Primero", "1º", "1", "primer", etc.
        """
        curso_str = curso_str.strip().lower()
        
        mapeo = {
            "primero": 1, "1º": 1, "1": 1, "primer": 1,
            "segundo": 2, "2º": 2, "2": 2,
            "tercero": 3, "3º": 3, "3": 3, "tercer": 3,
            "cuarto": 4, "4º": 4, "4": 4,
            "quinto": 5, "5º": 5, "5": 5,
            "sexto": 6, "6º": 6, "6": 6
        }
        
        for key, value in mapeo.items():
            if key in curso_str:
                return value
        
        try:
            curso_int = int(curso_str)
            if 1 <= curso_int <= 6:
                return curso_int
            else:
                raise ValueError(f"Curso fuera de rango: {curso_int} (debe estar entre 1 y 6)")
        except ValueError:
            raise ValueError(
                f"No se pudo parsear curso: '{curso_str}' "
                f"(esperado: '1', 'Primero', '1º', etc.)"
            )


data_normalizer = DataNormalizer()