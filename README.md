# Centro de Estudios Católicos · Plataforma pergamino

Aplicación web Flask preparada para Render.com. Permite publicar contenido de estudio con estética tradicional tipo pergamino y logo institucional CEC.

## Funciones principales

- Página pública con logo institucional.
- Temas de estudio: cada tema agrupa materiales y reseñas.
- Guías de estudio en PDF, DOC y DOCX.
- Conversión de DOCX a lectura web con tablas básicas mediante `mammoth`.
- Presentaciones en PDF, PPT y PPTX.
- Visor interactivo propio para PDF con avance de páginas y zoom.
- Visor Office para DOC, DOCX, PPT y PPTX cuando el sitio está publicado en internet.
- Podcast con reproductor de audio.
- Reseñas asociables a temas.
- Panel de administración protegido por clave.
- Carga de logo PNG/JPG/WEBP/SVG desde el panel.
- SQLite con migraciones suaves para versiones anteriores.

## Formatos aceptados

| Tipo | Formatos |
|---|---|
| Guía de estudio | PDF, DOC, DOCX |
| Presentación | PDF, PPT, PPTX |
| Podcast | MP3, WAV, M4A, OGG |
| Logo | PNG, JPG, JPEG, WEBP, SVG |

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Entrar en:

```text
http://127.0.0.1:5000
```

Panel de administración:

```text
http://127.0.0.1:5000/admin
```

Clave local por defecto:

```text
cambiar-esta-clave
```

En producción debes cambiarla mediante variable de entorno.

## Variables de entorno recomendadas en Render

```text
ADMIN_PASSWORD=tu_clave_segura
SECRET_KEY=una_cadena_larga_aleatoria
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

## Subir el logo

Hay dos opciones:

1. Desde la web: entra a `/admin`, luego al panel, sección **Identidad visual**, y sube el logo en PNG.
2. Como logo base del proyecto: reemplaza el archivo `static/img/logo_cec.png` antes de subir el repositorio.

Esta versión ya incluye el logo CEC recibido como `static/img/logo_cec.png`.

## Organización por tema

Desde el panel puedes crear temas. Al subir una guía, PDF, PPT, podcast o reseña, puedes elegir un tema existente o crear uno nuevo en el mismo formulario.

Cada tema tendrá una URL pública con todos sus materiales asociados.

## Nota sobre PPT/PPTX y DOC/DOCX

Los navegadores no muestran de forma nativa archivos Word o PowerPoint como un PDF. Por eso la app usa dos estrategias:

- DOCX: se convierte a HTML para lectura web con tablas básicas.
- DOC, DOCX, PPT, PPTX: se ofrecen mediante visor Office embebido cuando la app está desplegada públicamente en Render.

Para presentaciones con máxima estabilidad visual, exporta también una copia en PDF y súbela como presentación.


## Barra de avance

Esta versión incluye una barra de avance al subir archivos desde el panel de administración. La barra muestra el porcentaje y el volumen cargado, especialmente útil para audios, videos y PDF pesados. También agrega una barra visual de reproducción para audios y videos subidos directamente al sitio.
