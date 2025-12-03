# Sistema de Detección de Conflictos Académicos – TFG

Este proyecto está dividido en dos partes principales:

* **Backend**: API REST construida con **FastAPI** y **SQLAlchemy**.
* **Frontend**: aplicación web construida con **Next.js** (React) y gestionada con **pnpm**.

La estructura relevante del proyecto es:

```text
TFG/
  aplicacion/
    backend/     # Código del backend (FastAPI)
      main.py
      requirements.txt
      ...
    database/    # Modelos y utilidades de base de datos (SQLite)
      models.py
      dev.db
      ...
    frontend/    # Código del frontend (Next.js)
      package.json
      pnpm-lock.yaml
      ...
```

---

## 1. Requisitos previos

Asegúrate de tener instalado:

* **Python** ≥ 3.11
  Puedes comprobarlo con:

  ```bash
  python --version
  ```
* **Node.js** (recomendado LTS 18.x o 20.x)

  ```bash
  node --version
  ```
* **pnpm** (gestor de paquetes para el frontend)
  Si no lo tienes:

  ```bash
  npm install -g pnpm
  ```

En Windows, se recomienda usar **PowerShell** para los comandos.

---

## 2. Levantar el backend (FastAPI)

### 2.1. Crear y activar entorno virtual

Desde la carpeta del backend:

```powershell
cd aplicacion/backend

# Crear entorno virtual (solo la primera vez)
python -m venv .venv

# Activar el entorno virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
```

Verás algo como `(.venv) PS C:\Users\...` delante del prompt si está activo.

### 2.2. Instalar dependencias del backend

Con el entorno virtual activo:

```powershell
pip install -r requirements.txt
```

Esto instalará todas las librerías necesarias (FastAPI, SQLAlchemy, PyPDF2, PyMuPDF, pdfplumber, etc.).

### 2.3. Iniciar el servidor backend

Con el venv activo y estando en `aplicacion/backend`:

```powershell
python -m uvicorn main:app --reload
```

El backend quedará escuchando típicamente en:

* **API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Documentación interactiva (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

En los logs deberías ver algo similar a:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:main:🚀 Iniciando Sistema de Detección de Conflictos Académicos
INFO:main:📊 Conectando a base de datos: sqlite (pysqlite)
INFO:main:✅ Tablas de base de datos verificadas/creadas (entorno debug)
```

> La base de datos de desarrollo es un SQLite (`dev.db`) bajo `aplicacion/database/`.
> Las tablas se crean/verifican automáticamente al arrancar gracias a SQLAlchemy.

---

## 3. Levantar el frontend (Next.js + pnpm)

### 3.1. Instalar dependencias del frontend

En otra terminal (puedes dejar el backend corriendo), ve a la carpeta del frontend:

```powershell
cd aplicacion/frontend
pnpm install
```

Esto instalará todas las dependencias definidas en `package.json` y `pnpm-lock.yaml` dentro de `node_modules/`.

### 3.2. Configurar variables de entorno del frontend

El frontend necesita saber dónde está el backend.
Para ello se usa un fichero `.env.local` en `aplicacion/frontend`.

Comprueba si existe algún ejemplo:

```powershell
cd aplicacion/frontend
ls .env*
```

Si no hay ninguno, crea uno:

```powershell
ni .env.local
```

Y añade al menos:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> Esto hace que el frontend haga las peticiones a la API local de FastAPI.

### 3.3. Iniciar el servidor de desarrollo del frontend

Con las dependencias instaladas y `.env.local` configurado:

```powershell
cd aplicacion/frontend
pnpm dev
```

Si todo va bien, verás algo como:

```text
> next dev --turbopack
ready - started server on 0.0.0.0:3000
```

El frontend estará accesible en:

* **Frontend**: [http://localhost:3000](http://localhost:3000)

---

## 4. Flujo típico de arranque

1. **Terminal 1 – Backend**

   ```powershell
   cd aplicacion/backend
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn main:app --reload
   ```

2. **Terminal 2 – Frontend**

   ```powershell
   cd aplicacion/frontend
   pnpm dev
   ```

3. Abrir en el navegador:

   * [http://localhost:3000](http://localhost:3000) → interfaz web (frontend)
   * [http://localhost:8000/docs](http://localhost:8000/docs) → documentación de la API (backend)

---

## 5. Notas adicionales

* El entorno virtual del backend está en `aplicacion/backend/.venv` y **no se versiona** (está en `.gitignore`).

* Los archivos PDF, TXT y otros documentos generados en la raíz del proyecto no se versionan.

* Los scripts auxiliares de base de datos (`aplicacion/database/init_db.py`, `inspect_db.py`, etc.) deben ejecutarse usando el mismo entorno virtual del backend, por ejemplo:

  ```powershell
  cd aplicacion/backend
  .\.venv\Scripts\Activate.ps1

  # Ejecutar un script de database:
  python ..\database\inspect_db.py
  ```

* Para ejecutar tests (si están configurados), también se usan las dependencias de `requirements.txt` y `pytest` dentro del mismo venv.

---

## 6. Problemas frecuentes

* **`ModuleNotFoundError` en Python**
  Asegúrate de:

  * Tener el venv activado.
  * Haber ejecutado `pip install -r requirements.txt` en `aplicacion/backend`.

* **`next: command not found` o similar**
  Asegúrate de:

  * Haber ejecutado `pnpm install` en `aplicacion/frontend`.
  * Lanzar el servidor con `pnpm dev` desde `aplicacion/frontend`.

* **El frontend no llega al backend**
  Verifica:

  * Que el backend está levantado en `http://localhost:8000`.
  * Que `NEXT_PUBLIC_API_BASE_URL` en `.env.local` apunta a esa URL.

---

Con estos pasos deberías poder levantar toda la aplicación (backend + frontend) en una máquina nueva siguiendo un flujo reproducible, ideal para tu TFG y para cualquier persona que necesite revisar el proyecto.
