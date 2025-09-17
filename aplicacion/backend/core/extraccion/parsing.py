"""
Parser académico para extraer información estructurada de texto OCR.

Este módulo toma el texto extraído por OCR y lo convierte en entidades
académicas estructuradas (códigos de asignaturas, horarios, profesores, etc.).
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import time

from constants.extraccion import (
    MIN_CONFIDENCE,
    SUBJECT_CODE_PATTERNS,
    TIME_PATTERNS, 
    DAY_PATTERNS,
    PROFESSOR_PATTERNS,
    CLASSROOM_PATTERNS,
    ParsedAcademicContent,
    SubjectCode,
    Schedule,
    Professor,
    Classroom
)


class AcademicTextParser:
    """
    Parser principal para documentos académicos españoles.
    
    Extrae información estructurada de texto procesado por OCR,
    específicamente optimizado para horarios universitarios y
    documentos académicos en español.
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Inicializa el parser académico.
        
        Args:
            confidence_threshold: Umbral mínimo de confianza para aceptar extracciones
        """
        self.confidence_threshold = confidence_threshold
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila todos los patrones regex para mejor rendimiento."""
        
        self.compiled_subject_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in SUBJECT_CODE_PATTERNS
        ]
        self.compiled_time_patterns = [
            re.compile(pattern) 
            for pattern in TIME_PATTERNS
        ]
        self.compiled_day_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in DAY_PATTERNS
        ]
        self.compiled_professor_patterns = [
            re.compile(pattern) 
            for pattern in PROFESSOR_PATTERNS
        ]
        self.compiled_classroom_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in CLASSROOM_PATTERNS
        ]
    

    def parse_text(self, text: str) -> ParsedAcademicContent:
        """
        Método principal que extrae toda la información académica del texto.
        
        Args:
            text: Texto extraído por OCR
            
        Returns:
            ParsedAcademicContent con todas las entidades detectadas
        """
        # Preprocesar texto
        cleaned_text = self._preprocess_text(text)
        
        # Extraer cada tipo de entidad
        subject_codes = self._extract_subject_codes(cleaned_text)
        schedules = self._extract_schedules(cleaned_text)
        professors = self._extract_professors(cleaned_text)
        classrooms = self._extract_classrooms(cleaned_text)
        
        # Calcular confianza general
        overall_confidence = self._calculate_overall_confidence(
            subject_codes, schedules, professors, classrooms
        )
        
        # Crear resultado final
        return ParsedAcademicContent(
            subject_codes=subject_codes,
            schedules=schedules,
            professors=professors,
            classrooms=classrooms,
            confidence_score=overall_confidence
        )
    
    def validate_extraction_quality(self, result: ParsedAcademicContent) -> bool:
        """
        Valida si el resultado del parsing es de calidad aceptable.
        
        Args:
            result: Resultado del parsing
            
        Returns:
            True si es aceptable, False en caso contrario
        """
        
        # Verificar confianza global
        if result.overall_confidence < MIN_CONFIDENCE:
            return False
        
        # Verificar que al menos hay una entidad extraída
        total_entities = (
            len(result.subject_codes) + 
            len(result.schedules) + 
            len(result.professors) + 
            len(result.classrooms)
        )
        
        if total_entities == 0:
            return False
        
        # Verificar que hay al menos códigos de asignatura (lo más básico)
        if not result.subject_codes:
            return False
        
        # Verificar coherencia temporal en horarios
        conflictos_temporales = 0
        for i, schedule1 in enumerate(result.schedules):
            for j, schedule2 in enumerate(result.schedules[i+1:], i+1):
                # Verificar solapamiento en mismo día
                if (schedule1.day_of_week == schedule2.day_of_week and 
                    schedule1.time_start and schedule1.time_end and
                    schedule2.time_start and schedule2.time_end):
                    
                    # Convertir strings a time para comparación precisa
                    try:
                        from datetime import datetime
                        s1_start = datetime.strptime(schedule1.time_start, '%H:%M').time()
                        s1_end = datetime.strptime(schedule1.time_end, '%H:%M').time()
                        s2_start = datetime.strptime(schedule2.time_start, '%H:%M').time()  
                        s2_end = datetime.strptime(schedule2.time_end, '%H:%M').time()
                        
                        # Verificar solapamiento temporal
                        if (s1_start < s2_end and s2_start < s1_end):
                            conflictos_temporales += 1
                    except (ValueError, AttributeError):
                        # Si falla el parsing de tiempo, asumir conflicto para ser conservador
                        conflictos_temporales += 1
        
        # Si hay muchos conflictos temporales, probable error de extracción
        if conflictos_temporales > len(result.schedules) * 0.3:
            return False
        
        # Verificar patrones académicos básicos
        suspicious_patterns = 0
        
        # Códigos de asignatura sospechosos (muy largos o muy cortos)
        for subject in result.subject_codes:
            if len(subject.code) < 2 or len(subject.code) > 15:
                suspicious_patterns += 1
        
        # Nombres de profesores sospechosos (muy cortos o con demasiados números)
        for professor in result.professors:
            name_length = len(professor.name.strip())
            digit_count = sum(c.isdigit() for c in professor.name)
            
            if name_length < 3 or digit_count > name_length * 0.5:
                suspicious_patterns += 1
        
        # Si hay demasiados patrones sospechosos
        if suspicious_patterns > total_entities * 0.4:
            return False
        
        # Verificar balance de datos
        # Si solo hay códigos y nada más, podría ser extracción incompleta
        if len(result.subject_codes) > 0 and total_entities == len(result.subject_codes):
            if len(result.subject_codes) < 3:  # Muy pocos datos
                return False
        
        # Si llegamos aquí, la extracción es válida
        return True
    

    def _preprocess_text(self, text: str) -> str:
        """
        Limpia y normaliza el texto para mejorar la extracción.
        
        Args:
            text: Texto original del OCR
            
        Returns:
            Texto limpio y normalizado
        """
        if not text or not text.strip():
            return ""
        
        cleaned = self._normalize_whitespace(text)
        cleaned = self._fix_ocr_errors(cleaned)
        cleaned = self._remove_noise_characters(cleaned)
        
        return cleaned.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normaliza espacios y puntuación para parsing óptimo."""
        # Múltiples espacios → uno solo
        text = re.sub(r'\s+', ' ', text)
        
        # Espacios alrededor de puntuación común
        text = re.sub(r'\s*:\s*', ': ', text)      # "Profesor : Dr." → "Profesor: Dr."
        text = re.sub(r'\s*-\s*', ' - ', text)     # "9:00-11:00" → "9:00 - 11:00"
        text = re.sub(r'\s*,\s*', ', ', text)      # "L,M,X" → "L, M, X"
        text = re.sub(r'\s*\(\s*', ' (', text)     # "G1234 (" → "G1234 ("
        text = re.sub(r'\s*\)\s*', ') ', text)     # ") Ed." → ") Ed."
        
        return text
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Corrige errores típicos de OCR en contextos académicos."""
        # Correcciones en códigos de asignatura (G1234, M101, etc.)
        text = re.sub(r'\b([A-Z])l(\d{3,4})\b', r'\1I\2', text)  # Gl234 → GI234 → G1234
        text = re.sub(r'\b([A-Z])I(\d{3,4})\b', r'\g<1>1\g<2>', text)  # GI234 → G1234
        
        # Correcciones en horarios (9:00, 11:30, etc.)
        text = re.sub(r'(\d+):O(\d)', r'\1:0\2', text)           # 9:O0 → 9:00
        text = re.sub(r'(\d+):o(\d)', r'\1:0\2', text)           # 9:o0 → 9:00 (minúscula)
        text = re.sub(r'(\d+):[lI](\d)', r'\1:1\2', text)        # 9:l5 → 9:15
        
        # Correcciones en aulas (A101, B205, etc.)
        text = re.sub(r'\b([A-Z])l(\d+)l?\b', r'\g<1>1\g<2>', text)  # AlOl → A101
        text = re.sub(r'\b([A-Z])O(\d+)\b', r'\g<1>0\g<2>', text)    # AO1 → A01
        
        # Correcciones en números comunes
        text = re.sub(r'\bO(\d)', r'0\1', text)                  # O5 → 05
        text = re.sub(r'(\d)O\b', r'\g<1>0', text)               # 5O → 50
        text = re.sub(r'\bl(\d)', r'1\1', text)                  # l5 → 15
        text = re.sub(r'(\d)l\b', r'\g<1>1', text)               # 5l → 51
        
        return text
    
    def _remove_noise_characters(self, text: str) -> str:
        """Elimina caracteres que interfieren con el parsing."""
        # Caracteres de ruido típicos del OCR
        noise_chars = ['~', '•', '◦', '▪', '►', '¬', '§', '©', '®', '™']
        for char in noise_chars:
            text = text.replace(char, ' ')
        
        # Símbolos problemáticos alrededor de entidades importantes
        text = re.sub(r'([A-Z]\d{3,4})[@#$%^&*]+', r'\1', text)  # G1234@#$ → G1234
        text = re.sub(r'[@#$%^&*]+([A-Z]\d{3,4})', r'\1', text)  # @#$G1234 → G1234
        
        # Eliminar caracteres de control pero mantener saltos de línea útiles
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Limpiar secuencias de símbolos extraños
        text = re.sub(r'[^\w\s\.,;:!?\-()áéíóúñÁÉÍÓÚÑ]{2,}', ' ', text)
        
        return text
    
    
    def _extract_subject_codes(self, text: str) -> List[SubjectCode]:
        """
        Extrae códigos de asignaturas del texto.
        
        Args:
            text: Texto limpio
            
        Returns:
            Lista de códigos encontrados con su confianza
        """
        codes = []
        seen_codes = set()  # Para eliminar duplicados
        
        # Aplicar cada patrón compilado
        for pattern in self.compiled_subject_patterns:
            for match in pattern.finditer(text):
                # Extraer y limpiar código
                raw_code = match.group(0)
                clean_code = self._clean_subject_code(raw_code)
                
                # Evitar duplicados
                if clean_code in seen_codes:
                    continue
                seen_codes.add(clean_code)
                
                # Obtener contexto y calcular confianza
                context = self._get_context_around_match(text, match, 50)
                confidence = self._calculate_confidence_for_match(
                    match, context, 'subject_code'
                )
                
                # Crear entidad si supera el umbral
                if confidence >= self.confidence_threshold:
                    codes.append(SubjectCode(
                        code=clean_code,
                        full_match=raw_code,
                        confidence=confidence,
                        position=(match.start(), match.end())
                    ))
        
        # Ordenar por posición en el texto
        codes.sort(key=lambda x: x.position[0])
        return codes
    
    def _extract_schedules(self, text: str) -> List[Schedule]:
        """
        Extrae información de horarios del texto.
        
        Args:
            text: Texto limpio
            
        Returns:
            Lista de horarios encontrados
        """
        schedules = []
        
        # Extraer todas las coincidencias de tiempo y día por separado
        time_matches = self._find_all_time_matches(text)
        day_matches = self._find_all_day_matches(text)
        
        # Asociar tiempos con días por proximidad
        schedule_candidates = self._associate_times_with_days(time_matches, day_matches, text)
        
        # Validar y procesar cada candidato
        seen_schedules = set()  # Para eliminar duplicados
        
        for candidate in schedule_candidates:
            # Validar coherencia temporal
            if not self._validate_time_logic(candidate):
                continue
            
            # Crear identificador único para evitar duplicados
            schedule_key = self._create_schedule_key(candidate)
            if schedule_key in seen_schedules:
                continue
            seen_schedules.add(schedule_key)
            
            # Calcular confianza
            confidence = self._calculate_schedule_confidence(candidate, text)
            
            # Crear entidad si supera el umbral
            if confidence >= self.confidence_threshold:
                schedules.append(Schedule(
                    time_start=candidate['start_time'].strftime('%H:%M') if candidate['start_time'] else None,
                    time_end=candidate['end_time'].strftime('%H:%M') if candidate['end_time'] else None,
                    days=[candidate['day']],  # Lista de días
                    raw_text=candidate['full_text'],
                    confidence=confidence,
                    position=candidate['position']
                ))
        
        # Ordenar por día de semana y luego por hora de inicio
        schedules.sort(key=lambda x: (x.day_of_week_number, x.time_start or ""))
        return schedules
    
    def _extract_professors(self, text: str) -> List[Professor]:
        """
        Extrae información de profesores del texto.
        
        Args:
            text: Texto limpio
            
        Returns:
            Lista de profesores encontrados
        """
        professors = []
        seen_professors = set()  # Para eliminar duplicados
        
        # Aplicar cada patrón compilado
        for pattern in self.compiled_professor_patterns:
            for match in pattern.finditer(text):
                # Extraer y limpiar nombre
                raw_match = match.group(0)
                clean_name = self._clean_professor_name(raw_match)
                
                # Evitar duplicados
                if clean_name.lower() in seen_professors:
                    continue
                seen_professors.add(clean_name.lower())
                
                # Obtener contexto y calcular confianza
                context = self._get_context_around_match(text, match, 60)
                confidence = self._calculate_confidence_for_match(
                    match, context, 'professor'
                )
                
                # Crear entidad si supera el umbral
                if confidence >= self.confidence_threshold:
                    professors.append(Professor(
                        name=clean_name,
                        title=None,  # Por simplicidad, sin títulos por ahora
                        full_match=raw_match,
                        confidence=confidence,
                        position=(match.start(), match.end())
                    ))
        
        # Ordenar por posición en el texto
        professors.sort(key=lambda x: x.position[0])
        return professors
    
    def _extract_classrooms(self, text: str) -> List[Classroom]:
        """
        Extrae información de aulas del texto.
        
        Args:
            text: Texto limpio
            
        Returns:
            Lista de aulas encontradas
        """
        classrooms = []
        seen_classrooms = set()  # Para eliminar duplicados
        
        # Aplicar cada patrón compilado
        for pattern in self.compiled_classroom_patterns:
            for match in pattern.finditer(text):
                # Extraer y limpiar identificador de aula
                raw_match = match.group(0)
                clean_identifier = self._clean_classroom_identifier(raw_match)
                
                # Evitar duplicados
                if clean_identifier.lower() in seen_classrooms:
                    continue
                seen_classrooms.add(clean_identifier.lower())
                
                # Detectar tipo de aula y ubicación
                room_type = self._detect_classroom_type(raw_match)
                location = self._extract_classroom_location(raw_match)
                
                # Obtener contexto y calcular confianza
                context = self._get_context_around_match(text, match, 50)
                confidence = self._calculate_confidence_for_match(
                    match, context, 'classroom'
                )
                
                # Crear entidad si supera el umbral
                if confidence >= self.confidence_threshold:
                    classrooms.append(Classroom(
                        identifier=clean_identifier,
                        room_type=room_type,
                        location=location,
                        full_match=raw_match,
                        confidence=confidence,
                        position=(match.start(), match.end())
                    ))
        
        # Ordenar por posición en el texto
        classrooms.sort(key=lambda x: x.position[0])
        return classrooms
    
   
    def _calculate_overall_confidence(
        self,
        subject_codes: List[SubjectCode],
        schedules: List[Schedule], 
        professors: List[Professor],
        classrooms: List[Classroom]
    ) -> float:
        """
        Calcula la confianza general del parsing completo.
        
        Combina 3 dimensiones:
        1. Completitud (30%) - ¿Cuántas entidades encontramos?
        2. Calidad (50%) - ¿Qué tan buenas son las entidades?
        3. Coherencia (20%) - ¿Tienen sentido lógico juntas?
        
        Args:
            subject_codes: Listas de entidades extraídas
            schedules: Listas de entidades extraídas
            professors: Listas de entidades extraídas
            classrooms: Listas de entidades extraídas
            
        Returns:
            Confianza general (0.0-1.0)
        """
        
        # COMPLETITUD (30%) - Análisis de cantidad de entidades
        completeness_score = 0.0
        
        # Puntuación base por cada tipo de entidad encontrada
        if subject_codes:
            completeness_score += 0.4  # Los códigos son lo más importante
        if schedules:
            completeness_score += 0.3  # Horarios muy importantes
        if professors:
            completeness_score += 0.2  # Profesores importantes
        if classrooms:
            completeness_score += 0.1  # Aulas útiles pero no críticas
        
        # Bonificación por abundancia de datos
        total_entities = len(subject_codes) + len(schedules) + len(professors) + len(classrooms)
        if total_entities >= 5:
            completeness_score += 0.1  # Bonificación por riqueza de datos
        elif total_entities >= 10:
            completeness_score += 0.2  # Bonificación mayor por datos muy ricos
        
        completeness_score = min(1.0, completeness_score)
        

        # CALIDAD (50%) - Análisis de confianza promedio ponderada
        quality_score = 0.0
        
        if total_entities > 0:
            # Pesos por importancia de cada tipo de entidad
            total_weighted_confidence = 0.0
            total_weight = 0.0
            
            # Procesar códigos de asignatura (peso: 40%)
            if subject_codes:
                avg_confidence = sum(sc.confidence for sc in subject_codes) / len(subject_codes)
                total_weighted_confidence += avg_confidence * 0.4
                total_weight += 0.4
            
            # Procesar horarios (peso: 30%)
            if schedules:
                avg_confidence = sum(sch.confidence for sch in schedules) / len(schedules)
                total_weighted_confidence += avg_confidence * 0.3
                total_weight += 0.3
            
            # Procesar profesores (peso: 20%)
            if professors:
                avg_confidence = sum(prof.confidence for prof in professors) / len(professors)
                total_weighted_confidence += avg_confidence * 0.2
                total_weight += 0.2
            
            # Procesar aulas (peso: 10%)
            if classrooms:
                avg_confidence = sum(room.confidence for room in classrooms) / len(classrooms)
                total_weighted_confidence += avg_confidence * 0.1
                total_weight += 0.1
            
            quality_score = total_weighted_confidence / total_weight if total_weight > 0 else 0.0


        # COHERENCIA (20%) - Análisis de consistencia lógica
        coherence_score = 0.7  # Base neutral
        
        # COHERENCIA TEMPORAL: Verificar conflictos en horarios
        if schedules and len(schedules) > 1:
            has_conflicts = False
            for i, sch1 in enumerate(schedules):
                for sch2 in schedules[i+1:]:
                    # Verificar solapamiento en el mismo día
                    if (sch1.day_of_week == sch2.day_of_week and 
                        sch1.time_start and sch2.time_start and
                        sch1.time_end and sch2.time_end):
                        
                        # Convertir strings a time para comparación precisa
                        try:
                            from datetime import datetime
                            s1_start = datetime.strptime(sch1.time_start, '%H:%M').time()
                            s1_end = datetime.strptime(sch1.time_end, '%H:%M').time()
                            s2_start = datetime.strptime(sch2.time_start, '%H:%M').time()
                            s2_end = datetime.strptime(sch2.time_end, '%H:%M').time()
                            
                            # Hay conflicto si los horarios se solapan
                            if not (s1_end <= s2_start or s2_end <= s1_start):
                                has_conflicts = True
                                break
                        except (ValueError, AttributeError):
                            # Si falla el parsing, asumir conflicto
                            has_conflicts = True
                            break
                if has_conflicts:
                    break
            
            if has_conflicts:
                coherence_score -= 0.3  # Penalización por conflictos temporales
            else:
                coherence_score += 0.1  # Bonificación por coherencia temporal
        
        # COHERENCIA ACADÉMICA: Verificar patrones típicos
        if schedules:
            # Verificar que los horarios están en rangos académicos razonables
            reasonable_schedules = 0
            for sch in schedules:
                if sch.time_start:
                    try:
                        from datetime import datetime
                        start_time = datetime.strptime(sch.time_start, '%H:%M').time()
                        if 7 <= start_time.hour <= 21:
                            reasonable_schedules += 1
                            # Bonificación extra por días laborables
                            if sch.day_of_week in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']:
                                reasonable_schedules += 0.5
                    except (ValueError, AttributeError):
                        # Si falla el parsing, no contar como razonable
                        pass
            
            if reasonable_schedules / len(schedules) >= 0.8:  # 80% de horarios razonables
                coherence_score += 0.1
            elif reasonable_schedules / len(schedules) < 0.5:  # Menos del 50% razonables
                coherence_score -= 0.2
        
        # COHERENCIA DE DATOS: Verificar que tenemos combinaciones lógicas
        academic_completeness = 0
        if subject_codes and schedules:
            academic_completeness += 0.3  # Código + horario es lógico
        if subject_codes and professors:
            academic_completeness += 0.2  # Código + profesor es lógico
        if schedules and classrooms:
            academic_completeness += 0.2  # Horario + aula es lógico
        if subject_codes and professors and schedules:
            academic_completeness += 0.2  # Tripleta académica completa
        if len([x for x in [subject_codes, schedules, professors, classrooms] if x]) >= 3:
            academic_completeness += 0.1  # Bonificación por riqueza
        
        coherence_score += min(0.2, academic_completeness)  # Máximo 0.2 de bonificación
        
        # COHERENCIA ESPACIAL: Verificar patrones de aulas
        if classrooms and len(classrooms) > 1:
            # Verificar que no hay aulas duplicadas o conflictivas
            room_identifiers = set()
            has_duplicates = False
            for room in classrooms:
                if room.identifier.lower() in room_identifiers:
                    has_duplicates = True
                    break
                room_identifiers.add(room.identifier.lower())
            
            if has_duplicates:
                coherence_score -= 0.1  # Penalización leve por duplicados
        
        # Normalizar coherencia entre 0.0 y 1.0
        coherence_score = max(0.0, min(1.0, coherence_score))


        # CÁLCULO FINAL: Combinación ponderada de las 3 dimensiones
        overall_confidence = (
            completeness_score * 0.3 +  # 30% - ¿Tenemos datos suficientes?
            quality_score * 0.5 +       # 50% - ¿Son datos de buena calidad?
            coherence_score * 0.2       # 20% - ¿Son datos coherentes?
        )
        
        # Ajuste final: penalización si no hay datos mínimos
        if total_entities == 0:
            overall_confidence = 0.0
        elif total_entities == 1:
            overall_confidence *= 0.7  # Penalización por datos muy escasos
        
        # Normalizar resultado final
        return max(0.0, min(1.0, overall_confidence))
    
    def _calculate_confidence_for_match(
        self, 
        match: re.Match, 
        context: str, 
        entity_type: str
    ) -> float:
        """
        Calcula la confianza de una coincidencia basada en contexto.
        
        Args:
            match: Coincidencia regex
            context: Contexto circundante
            entity_type: Tipo de entidad ('subject_code', 'professor', 'schedule', etc.)
            
        Returns:
            Puntuación de confianza (0.0-1.0)
        """
        if entity_type == 'subject_code':
            return self._calculate_subject_code_confidence(match, context)
        elif entity_type == 'professor':
            return self._calculate_professor_confidence_simple(match, context)
        elif entity_type == 'classroom':
            return self._calculate_classroom_confidence_simple(match, context)

        # Para otros tipos de entidad (implementar más tarde)
        return 0.5
    
    def _calculate_subject_code_confidence(self, match: re.Match, context: str) -> float:
        """Calcula confianza específica para códigos de asignatura."""
        base_confidence = 0.7  # Confianza base neutral (sin considerar paréntesis)
        context_lower = context.lower()
        
        # Bonificaciones por contexto académico positivo
        positive_terms = {
            'asignatura': 0.2,
            'código': 0.2, 
            'materia': 0.15,
            'curso': 0.15,
            'subject': 0.2,
            'créditos': 0.1,
            'ects': 0.1
        }
        
        for term, bonus in positive_terms.items():
            if term in context_lower:
                base_confidence += bonus
                break  # Solo aplicar una bonificación
        
        # Penalizaciones por contexto no académico
        negative_terms = {
            'teléfono': 0.4,
            'dirección': 0.3,
            'precio': 0.4,
            'euros': 0.4,
            'fecha': 0.2,
            'número': 0.2,
            'calle': 0.3
        }
        
        for term, penalty in negative_terms.items():
            if term in context_lower:
                base_confidence -= penalty
                break  # Solo aplicar una penalización
        
        # Bonificación por patrones académicos cercanos
        if any(word in context_lower for word in ['profesor', 'docente', 'aula', 'horario']):
            base_confidence += 0.1
        
        # Normalizar entre 0.0 y 1.0
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_professor_confidence_simple(self, match: re.Match, context: str) -> float:
        """Calcula confianza para profesores (versión simple)."""
        base_confidence = 0.6
        context_lower = context.lower()
        
        # Bonificaciones básicas por contexto académico
        if any(term in context_lower for term in ['profesor', 'profesora', 'docente', 'dr.', 'prof.']):
            base_confidence += 0.2
        
        # Bonificación adicional por términos relacionados
        if any(term in context_lower for term in ['impartir', 'imparte', 'enseña', 'coordinador']):
            base_confidence += 0.1
        
        # Penalizaciones básicas por contexto no académico
        if any(term in context_lower for term in ['estudiante', 'alumno', 'alumna', 'teléfono', 'dirección']):
            base_confidence -= 0.3
        
        # Penalización por contexto de matrícula/administración
        if any(term in context_lower for term in ['matrícula', 'expediente', 'nota', 'calificación']):
            base_confidence -= 0.2
        
        # Normalizar entre 0.0 y 1.0
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_classroom_confidence_simple(self, match: re.Match, context: str) -> float:
        """Calcula confianza para aulas (versión simple)."""
        base_confidence = 0.65
        context_lower = context.lower()
        
        # Bonificaciones por contexto académico espacial
        if any(term in context_lower for term in ['aula', 'laboratorio', 'seminario', 'clase']):
            base_confidence += 0.2
        
        # Bonificación adicional por términos de ubicación
        if any(term in context_lower for term in ['edificio', 'planta', 'piso']):
            base_confidence += 0.1
        
        # Bonificación por términos de actividad académica
        if any(term in context_lower for term in ['práctica', 'teoría', 'examen']):
            base_confidence += 0.05
        
        # Penalizaciones por contexto no espacial
        if any(term in context_lower for term in ['profesor', 'estudiante', 'nombre']):
            base_confidence -= 0.1
        
        # Penalización fuerte por contexto personal/administrativo
        if any(term in context_lower for term in ['teléfono', 'email', 'dirección', 'matrícula']):
            base_confidence -= 0.3
        
        # Normalizar entre 0.0 y 1.0
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_schedule_confidence(self, candidate: Dict, text: str) -> float:
        """Calcula confianza específica para horarios."""
        base_confidence = 0.7
        
        # Bonificación por tener hora de fin (rango completo)
        if candidate['end_time']:
            base_confidence += 0.1
        
        # Bonificación por contexto académico en el texto combinado
        combined_text = candidate['full_text'].lower()
        if any(term in combined_text for term in ['clase', 'asignatura', 'materia', 'curso']):
            base_confidence += 0.1
        
        # Bonificación por horarios típicos académicos
        start_hour = candidate['start_time'].hour
        if 8 <= start_hour <= 20:  # Horario académico típico
            base_confidence += 0.05
        
        # Penalización por horarios extraños
        if start_hour < 7 or start_hour > 22:
            base_confidence -= 0.2
        
        # Bonificación por días laborables vs fin de semana
        if candidate['day'] in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']:
            base_confidence += 0.05
        
        # Normalizar entre 0.0 y 1.0
        return max(0.0, min(1.0, base_confidence))
    
    
    def _clean_subject_code(self, raw_code: str) -> str:
        """Limpia y normaliza un código de asignatura."""
        # Remover paréntesis y separadores
        code = re.sub(r'[().\-\s]', '', raw_code)
        
        # Normalizar a mayúsculas
        return code.upper()
    
    def _clean_professor_name(self, raw_name: str) -> str:
        """Limpia y normaliza un nombre de profesor."""
        # Quitar títulos comunes al principio
        name = re.sub(r'^(Dr\.?|Dra\.?|Prof\.?|Profa\.?|D\.?|Dña\.?)\s*', '', raw_name, flags=re.IGNORECASE)
        
        # Limpiar caracteres problemáticos
        name = re.sub(r'[().\-]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def _clean_classroom_identifier(self, raw_identifier: str) -> str:
        """Limpia y normaliza un identificador de aula."""
        # Normalizar espacios
        identifier = re.sub(r'\s+', ' ', raw_identifier)
        
        # Capitalizar palabras importantes
        identifier = re.sub(r'\b(aula|laboratorio|seminario|lab)\b', 
                           lambda m: m.group(0).title(), identifier, flags=re.IGNORECASE)
        
        # Limpiar caracteres problemáticos pero mantener guiones para códigos
        identifier = re.sub(r'[().]', ' ', identifier)
        identifier = re.sub(r'\s+', ' ', identifier)
        
        return identifier.strip()
    
    
    def _find_all_time_matches(self, text: str) -> List[Dict]:
        """Encuentra todas las coincidencias de tiempo en el texto."""
        time_matches = []
        
        for pattern in self.compiled_time_patterns:
            for match in pattern.finditer(text):
                time_data = self._parse_time_match(match)
                if time_data:  # Solo si es válido
                    time_matches.append({
                        'start_time': time_data['start'],
                        'end_time': time_data['end'],
                        'raw_text': match.group(0),
                        'position': (match.start(), match.end())
                    })
        
        return time_matches
    
    def _find_all_day_matches(self, text: str) -> List[Dict]:
        """Encuentra todas las coincidencias de días en el texto."""
        day_matches = []
        
        for pattern in self.compiled_day_patterns:
            for match in pattern.finditer(text):
                days = self._parse_day_match(match)
                for day in days:  # Un patrón puede tener múltiples días (L-M-X)
                    day_matches.append({
                        'day': day,
                        'raw_text': match.group(0),
                        'position': (match.start(), match.end())
                    })
        
        return day_matches
    
    def _parse_time_match(self, match: re.Match) -> Optional[Dict]:
        """Parsea una coincidencia de tiempo a objetos time de Python."""
        try:
            text = match.group(0)
            
            # Buscar patrón de rango (9:00-11:00, 9h-11h)
            range_patterns = [
                r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})',     # 9:00-11:00
                r'(\d{1,2})h\s*[-–]\s*(\d{1,2})h',                   # 9h-11h
                r'(\d{1,2}):(\d{2})\s*a\s*(\d{1,2}):(\d{2})',        # 9:00 a 11:00
            ]
            
            for pattern in range_patterns:
                range_match = re.search(pattern, text)
                if range_match:
                    groups = range_match.groups()
                    if len(groups) == 4:  # Formato completo con minutos
                        start_hour, start_min, end_hour, end_min = map(int, groups)
                    else:  # Formato solo horas (9h-11h)
                        start_hour, end_hour = map(int, [groups[0], groups[1]])
                        start_min = end_min = 0
                    
                    return {
                        'start': time(start_hour, start_min),
                        'end': time(end_hour, end_min)
                    }
            
            # Buscar tiempo simple (9:00, 9h)
            simple_patterns = [
                r'(\d{1,2}):(\d{2})',  # 9:00
                r'(\d{1,2})h',         # 9h
            ]
            
            for pattern in simple_patterns:
                simple_match = re.search(pattern, text)
                if simple_match:
                    groups = simple_match.groups()
                    hour = int(groups[0])
                    minute = int(groups[1]) if len(groups) > 1 else 0
                    
                    return {
                        'start': time(hour, minute),
                        'end': None  # Sin hora de fin
                    }
            
            return None
        except (ValueError, AttributeError, IndexError):
            return None
    
    def _parse_day_match(self, match: re.Match) -> List[str]:
        """Parsea una coincidencia de días a lista de días individuales."""
        text = match.group(0).lower()
        days = []
        
        # Mapeo de abreviaciones y nombres completos
        day_mapping = {
            'l': 'Lunes', 'lunes': 'Lunes',
            'm': 'Martes', 'martes': 'Martes', 'ma': 'Martes',
            'x': 'Miércoles', 'miércoles': 'Miércoles', 'mi': 'Miércoles',
            'j': 'Jueves', 'jueves': 'Jueves', 'ju': 'Jueves',
            'v': 'Viernes', 'viernes': 'Viernes', 'vi': 'Viernes',
            's': 'Sábado', 'sábado': 'Sábado', 'sa': 'Sábado',
            'd': 'Domingo', 'domingo': 'Domingo', 'do': 'Domingo'
        }
        
        # Detectar formato de días separados (L-M-X, L,M,X)
        if re.search(r'[lmxjvsd][-,\s]*[lmxjvsd]', text):
            # Extraer cada letra/abreviación individual
            day_parts = re.findall(r'[lmxjvsd]+', text)
            for part in day_parts:
                for char in part:
                    if char in day_mapping:
                        day_name = day_mapping[char]
                        if day_name not in days:
                            days.append(day_name)
        else:
            # Buscar nombres completos o abreviaciones individuales
            for key, day_name in day_mapping.items():
                if key in text:
                    if day_name not in days:
                        days.append(day_name)
        
        return days
    
    def _associate_times_with_days(self, time_matches: List[Dict], day_matches: List[Dict], text: str) -> List[Dict]:
        """Asocia tiempos con días basándose en proximidad espacial."""
        candidates = []
        
        for time_match in time_matches:
            # Encontrar el día más cercano (antes o después)
            closest_day = self._find_closest_day(time_match, day_matches)
            
            if closest_day:
                candidates.append({
                    'day': closest_day['day'],
                    'start_time': time_match['start_time'],
                    'end_time': time_match['end_time'],
                    'full_text': self._extract_combined_text(time_match, closest_day, text),
                    'position': (
                        min(time_match['position'][0], closest_day['position'][0]),
                        max(time_match['position'][1], closest_day['position'][1])
                    )
                })
        
        return candidates
    
    def _find_closest_day(self, time_match: Dict, day_matches: List[Dict]) -> Optional[Dict]:
        """Encuentra el día más cercano a una coincidencia de tiempo."""
        if not day_matches:
            return None
        
        time_pos = time_match['position'][0]  # Posición del tiempo en el texto
        closest_day = None
        min_distance = float('inf')
        
        for day_match in day_matches:
            day_pos = day_match['position'][0]
            distance = abs(time_pos - day_pos)
            
            # Preferir días que estén antes del tiempo (más natural)
            if day_pos < time_pos:
                distance *= 0.8  # Reducir distancia para días anteriores
            
            if distance < min_distance:
                min_distance = distance
                closest_day = day_match
        
        # Solo asociar si la distancia es razonable (menos de 100 caracteres)
        return closest_day if min_distance < 100 else None
    
    def _extract_combined_text(self, time_match: Dict, day_match: Dict, text: str) -> str:
        """Extrae el texto combinado que incluye día y tiempo."""
        start_pos = min(time_match['position'][0], day_match['position'][0])
        end_pos = max(time_match['position'][1], day_match['position'][1])
        
        # Expandir ligeramente para incluir contexto
        start_pos = max(0, start_pos - 5)
        end_pos = min(len(text), end_pos + 5)
        
        return text[start_pos:end_pos].strip()
    
    def _validate_time_logic(self, candidate: Dict) -> bool:
        """Valida que el horario tenga lógica temporal correcta."""
        start_time = candidate['start_time']
        end_time = candidate['end_time']
        
        # Si no hay hora de fin, es válido
        if not end_time:
            return True
        
        # La hora de inicio debe ser anterior a la de fin
        if start_time >= end_time:
            return False
        
        # Validar rangos razonables académicos (no clases de más de 6 horas)
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        duration_minutes = end_minutes - start_minutes
        
        if duration_minutes > 360:  # Más de 6 horas
            return False
        
        # Validar horarios académicos razonables (6:00-23:00)
        if start_time.hour < 6 or start_time.hour > 23:
            return False
        if end_time and (end_time.hour < 6 or end_time.hour > 23):
            return False
        
        return True
    
    def _create_schedule_key(self, candidate: Dict) -> str:
        """Crea un identificador único para evitar horarios duplicados."""
        day = candidate['day']
        start_time = candidate['start_time']
        end_time = candidate['end_time']
        
        if end_time:
            return f"{day}_{start_time.hour:02d}:{start_time.minute:02d}-{end_time.hour:02d}:{end_time.minute:02d}"
        else:
            return f"{day}_{start_time.hour:02d}:{start_time.minute:02d}"
    

    def _detect_classroom_type(self, raw_match: str) -> Optional[str]:
        """Detecta el tipo de aula basándose en el texto."""
        match_lower = raw_match.lower()
        
        # Orden importa: más específicos primero
        type_patterns = {
            'Aula Magna': ['aula magna', 'magna'],
            'Aula de Informática': ['informática', 'ordenadores', 'computación'],
            'Laboratorio': ['lab', 'laboratorio'],
            'Seminario': ['seminario', 'sem'],
            'Biblioteca': ['biblioteca', 'bib'],
            'Salón de Actos': ['salón de actos', 'actos'],
            'Aula': ['aula']  # Genérico, debe ir al final
        }
        
        for room_type, keywords in type_patterns.items():
            if any(keyword in match_lower for keyword in keywords):
                return room_type
        
        return None
    
    def _extract_classroom_location(self, raw_match: str) -> Optional[str]:
        """Extrae información de ubicación si está disponible."""
        # Buscar patrones de edificio/planta (A-301, B2-15, Edificio A, etc.)
        location_patterns = [
            r'([A-Z]\d*-?\d+)',           # A-301, B2-15, C123
            r'(Edificio\s+[A-Z])',        # Edificio A
            r'(Planta\s+\d)',             # Planta 2
            r'(\d+º\s*Piso)',             # 2º Piso
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, raw_match, re.IGNORECASE)
            if location_match:
                return location_match.group(1)
        
        return None
    
    def _get_context_around_match(self, text: str, match: re.Match, radius: int = 50) -> str:
        """Extrae contexto alrededor de una coincidencia."""
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        return text[start:end]


# Instancia global para reutilización
academic_parser = AcademicTextParser()