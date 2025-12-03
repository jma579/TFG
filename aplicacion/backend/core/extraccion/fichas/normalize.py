"""
Normalización de datos extraídos de fichas académicas.

Responsabilidades:
- Limpiar y normalizar nombres (capitalización, espacios)
- Validar códigos y rangos
- Mapear periodos a enums
- Mapear tipos de asignatura a enums
- Mapear modalidades e idiomas a enums
- Detectar duplicados en BD
- Enriquecer datos desde BD

Flujo:
    SubjectSheet (datos crudos) → normalize_ficha() → NormalizedFichaData (datos listos para BD)
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
    - Detecta duplicados consultando BD
    - Valida rangos y formatos
    
    Example:
        >>> normalizer = DataNormalizer()
        >>> ficha = parser.parse(pdf_text)
        >>> normalized = normalizer.normalize_ficha(ficha, db)
        >>> 
        >>> print(normalized.asignatura.nombre)
        "Cálculo I"
        >>> print(normalized.asignatura.periodo)
        Periodo.PRIMER_CUATRIMESTRE
        >>> print(normalized.asignatura.is_duplicate)
        False
    """
    
    def normalize_ficha(self, ficha: SubjectSheet) -> NormalizedFichaData:
        """
        Normalizar ficha académica SIN acceso a base de datos.
        
        Realiza:
        - Limpieza de strings (strip, capitalize, uppercase)
        - Mapeo a enums (Periodo, ModalidadAsignatura, Idioma, TipoAsignatura)
        - Validación de formatos
        - Parseo de tipos (curso: str → int)
        
        NO realiza:
        - Detección de duplicados (requiere BD)
        - Búsqueda de IDs existentes
        
        Args:
            ficha: SubjectSheet parseado del PDF
            
        Returns:
            NormalizedFichaData con todos los datos normalizados
            (is_duplicate=False, existing_id=None, programa_id=None)
            
        Example:
            >>> normalizer = DataNormalizer()
            >>> ficha = SubjectSheet(codigo_plan="g264", nombre="  CÁLCULO I  ", ...)
            >>> normalized = normalizer.normalize_ficha(ficha)
            >>> normalized.asignatura.codigo_plan  # "G264"
            >>> normalized.asignatura.nombre       # "Cálculo I"
            >>> normalized.asignatura.is_duplicate # False
        """
        # 1. Normalizar asignatura (sin detección de duplicados)
        asignatura = self._normalize_asignatura(ficha)
        
        # 2. Normalizar titulaciones (sin búsqueda de IDs)
        titulaciones = self._normalize_titulaciones(ficha.titulaciones)
        
        # 3. Normalizar profesores (sin detección de duplicados)
        profesores = self._normalize_profesores(ficha.profesores)

        return NormalizedFichaData(
            asignatura=asignatura,
            titulaciones=titulaciones,
            profesores=profesores
        )
    
    # ============================================================
    #  NORMALIZADORES ESPECÍFICOS
    # ============================================================
    
    def _normalize_asignatura(self, ficha: SubjectSheet) -> NormalizedAsignaturaData:
        """Normalizar asignatura"""
        # Normalizar código (uppercase, strip)
        codigo_plan = self._normalize_codigo(ficha.codigo_plan)
        
        # Normalizar nombre (capitalize, strip)
        nombre = self._normalize_nombre(ficha.nombre)
        
        # Mapear periodo a enum
        periodo = self._map_periodo(ficha.periodo, ficha.num_periodo)
        
        # Mapear modalidad a enum
        modalidad = self._map_modalidad(ficha.modalidad)
        
        # Mapear idioma a enum
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
        """Normalizar titulaciones"""
        normalized_list = []
        
        for tit in titulaciones:
            # Normalizar nombre del programa
            programa_nombre = self._normalize_nombre(tit.programa_nombre)
            
            # Mapear tipo de asignatura a enum
            tipo_asignatura = self._map_tipo_asignatura(tit.tipo_asignatura)
            
            # Parsear curso (str → int)
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
        """Normalizar profesores"""
        normalized_list = []
        
        for prof in profesores:
            # Normalizar nombre y apellidos
            nombre = self._normalize_nombre(prof.nombre)
            apellidos = self._normalize_nombre(prof.apellidos)

            normalized_list.append(
                NormalizedProfesorData(
                    nombre=nombre,
                    apellidos=apellidos,
                )
            )
        
        return normalized_list
    
    # ============================================================
    #  MÉTODOS AUXILIARES (Transformaciones)
    # ============================================================

    def _normalize_codigo(self, codigo: str) -> str:
        """
        Normalizar código de asignatura.
        
        Transformaciones:
        - Strip espacios
        - Uppercase (G652, M123, etc.)
        
        Example:
            "g652  " → "G652"
            "  m123" → "M123"
        """
        return codigo.strip().upper()
    
    def _normalize_nombre(self, nombre: str) -> str:
        """
        Normalizar nombre (asignatura, programa, profesor).
        
        Transformaciones:
        - Strip espacios al inicio/final
        - Colapsar espacios múltiples → uno solo
        - Capitalizar cada palabra (title case)
        - Corregir números romanos (I, II, III, IV)
        """
        nombre = nombre.strip()
        nombre = re.sub(r'\s+', ' ', nombre)  # Colapsar espacios múltiples
        nombre = nombre.title()  # Capitalizar cada palabra
        
        # Corregir números romanos (title() convierte: I→I, Ii→Ii, III→Iii)
        nombre = re.sub(r'\bIi\b', 'II', nombre)
        nombre = re.sub(r'\bIii\b', 'III', nombre)
        nombre = re.sub(r'\bIv\b', 'IV', nombre)
        nombre = re.sub(r'\bVi\b', 'VI', nombre)
        nombre = re.sub(r'\bVii\b', 'VII', nombre)
        nombre = re.sub(r'\bViii\b', 'VIII', nombre)
        
        return nombre
    
    def _map_periodo(self, periodo: str, num_periodo: int) -> Periodo:
        """Mapear periodo de ficha a enum Periodo."""
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
        """Mapear tipo_asignatura de ficha a enum TipoAsignatura."""
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
        """Mapear modalidad de ficha a enum ModalidadAsignatura."""
        if not modalidad:
            return ModalidadAsignatura.PRESENCIAL  # Default
        
        modalidad_lower = modalidad.lower().strip()
        
        if "presencial" in modalidad_lower and "semi" not in modalidad_lower:
            return ModalidadAsignatura.PRESENCIAL
        elif "online" in modalidad_lower or "virtual" in modalidad_lower:
            return ModalidadAsignatura.ONLINE
        elif "semi" in modalidad_lower or "hibrida" in modalidad_lower or "híbrida" in modalidad_lower:
            return ModalidadAsignatura.SEMIPRESENCIAL
        else:
            # Si no coincide con ningún patrón, asumir presencial
            return ModalidadAsignatura.PRESENCIAL
    
    def _map_idioma(self, idioma: Optional[str]) -> Idioma:
        """Mapear idioma de ficha a enum Idioma."""
        if not idioma:
            return Idioma.ESPAÑOL  # Default (ajustado: ESPAÑOL en lugar de ESPANOL)
        
        idioma_lower = idioma.lower().strip()
        
        if "español" in idioma_lower or "castellano" in idioma_lower or "spanish" in idioma_lower:
            return Idioma.ESPAÑOL
        elif "inglés" in idioma_lower or "ingles" in idioma_lower or "english" in idioma_lower:
            return Idioma.INGLES
        else:
            # Default a español si no se reconoce
            return Idioma.ESPAÑOL
    
    def _parse_curso(self, curso_str: str) -> int:
        """Parsear curso de string a int."""
        curso_str = curso_str.strip().lower()
        
        # Mapeo de nombres a números
        mapeo = {
            "primero": 1, "1º": 1, "1": 1, "primer": 1,
            "segundo": 2, "2º": 2, "2": 2,
            "tercero": 3, "3º": 3, "3": 3, "tercer": 3,
            "cuarto": 4, "4º": 4, "4": 4,
            "quinto": 5, "5º": 5, "5": 5,
            "sexto": 6, "6º": 6, "6": 6
        }
        
        # Buscar coincidencia en el mapeo
        for key, value in mapeo.items():
            if key in curso_str:
                return value
        
        # Intentar parsear directamente como int
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
        

# ============================================================
#  SINGLETON
# ============================================================

data_normalizer = DataNormalizer()