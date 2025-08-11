# ROADMAP BACKEND TFG - Finalización en 1 Semana

## 1. Objetivo del Backend
Completar la lógica de negocio para detección automática de conflictos en horarios académicos a partir de PDFs, con API REST funcional y testeos validados.

## 2. Fases y Entregables (7 días)

### 📅 **FASE 1: Infraestructura Base (Días 1-2)**

**Día 1:**
- Completar `database/session.py` con gestión de conexiones SQLAlchemy
- Implementar contenido de todos los archivos CRUD (create, read, update, delete)
- Verificar y completar modelos Pydantic en `schemas/`
- Crear archivo `constants/enums.py` con tipos de restricciones, días semana, etc.

**Día 2:**
- Implementar todos los endpoints en `api/v0/` 
- Configurar dependencias de inyección de BD en endpoints
- Testear CRUD básico con datos de prueba
- Documentar API con ejemplos en docstrings

### 📅 **FASE 2: Lógica de Negocio Core (Días 3-4)**

**Día 3:**
- Implementar `core/ocr.py`: extracción de texto de PDFs con Tesseract
- Crear parsers para horarios y fichas de asignaturas
- Desarrollar funciones de normalización de datos extraídos

**Día 4:**
- Implementar `core/restricciones.py`: algoritmos de detección de conflictos
- Crear validadores para solapamientos de horarios, aulas duplicadas, disponibilidad profesores
- Integrar lógica de restricciones con modelos de BD

### 📅 **FASE 3: Endpoints Específicos del Dominio (Día 5)**

**Día 5:**
- Endpoint `/upload-pdf/` para carga de documentos
- Endpoint `/analyze-conflicts/` para procesamiento y detección
- Endpoint `/reports/conflicts/` para exportar resultados
- Middleware para manejo de archivos grandes
- Validaciones de tipos de archivo y tamaños

### 📅 **FASE 4: Testing y Validación (Días 6-7)**

**Día 6:**
- Crear tests unitarios para CRUD operations
- Tests de integración para endpoints principales
- Tests específicos para lógica de detección de conflictos
- Configurar pytest con cobertura mínima 80%

**Día 7:**
- Tests end-to-end con datos reales de PDFs
- Corrección de bugs encontrados
- Optimización de performance
- Documentación final de API

## 3. Criterios de Aceptación por Fase

### Fase 1:
- ✅ Todos los endpoints CRUD responden correctamente
- ✅ Base de datos SQLite funcional con datos de prueba
- ✅ Documentación OpenAPI generada automáticamente

### Fase 2:
- ✅ OCR extrae texto correctamente de PDFs de prueba
- ✅ Algoritmo detecta al menos 3 tipos de conflictos principales
- ✅ Datos extraídos se persisten en BD correctamente

### Fase 3:
- ✅ Upload de PDFs funcional con validaciones
- ✅ Endpoint de análisis retorna conflictos detectados
- ✅ Respuestas JSON bien estructuradas con códigos HTTP correctos

### Fase 4:
- ✅ Cobertura de tests ≥ 80%
- ✅ Pipeline de tests ejecuta sin errores
- ✅ Performance aceptable (<2s para análisis PDF típico)

## 4. Dependencias y Bloqueadores

**Dependencias externas:**
- Tesseract OCR instalado en sistema
- Bibliotecas Python: pytesseract, pdf2image, spacy

**Posibles bloqueadores:**
- Calidad OCR en PDFs de horarios complejos
- Performance en análisis de PDFs grandes
- Configuración correcta de Tesseract en Windows

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| OCR inexacto | Alta | Alto | Implementar múltiples estrategias de parsing + validación manual |
| Performance lenta | Media | Medio | Procesamiento asíncrono + límites de archivo |
| Bugs complejos | Media | Alto | Testing exhaustivo + datos de prueba variados |

## 6. Checklist "Listo para Frontend"

### API Endpoints:
- [ ] CRUD completo para todas las entidades
- [ ] `/upload-pdf/` funcional
- [ ] `/analyze-conflicts/` implementado
- [ ] `/reports/` con exportación de resultados
- [ ] Health check `/` operativo

### Contratos y Validaciones:
- [ ] Esquemas Pydantic completos con validaciones
- [ ] Respuestas JSON consistentes
- [ ] Códigos HTTP apropiados (200, 201, 400, 404, 422, 500)
- [ ] Manejo de errores estandarizado

### Documentación:
- [ ] OpenAPI/Swagger UI accesible en `/docs`
- [ ] Ejemplos de request/response en todos los endpoints
- [ ] Descripción clara de tipos de conflictos detectables

### Configuración:
- [ ] CORS configurado para desarrollo
- [ ] Variables de entorno documentadas
- [ ] Configuración dual SQLite/PostgreSQL validada

### Testing:
- [ ] Tests unitarios para lógica de negocio
- [ ] Tests de integración para endpoints
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
