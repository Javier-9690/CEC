# Despliegue en Render

1. Sube el proyecto a GitHub.
2. En Render crea un Web Service.
3. Conecta el repositorio.
4. Configura:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

5. Variables de entorno mínimas:

```text
ADMIN_PASSWORD=tu_clave_segura
SECRET_KEY=una_clave_larga_aleatoria
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

6. Para persistencia real de subidas, posts y suscriptores, crea un Persistent Disk:

```text
Mount Path: /var/data
```

7. Para enviar correos automáticos a suscriptores al publicar posts, configura SMTP:

```text
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=tu_usuario_smtp
SMTP_PASSWORD=tu_clave_smtp
MAIL_FROM=correo@tudominio.cl
SMTP_USE_TLS=1
```

Si SMTP no está configurado, la app registra suscriptores y permite exportarlos en CSV desde el panel.
