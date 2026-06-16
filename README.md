# Centro de Estudios Pergamino

Aplicación web en Flask para publicar y visualizar:

- Guías de estudio en PDF.
- Presentaciones PDF con visor interactivo.
- Podcast en audio.
- Reseñas de libros, documentos o materiales.
- Logo personalizado subido desde el panel de administración.

La estética visual usa tonos pergamino, tipografía tradicional y paneles ornamentales sobrios.

## 1. Estructura

```text
centro_estudios_pergamino/
├── app.py
├── requirements.txt
├── Procfile
├── render.yaml
├── static/
│   ├── css/style.css
│   ├── js/pdf_viewer.js
│   └── img/default_logo.svg
└── templates/
```

## 2. Uso local

```bash
cd centro_estudios_pergamino
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
set ADMIN_PASSWORD=tu_clave_segura
set SECRET_KEY=una_clave_larga_aleatoria
python app.py
```

Abre:

```text
http://127.0.0.1:5000
```

Panel de administración:

```text
http://127.0.0.1:5000/admin
```

Si no defines `ADMIN_PASSWORD`, la clave local por defecto es:

```text
cambiar-esta-clave
```

Cámbiala siempre antes de publicar.

## 3. Subida de contenido

Desde el panel puedes:

1. Cambiar el nombre del sitio.
2. Subir el logo.
3. Publicar guías PDF.
4. Publicar presentaciones PDF.
5. Publicar podcast en MP3, WAV, M4A u OGG.
6. Publicar reseñas.
7. Eliminar materiales y reseñas.

## 4. Despliegue en Render

### Opción recomendada: Blueprint con `render.yaml`

1. Sube esta carpeta a un repositorio de GitHub.
2. En Render, crea un nuevo **Blueprint** usando ese repositorio.
3. Render leerá `render.yaml`.
4. Define la variable `ADMIN_PASSWORD` con una clave segura.
5. Despliega.

El archivo `render.yaml` ya define:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: gunicorn app:app
DATA_DIR: /var/data
```

También define un disco persistente montado en `/var/data`, donde se guardan:

- Base SQLite `site.db`.
- Archivos subidos.
- Logo personalizado.

### Opción manual: Web Service

En Render crea un **Web Service** conectado al repositorio:

- Runtime: Python.
- Build command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
gunicorn app:app
```

- Variables de entorno:

```text
SECRET_KEY=una_clave_larga_aleatoria
ADMIN_PASSWORD=tu_clave_segura
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

Luego agrega un **Persistent Disk** montado en:

```text
/var/data
```

## 5. Nota importante sobre almacenamiento en Render

La aplicación permite subir archivos, por lo que necesita almacenamiento persistente. Si se despliega sin disco persistente, los archivos y la base local pueden perderse después de reinicios o redespliegues. Para un uso más avanzado, puedes reemplazar SQLite + disco por PostgreSQL y un servicio de almacenamiento de objetos.

## 6. Personalización rápida

- Colores y estética: `static/css/style.css`.
- Logo provisional: `static/img/default_logo.svg`.
- Tamaño máximo de subida: variable `MAX_UPLOAD_MB`.
- Nombre visible del sitio: desde el panel de administración.

## 7. Producción

Recomendaciones mínimas:

- Usar una clave `ADMIN_PASSWORD` fuerte.
- No publicar la clave en GitHub.
- Activar disco persistente en Render.
- Mantener copias de seguridad periódicas de `/var/data` si el contenido es importante.
