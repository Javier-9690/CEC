# Despliegue en Render.com

## 1. Subir a GitHub

Descomprime el proyecto, entra a la carpeta y súbelo a un repositorio GitHub.

```bash
git init
git add .
git commit -m "Plataforma CEC pergamino"
git branch -M main
git remote add origin URL_DE_TU_REPOSITORIO
git push -u origin main
```

## 2. Crear Web Service en Render

En Render:

1. New +
2. Web Service
3. Conecta tu repositorio GitHub
4. Runtime: Python
5. Build Command:

```bash
pip install -r requirements.txt
```

6. Start Command:

```bash
gunicorn app:app
```

## 3. Variables de entorno

Agrega:

```text
ADMIN_PASSWORD=tu_clave_segura
SECRET_KEY=una_cadena_larga_aleatoria
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

## 4. Disco persistente

Para que no se pierdan PDFs, Word, PPT, audios y logos cuando Render reinicie o redespliegue el servicio, agrega un Persistent Disk y móntalo en:

```text
/var/data
```

## 5. Subir el logo

Cuando el sitio esté en línea:

1. Abre `https://tu-sitio.onrender.com/admin`
2. Entra con tu clave `ADMIN_PASSWORD`
3. Ve a **Identidad visual**
4. Sube el logo PNG
5. Guarda

Esta versión ya trae el logo CEC como logo base. El panel sirve para reemplazarlo sin tocar código.

## 6. Uso recomendado

1. Crea un tema: por ejemplo, `Simbolismo religioso`.
2. Sube una guía DOCX o PDF y asóciala a ese tema.
3. Sube una presentación PDF, PPT o PPTX al mismo tema.
4. Sube un podcast al mismo tema.
5. Publica una reseña asociada al mismo tema.
6. En la página pública del tema aparecerá todo reunido.


## Barra de avance

Esta versión incluye una barra de avance al subir archivos desde el panel de administración. La barra muestra el porcentaje y el volumen cargado, especialmente útil para audios, videos y PDF pesados. También agrega una barra visual de reproducción para audios y videos subidos directamente al sitio.
