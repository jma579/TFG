# ROADMAP BACKEND TFG - Finalización en 1 Semana

## 1. Objetivo del Backend

Implementar la lógica de negocio para detección automática de conflictos en horarios académicos, completar funcionalidades de OCR para PDFs y asegurar un backend robusto listo para frontend.

## 2. Fases y Entregables (7 días)

### 📅 **FASE 1: Lógica de Negocio Core - Validación de Sesiones (Días 1-2)**

**Día 1:**

- **PRIORIDAD CRÍTICA**: Implementar `core/deteccion_conflictos.py` con algoritmos de detección de conflictos
- Desarrollar validaciones de solapamientos: profesor, aula, asignatura en mismo horario
- Crear función para validar restricciones activas antes de crear/actualizar sesiones
- Integrar validaciones en `crud/sesion.py` (la nota ya indica que debe hacerse)

**Día 2:**

- Crear endpoints específicos para validación: `POST /v0/sesiones/validar`
- Implementar `POST /v0/restricciones/validar` usando schemas `ValidacionRestriccion` y `ResultadoValidacion`
- Definir contratos JSON claros para endpoints de validación
- Crear script de datos semilla: 1 grado, 1 mención, 2 aulas, 1 profesor, 2 asignaturas, 3 sesiones

### 📅 **FASE 2: Funcionalidades OCR y Procesamiento de PDFs (Días 3-4)**

**Día 3:**

- Implementar `core/ocr.py`: extracción de texto de PDFs con Tesseract
- Definir formato de salida del parser: lista de objetos `SesionCreate`
- Crear parsers específicos para horarios académicos (tablas, estructuras comunes)
- Usar PDFs de ejemplo del directorio `Horarios/` para testing

**Día 4:**

- Endpoint `POST /v0/upload-pdf/` para carga de documentos académicos
- Validaciones: tipos de archivo (.pdf), tamaño máximo (50MB ya configurado)
- Integrar OCR con validación de conflictos automática
- Endpoint `POST /v0/analyze-conflicts/` que combine OCR + detección

### 📅 **FASE 3: Endpoints de Dominio y Reportes (Día 5)**

**Día 5:**

- Definir contratos JSON para endpoints `/upload-pdf`, `/analyze-conflicts`, `/reports/conflicts`
- Implementar `GET /v0/reports/conflicts/` para exportar resultados de análisis
- Añadir ejemplos OpenAPI en endpoints existentes (ya funcionan pero falta documentación)
- Middleware para manejo de archivos grandes y respuestas asíncronas
- Mejorar mensajes de error y códigos HTTP consistentes

### 📅 **FASE 4: Testing Completo y Optimización (Días 6-7)**

**Día 6:**

- **Testing E2E prioritario**: casos de sesiones con solapes y violación de restricciones
- Tests unitarios para lógica de detección de conflictos (`core/restricciones.py`)
- Tests de integración para endpoints de validación y OCR
- Verificar que tests CRUD existentes sigan funcionando

**Día 7:**

- Tests end-to-end con PDFs reales del directorio `Horarios/`
- Optimización de performance para análisis de PDFs grandes
- Documentación final: ejemplos completos en Swagger UI
- Corrección de bugs y ajustes finales

## 3. Criterios de Aceptación por Fase

### Fase 1

- ✅ Función de detección de conflictos implementada y probada
- ✅ Endpoint `/v0/sesiones/validar` funcional con casos de prueba
- ✅ CRUD de sesiones integra validaciones antes de persistir
- ✅ Script de datos semilla ejecutable

### Fase 2

- ✅ OCR extrae texto correctamente de PDFs de horarios del proyecto
- ✅ Parser convierte texto a objetos `SesionCreate` válidos
- ✅ Al menos 3 formatos de PDF diferentes procesados correctamente

### Fase 3

- ✅ Upload de PDFs funcional con validaciones de tipo y tamaño
- ✅ Endpoint de análisis combina OCR + detección automática de conflictos
- ✅ Respuestas JSON bien estructuradas con códigos HTTP correctos
- ✅ Documentación OpenAPI completa con ejemplos

### Fase 4

- ✅ Tests E2E funcionan con PDFs reales del directorio `Horarios/`
- ✅ Cobertura de tests ≥ 80% incluyendo lógica de negocio
- ✅ Performance aceptable (<3s para PDF típico con OCR + análisis)
- ✅ Documentación técnica actualizada

## 4. Dependencias y Bloqueadores

**Dependencias externas ya identificadas:**

- Tesseract OCR (instalación en sistema Windows)
- Bibliotecas Python: `pytesseract`, `pdf2image`, `pillow`

**Posibles bloqueadores críticos:**

- Calidad OCR variable según tipo de PDF (tablas, escaneos, formato)
- Complejidad de parsing de horarios académicos (estructuras no estándar)
- Performance con PDFs grandes y múltiples análisis simultáneos

