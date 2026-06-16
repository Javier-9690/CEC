# Centro de Estudios CEC - Suscripción y protección visual

Aplicación Flask para biblioteca digital con estética pergamino, organizada por temas.

## Funciones principales

- Temas de estudio.
- Guías PDF, DOC y DOCX.
- Presentaciones PDF con visor interactivo.
- Presentaciones PPT/PPTX con visor Office cuando el sitio está público.
- Podcast subidos: MP3, WAV, M4A, AAC, OGG.
- Videos subidos: MP4, WEBM, OGV, MOV.
- Videos de YouTube embebidos.
- Enlaces de SoundCloud embebidos.
- Textos/artículos publicados desde el panel.
- Reseñas asociadas a temas.
- Posts públicos.
- Formulario de suscripción para recibir avisos de nuevos posts.
- Exportación CSV de suscriptores desde el panel.
- Envío opcional por SMTP si se configuran variables de correo.
- Modo sin descarga pública.
- Bloqueo de copia simple, clic derecho, impresión y selección en textos protegidos.
- Marca de agua disuasiva en textos y visor PDF.

## Advertencia importante sobre protección

La web puede bloquear copia simple, selección, clic derecho, impresión desde el navegador y botones de descarga. Sin embargo, ningún sitio web puede impedir completamente capturas de pantalla, grabaciones de pantalla, fotografías externas, herramientas de desarrollador u OCR. Esta versión aplica protección disuasiva, no DRM absoluto.

## Variables recomendadas en Render

```text
ADMIN_PASSWORD=tu_clave_segura
SECRET_KEY=una_cadena_larga_aleatoria
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

Para envío automático de correos a suscriptores, agrega opcionalmente:

```text
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=tu_usuario_smtp
SMTP_PASSWORD=tu_clave_smtp
MAIL_FROM=correo@tudominio.cl
SMTP_USE_TLS=1
```

Si no configuras SMTP, los posts se publican igual y puedes exportar los suscriptores como CSV.

## Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

## Persistencia

Para que archivos subidos, textos, posts, reseñas y suscriptores permanezcan después de reinicios o redeploys, usa un Persistent Disk montado en:

```text
/var/data
```

Si usas Render gratis sin disco persistente, el almacenamiento local puede perderse.
