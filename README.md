# Sistema de Detección de Conflictos Académicos

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14%2B-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## 📋 Descripción General

Este proyecto consiste en una plataforma integral **Full-Stack** diseñada para la gestión, ingesta y validación de la planificación académica universitaria. Su núcleo es un **motor algorítmico de detección de conflictos** que cruza horarios, disponibilidad docente, aules y recursos físicos en tiempo real para garantizar la viabilidad de los cuadros horarios.

El sistema resuelve la complejidad de la gestión académica mediante una arquitectura desacoplada: un backend robusto basado en **Domain-Driven Design (DDD)** para la lógica de negocio compleja, y un frontend reactivo optimizado para la visualización de grandes volúmenes de datos temporales.

---

## 🚀 Características Principales

### 🧠 Motor de Conflictos (Core)
El corazón del sistema es un motor determinista que evalúa reglas de negocio estrictas:
* **Colisiones Espacio-Temporales:** Detección de solapamientos de aulas y recursos compartidos.
* **Ubicuidad Docente:** Validación de que un profesor no tenga asignadas dos sesiones simultáneas en ubicaciones distintas.
* **Conciliación:** Verificación de reglas de descanso y jornadas máximas (configurable por docente).

### 🔄 Arquitectura de Ingesta Dinámica
El sistema implementa un pipeline ETL especializado para la ingesta de "Fichas Docentes" y "Horarios".
* **Asociación de Contexto 'Lazy':** Una característica clave de la arquitectura es que **el extractor de fichas no persiste las menciones (especialidades) de forma estática**.
* Las menciones se asocian dinámicamente durante el procesamiento de los horarios. Esto permite que una misma asignatura troncal pueda pertenecer a múltiples contextos sin duplicidad de datos, garantizando la coherencia e integridad referencial por titulación en tiempo de ejecución.

### 📊 Gestión Visual e Interactiva
* **Gridmaster UI:** Interfaz de rejilla avanzada para la manipulación directa de slots horarios.
* **Filtrado Contextual:** Capacidad para filtrar vistas por Grado, Curso, Grupo y Semestre simultáneamente.
* **Reportes en Tiempo Real:** Feedback inmediato sobre conflictos generados tras cualquier modificación.

---

## 🏗️ Arquitectura y Stack Técnico

El proyecto sigue una arquitectura hexagonal (Ports & Adapters) simplificada, orientada al dominio.

### Backend (Python / FastAPI)
* **Domain-Driven Design (DDD):** El código está organizado por contextos delimitados (`modulos/docencia`, `modulos/recursos`, `core/conflictos`), aislando la lógica de negocio de la infraestructura tecnológica.
* **Patrón Unit of Work (UoW):** Se utiliza UoW junto con el patrón Repository para garantizar la atomicidad de las operaciones complejas. Todas las modificaciones de una transacción de planificación se confirman (commit) o rechazan (rollback) en bloque, asegurando propiedades **ACID**.
* **SQLAlchemy 2.0:** ORM moderno utilizado para la gestión de persistencia, aprovechando características asíncronas y tipado estricto.

### Frontend (Next.js / TypeScript)
* **App Router:** Uso de las últimas capacidades de enrutamiento y Server Components de Next.js para optimizar la carga inicial.
* **Estado Global:** Gestión de estado eficiente para manejar la complejidad de la interfaz de edición de horarios.
* **Tailwind CSS:** Diseño de sistema de componentes atómicos para una UI consistente y mantenible.

---

## 🛠️ Getting Started (Guía de Instalación)

Esta sección detalla los pasos para levantar toda la aplicación (backend + frontend) en una máquina local.

La estructura relevante del proyecto es:

```text
TFG/
  aplicacion/
    backend/     # Código del backend (FastAPI)
    database/    # Modelos y utilidades de base de datos (SQLite)
    frontend/    # Código del frontend (Next.js)
```

### 1. Requisitos Previos

Asegúrate de tener instalado:

* **Python** ≥ 3.11
  ```powershell
  python --version
  ```
* **Node.js** (LTS 18.x o 20.x)
  ```powershell
  node --version
  ```
* **pnpm** (Gestor de paquetes recomendado para el frontend)
  ```powershell
  npm install -g pnpm
  ```

En Windows, se recomienda usar **PowerShell** para los comandos.

---

### 2. Levantar el Backend (FastAPI)

El backend expone la API REST y la documentación interactiva.

#### 2.1. Configuración del Entorno

Desde la carpeta del backend:

```powershell
cd aplicacion/backend

# Crear entorno virtual (solo la primera vez)
python -m venv .venv

# Activar el entorno virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
```
> Verás `(.venv)` delante del prompt si está activo.

#### 2.2. Instalación de Dependencias

Con el entorno virtual activo:

```powershell
pip install -r requirements.txt
```
> Esto instalará FastAPI, SQLAlchemy, y las librerías de procesamiento de PDF (PyPDF2, etc.).

#### 2.3. Iniciar el Servidor

```powershell
python -m uvicorn main:app --reload
```

El backend quedará disponible en:
* **API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 3. Levantar el Frontend (Next.js)

La interfaz web permite interactuar con el sistema de horarios.

#### 3.1. Instalación de Dependencias

Desde la carpeta del frontend (en una nueva terminal):

```powershell
cd aplicacion/frontend
pnpm install
```

#### 3.2. Configuración de Entorno

Crea un archivo `.env.local` en `aplicacion/frontend` para conectar con el backend:

```powershell
# Crear archivo si no existe
ni .env.local
```

Añade el siguiente contenido al archivo `.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### 3.3. Iniciar Servidor de Desarrollo

```powershell
pnpm dev
```

El frontend estará accesible en:
* **Web**: [http://localhost:3000](http://localhost:3000)

---

### 4. Flujo de Trabajo Típico

Para retomar el desarrollo en sesiones futuras:

1. **Terminal 1 (Backend):**
   ```powershell
   cd aplicacion/backend
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn main:app --reload
   ```

2. **Terminal 2 (Frontend):**
   ```powershell
   cd aplicacion/frontend
   pnpm dev
   ```

3. **Navegador:**
   Abra [http://localhost:3000](http://localhost:3000) para ver la aplicación.

---

## 5. Notas de Desarrollo

* **Base de Datos:** El entorno de desarrollo utiliza SQLite (`dev.db` en `aplicacion/database/`). Las tablas se generan automáticamente al iniciar el backend.
* **Scripts de Utilidad:** Para ejecutar scripts de mantenimiento (como `inspect_db.py`), usa el entorno virtual del backend:
  ```powershell
  python ..\database\inspect_db.py
  ```
* **Git:** La carpeta `.venv`, `node_modules`, archivos compilados y la base de datos `dev.db` están excluidos del control de versiones.

---
*Trabajo de Fin de Grado - Ingeniería Informática*