## 5. Riesgos y Mitigaciones

| Riesgo            | Probabilidad | Impacto | Mitigación                                                        |
| ----------------- | ------------ | ------- | ------------------------------------------------------------------ |
| OCR inexacto      | Alta         | Alto    | Implementar múltiples estrategias de parsing + validación manual |
| Performance lenta | Media        | Medio   | Procesamiento asíncrono + límites de archivo                     |
| Bugs complejos    | Media        | Alto    | Testing exhaustivo + datos de prueba variados                      |

## 6. Checklist "Listo para Frontend" (Actualizado)

### API Endpoints ✅ PARCIALMENTE COMPLETADO

- [X] CRUD completo para todas las entidades (YA IMPLEMENTADO)
- [X] Health check `/` operativo (YA IMPLEMENTADO)
- [ ] `POST /v0/sesiones/validar` para validación previa
- [ ] `POST /v0/upload-pdf/` funcional con manejo de archivos
- [ ] `POST /v0/analyze-conflicts/` para análisis automático
- [ ] `GET /v0/reports/conflicts/` para exportar resultados

### Contratos y Validaciones ✅ MAYORMENTE COMPLETADO

- [X] Esquemas Pydantic completos con validaciones (YA IMPLEMENTADO)
- [X] Respuestas JSON consistentes (YA IMPLEMENTADO)
- [X] Códigos HTTP apropiados en endpoints existentes (YA IMPLEMENTADO)
- [ ] Contratos específicos para endpoints de validación y OCR
- [ ] Manejo de errores específicos de lógica de negocio

### Documentación ✅ BASE IMPLEMENTADA

- [X] OpenAPI/Swagger UI accesible en `/docs` (YA FUNCIONA)
- [ ] Ejemplos de request/response en endpoints existentes
- [ ] Documentación de tipos de conflictos detectables
- [ ] Especificación de formatos PDF soportados

### Configuración ✅ COMPLETADO

- [X] CORS configurado para desarrollo (YA IMPLEMENTADO)
- [X] Variables de entorno documentadas (YA IMPLEMENTADO)
- [X] Configuración dual SQLite/PostgreSQL validada (YA IMPLEMENTADO)
- [X] Gestión de sesiones de BD funcional (YA IMPLEMENTADO)

### Testing 🔄 EN PROGRESO

- [X] Tests básicos de schemas y models (YA IMPLEMENTADO)
- [X] Tests CRUD existentes (YA IMPLEMENTADO)
- [ ] Tests específicos para lógica de detección de conflictos
- [ ] Tests de integración para endpoints de validación
- [ ] Tests E2E con PDFs reales
- [ ] Cobertura ≥ 80%

## 7. Recomendaciones Técnicas Adicionales

### Inmediatas:

- Usar `asyncio` para operaciones de OCR (no bloquear API)
- Implementar cache Redis para resultados de análisis frecuentes
- Añadir logging estructurado con `loguru`
- Configurar rate limiting para endpoints de upload

### Post-semana:

- Migrar a PostgreSQL con Alembic
- Implementar autenticación JWT
- Añadir WebSockets para progress de análisis largos
- Containerizar con Docker

---

## 8. Estado Actual del Proyecto

### ✅ **Completado (70%):**

- Arquitectura FastAPI de 5 capas implementada
- Modelos SQLAlchemy completos
- Configuración de entornos (SQLite/PostgreSQL)
- Estructura de API versionada (v0/)
- CORS y health check configurados
- Organización modular excelente

### ⚠️ **Pendiente (30%):**

- Implementación específica de CRUD operations
- Gestión de sesiones de BD
- Lógica core: OCR y detección de conflictos
- Endpoints específicos del dominio
- Testing completo
- Documentación detallada

---

**Tiempo estimado total: 6-7 días de desarrollo intensivo**
**Resultado: Backend completamente funcional y listo para desarrollo de frontend**

---

## Notas de Implementación

### Prioridades Críticas:

1. **Database session management** - Sin esto, ningún endpoint funcionará
2. **CRUD implementations** - Base para toda la funcionalidad
3. **OCR pipeline** - Funcionalidad core del proyecto
4. **Conflict detection** - Valor diferencial de la aplicación

### Archivos Clave a Implementar:

- `backend/database/session.py`
- `backend/crud/*.py` (contenido específico)
- `backend/core/ocr.py`
- `backend/core/restricciones.py`
- `backend/api/v0/*.py` (endpoints)
- Tests en `backend/test_*.py`

### Dependencias Críticas:

```bash
pip install pytesseract pdf2image pillow spacy pytest pytest-cov
```

### Configuración Tesseract Windows:

- Descargar Tesseract desde GitHub releases
- Añadir al PATH o configurar en `config.py`
- Instalar pack de idioma español si es necesario
