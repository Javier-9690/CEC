# Guía breve para montar en Render.com

## 1. Subir a GitHub

```bash
git init
git add .
git commit -m "Primera version Centro de Estudios"
git branch -M main
git remote add origin TU_REPOSITORIO
git push -u origin main
```

## 2. Crear servicio en Render

### Con Blueprint

1. Entra a Render.
2. Selecciona **New +**.
3. Selecciona **Blueprint**.
4. Conecta tu repositorio.
5. Render detectará `render.yaml`.
6. Agrega `ADMIN_PASSWORD`.
7. Despliega.

### Manual

1. New + → Web Service.
2. Conecta el repositorio.
3. Runtime: Python.
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
gunicorn app:app
```

6. Environment variables:

```text
SECRET_KEY=clave_larga_y_segura
ADMIN_PASSWORD=clave_para_entrar_al_panel
DATA_DIR=/var/data
MAX_UPLOAD_MB=120
```

7. Agrega Persistent Disk con mount path:

```text
/var/data
```

## 3. Entrar al panel

Cuando Render entregue la URL pública, entra a:

```text
https://tu-sitio.onrender.com/admin
```

Desde ahí subes tu logo, guías, presentaciones, podcasts y reseñas.
