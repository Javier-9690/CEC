import os
import secrets
import sqlite3
import unicodedata
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "instance")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "site.db"

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc", "docx",
    "ppt", "pptx",
    "mp3", "wav", "m4a", "ogg",
    "png", "jpg", "jpeg", "webp", "gif",
}
LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}
WORD_EXTENSIONS = {"doc", "docx"}
PRESENTATION_EXTENSIONS = {"pdf", "ppt", "pptx"}
PDF_EXTENSIONS = {"pdf"}
OFFICE_VIEWER_EXTENSIONS = {"doc", "docx", "ppt", "pptx"}
PDF_VIEWER_KINDS = {"guia", "presentacion"}

KIND_LABELS = {
    "guia": "Guía de estudio",
    "presentacion": "Presentación",
    "podcast": "Podcast",
}

KIND_HELP = {
    "guia": "Acepta PDF, DOC o DOCX. Si subes DOCX, la guía se transforma a una lectura web con tablas.",
    "presentacion": "Acepta PDF, PPT o PPTX. Los PDF usan visor propio; los PPT/PPTX se abren con visor Office cuando el sitio está público.",
    "podcast": "Acepta MP3, WAV, M4A u OGG.",
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def column_exists(db: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in columns)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    safe = []
    for char in ascii_value.lower():
        if char.isalnum():
            safe.append(char)
        elif char in {" ", "-", "_"}:
            safe.append("-")
    slug = "".join(safe).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "tema"


def unique_slug(db: sqlite3.Connection, title: str) -> str:
    base = slugify(title)
    slug = base
    counter = 2
    while db.execute("SELECT 1 FROM topics WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            kind TEXT NOT NULL CHECK(kind IN ('guia', 'presentacion', 'podcast')),
            filename TEXT NOT NULL,
            html_filename TEXT,
            original_filename TEXT NOT NULL,
            original_extension TEXT,
            mime_type TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            title TEXT NOT NULL,
            author TEXT,
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )

    # Migraciones suaves para bases SQLite ya creadas por versiones anteriores.
    material_columns = {
        "topic_id": "ALTER TABLE materials ADD COLUMN topic_id INTEGER",
        "html_filename": "ALTER TABLE materials ADD COLUMN html_filename TEXT",
        "original_extension": "ALTER TABLE materials ADD COLUMN original_extension TEXT",
    }
    for col, sql in material_columns.items():
        if not column_exists(db, "materials", col):
            db.execute(sql)

    if not column_exists(db, "reviews", "topic_id"):
        db.execute("ALTER TABLE reviews ADD COLUMN topic_id INTEGER")

    general = db.execute("SELECT id FROM topics WHERE slug = ?", ("general",)).fetchone()
    if not general:
        db.execute(
            "INSERT INTO topics(title, slug, description, created_at) VALUES (?, ?, ?, ?)",
            (
                "General",
                "general",
                "Tema general para materiales todavía no clasificados.",
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
    general_id = db.execute("SELECT id FROM topics WHERE slug = ?", ("general",)).fetchone()[0]
    db.execute("UPDATE materials SET topic_id = ? WHERE topic_id IS NULL", (general_id,))
    db.execute("UPDATE reviews SET topic_id = ? WHERE topic_id IS NULL", (general_id,))
    db.execute("UPDATE materials SET original_extension = lower(substr(original_filename, instr(original_filename, '.') + 1)) WHERE original_extension IS NULL")
    db.commit()
    db.close()


def get_setting(key: str) -> Optional[str]:
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    db = get_db()
    db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    db.commit()


def allowed_file(filename: str, extensions=ALLOWED_EXTENSIONS) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def unique_filename(original_name: str) -> str:
    safe = secure_filename(original_name)
    if not safe:
        safe = "archivo"
    stem, dot, ext = safe.rpartition(".")
    suffix = secrets.token_hex(8)
    if dot:
        return f"{stem}_{suffix}.{ext.lower()}"
    return f"{safe}_{suffix}"


def is_logged_in() -> bool:
    return session.get("admin_logged_in") is True


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            flash("Debes ingresar al panel para realizar esa acción.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def validate_file_kind(kind: str, ext: str) -> Optional[str]:
    if kind == "guia" and ext not in PDF_EXTENSIONS | WORD_EXTENSIONS:
        return "Las guías deben ser PDF, DOC o DOCX. Para lectura web con tablas, usa DOCX."
    if kind == "presentacion" and ext not in PRESENTATION_EXTENSIONS:
        return "Las presentaciones deben ser PDF, PPT o PPTX."
    if kind == "podcast" and ext not in AUDIO_EXTENSIONS:
        return "Los podcasts deben ser MP3, WAV, M4A u OGG."
    return None


def generate_docx_html(source_path: Path, stored_name: str) -> Optional[str]:
    """Convierte DOCX a HTML de lectura. Mantiene tablas básicas con Mammoth."""
    if source_path.suffix.lower() != ".docx":
        return None
    try:
        import mammoth

        with source_path.open("rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
        html_name = f"{source_path.stem}.html"
        html = "\n".join([
            "<article class=\"docx-render\">",
            result.value,
            "</article>",
        ])
        (UPLOAD_DIR / html_name).write_text(html, encoding="utf-8")
        return html_name
    except Exception:
        return None


def resolve_topic(db: sqlite3.Connection, topic_id_raw: str, new_topic_title: str, new_topic_description: str = "") -> int:
    new_topic_title = (new_topic_title or "").strip()
    new_topic_description = (new_topic_description or "").strip()
    if new_topic_title:
        existing = db.execute("SELECT id FROM topics WHERE lower(title) = lower(?)", (new_topic_title,)).fetchone()
        if existing:
            return existing["id"] if isinstance(existing, sqlite3.Row) else existing[0]
        slug = unique_slug(db, new_topic_title)
        cursor = db.execute(
            "INSERT INTO topics(title, slug, description, created_at) VALUES (?, ?, ?, ?)",
            (new_topic_title, slug, new_topic_description, datetime.utcnow().isoformat(timespec="seconds")),
        )
        return cursor.lastrowid

    try:
        topic_id = int(topic_id_raw or "")
    except ValueError:
        topic_id = 0
    if topic_id:
        row = db.execute("SELECT id FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if row:
            return row["id"] if isinstance(row, sqlite3.Row) else row[0]
    row = db.execute("SELECT id FROM topics WHERE slug = ?", ("general",)).fetchone()
    return row["id"] if isinstance(row, sqlite3.Row) else row[0]


def office_viewer_url(file_url: str) -> str:
    return "https://view.officeapps.live.com/op/embed.aspx?src=" + quote(file_url, safe="")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "120")) * 1024 * 1024

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        init_db()

    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_globals():
        logo_filename = get_setting("logo_filename")
        if logo_filename:
            logo_url = url_for("uploaded_file", filename=logo_filename)
        else:
            logo_url = url_for("static", filename="img/logo_cec.png")
        return {
            "logo_url": logo_url,
            "site_logo": logo_filename,
            "site_name": get_setting("site_name") or "Centro de Estudios Católicos",
            "kind_labels": KIND_LABELS,
            "kind_help": KIND_HELP,
            "office_viewer_url": office_viewer_url,
        }

    return app


app = create_app()


def material_query(where: str = "", params: tuple = (), limit: Optional[int] = None):
    db = get_db()
    sql = """
        SELECT m.*, t.title AS topic_title, t.slug AS topic_slug
        FROM materials m
        LEFT JOIN topics t ON t.id = m.topic_id
    """
    if where:
        sql += " WHERE " + where
    sql += " ORDER BY datetime(m.created_at) DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.execute(sql, params).fetchall()


def review_query(where: str = "", params: tuple = (), limit: Optional[int] = None):
    db = get_db()
    sql = """
        SELECT r.*, t.title AS topic_title, t.slug AS topic_slug
        FROM reviews r
        LEFT JOIN topics t ON t.id = r.topic_id
    """
    if where:
        sql += " WHERE " + where
    sql += " ORDER BY datetime(r.created_at) DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.execute(sql, params).fetchall()


@app.route("/")
def index():
    db = get_db()
    latest_materials = material_query(limit=6)
    latest_reviews = review_query(limit=3)
    topics = db.execute(
        """
        SELECT t.*, COUNT(m.id) AS material_count
        FROM topics t
        LEFT JOIN materials m ON m.topic_id = t.id
        GROUP BY t.id
        ORDER BY lower(t.title)
        LIMIT 8
        """
    ).fetchall()
    counts = {
        "guia": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='guia'").fetchone()["c"],
        "presentacion": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='presentacion'").fetchone()["c"],
        "podcast": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='podcast'").fetchone()["c"],
        "resena": db.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"],
        "tema": db.execute("SELECT COUNT(*) AS c FROM topics").fetchone()["c"],
    }
    return render_template(
        "index.html",
        latest_materials=latest_materials,
        latest_reviews=latest_reviews,
        topics=topics,
        counts=counts,
    )


@app.route("/biblioteca")
def library():
    selected_kind = request.args.get("tipo", "").strip()
    selected_topic = request.args.get("tema", "").strip()
    db = get_db()
    topics = db.execute("SELECT * FROM topics ORDER BY lower(title)").fetchall()
    wheres = []
    params = []
    if selected_kind in KIND_LABELS:
        wheres.append("m.kind = ?")
        params.append(selected_kind)
    else:
        selected_kind = ""
    if selected_topic:
        wheres.append("t.slug = ?")
        params.append(selected_topic)
    rows = material_query(" AND ".join(wheres), tuple(params)) if wheres else material_query()
    return render_template(
        "library.html",
        materials=rows,
        topics=topics,
        selected_kind=selected_kind,
        selected_topic=selected_topic,
    )


@app.route("/temas")
def topics():
    db = get_db()
    rows = db.execute(
        """
        SELECT t.*,
               COUNT(DISTINCT m.id) AS material_count,
               COUNT(DISTINCT r.id) AS review_count
        FROM topics t
        LEFT JOIN materials m ON m.topic_id = t.id
        LEFT JOIN reviews r ON r.topic_id = t.id
        GROUP BY t.id
        ORDER BY lower(t.title)
        """
    ).fetchall()
    return render_template("topics.html", topics=rows)


@app.route("/tema/<slug>")
def topic_detail(slug: str):
    db = get_db()
    topic = db.execute("SELECT * FROM topics WHERE slug = ?", (slug,)).fetchone()
    if topic is None:
        abort(404)
    materials = material_query("t.slug = ?", (slug,))
    reviews_rows = review_query("t.slug = ?", (slug,))
    return render_template("topic_detail.html", topic=topic, materials=materials, reviews=reviews_rows)


@app.route("/material/<int:material_id>")
def material_detail(material_id: int):
    db = get_db()
    material = db.execute(
        """
        SELECT m.*, t.title AS topic_title, t.slug AS topic_slug
        FROM materials m
        LEFT JOIN topics t ON t.id = m.topic_id
        WHERE m.id = ?
        """,
        (material_id,),
    ).fetchone()
    if material is None:
        abort(404)
    docx_html = None
    if material["html_filename"]:
        html_path = UPLOAD_DIR / material["html_filename"]
        if html_path.exists():
            docx_html = html_path.read_text(encoding="utf-8")
    ext = file_extension(material["filename"])
    return render_template(
        "material_detail.html",
        material=material,
        docx_html=docx_html,
        ext=ext,
        file_url_external=url_for("uploaded_file", filename=material["filename"], _external=True),
    )


@app.route("/visor/pdf/<int:material_id>")
def pdf_viewer(material_id: int):
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if material is None or material["kind"] not in PDF_VIEWER_KINDS or not material["filename"].lower().endswith(".pdf"):
        abort(404)
    return render_template("presentation_viewer.html", material=material)


# Compatibilidad con enlaces generados por la primera versión.
@app.route("/presentacion/<int:material_id>")
def presentation_viewer(material_id: int):
    return redirect(url_for("pdf_viewer", material_id=material_id))


@app.route("/podcasts")
def podcasts():
    rows = material_query("m.kind='podcast'")
    return render_template("podcasts.html", podcasts=rows)


@app.route("/resenas")
def reviews():
    rows = review_query()
    return render_template("reviews.html", reviews=rows)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD", "cambiar-esta-clave")
        if secrets.compare_digest(password, expected):
            session["admin_logged_in"] = True
            flash("Ingreso correcto al panel de administración.", "success")
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("Clave incorrecta.", "danger")
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    db = get_db()
    materials = material_query(limit=14)
    reviews_rows = review_query(limit=14)
    topics_rows = db.execute(
        """
        SELECT t.*,
               COUNT(DISTINCT m.id) AS material_count,
               COUNT(DISTINCT r.id) AS review_count
        FROM topics t
        LEFT JOIN materials m ON m.topic_id = t.id
        LEFT JOIN reviews r ON r.topic_id = t.id
        GROUP BY t.id
        ORDER BY lower(t.title)
        """
    ).fetchall()
    return render_template("admin_dashboard.html", materials=materials, reviews=reviews_rows, topics=topics_rows)


@app.route("/admin/topic/new", methods=["POST"])
@login_required
def admin_topic_new():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not title:
        flash("El tema necesita un título.", "warning")
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    if db.execute("SELECT 1 FROM topics WHERE lower(title) = lower(?)", (title,)).fetchone():
        flash("Ese tema ya existe.", "warning")
        return redirect(url_for("admin_dashboard"))
    db.execute(
        "INSERT INTO topics(title, slug, description, created_at) VALUES (?, ?, ?, ?)",
        (title, unique_slug(db, title), description, datetime.utcnow().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("Tema creado correctamente.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/upload", methods=["GET", "POST"])
@login_required
def admin_upload():
    db = get_db()
    topics_rows = db.execute("SELECT * FROM topics ORDER BY lower(title)").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        kind = request.form.get("kind", "").strip()
        topic_id_raw = request.form.get("topic_id", "").strip()
        new_topic_title = request.form.get("new_topic_title", "").strip()
        new_topic_description = request.form.get("new_topic_description", "").strip()
        file = request.files.get("file")

        if not title or kind not in KIND_LABELS or not file or file.filename == "":
            flash("Completa título, tipo y archivo.", "warning")
            return redirect(url_for("admin_upload"))

        if not allowed_file(file.filename):
            flash("Formato no permitido. Usa PDF, DOCX/DOC, PPTX/PPT o audio compatible.", "danger")
            return redirect(url_for("admin_upload"))

        ext = file_extension(file.filename)
        error = validate_file_kind(kind, ext)
        if error:
            flash(error, "warning")
            return redirect(url_for("admin_upload"))

        stored_name = unique_filename(file.filename)
        saved_path = UPLOAD_DIR / stored_name
        file.save(saved_path)
        html_filename = generate_docx_html(saved_path, stored_name) if ext == "docx" else None
        topic_id = resolve_topic(db, topic_id_raw, new_topic_title, new_topic_description)

        db.execute(
            """
            INSERT INTO materials(topic_id, title, description, kind, filename, html_filename, original_filename, original_extension, mime_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                title,
                description,
                kind,
                stored_name,
                html_filename,
                file.filename,
                ext,
                file.mimetype,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        db.commit()
        flash("Material publicado correctamente.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_upload.html", topics=topics_rows)


@app.route("/admin/review/new", methods=["GET", "POST"])
@login_required
def admin_review_new():
    db = get_db()
    topics_rows = db.execute("SELECT * FROM topics ORDER BY lower(title)").fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        body = request.form.get("body", "").strip()
        rating_raw = request.form.get("rating", "").strip()
        topic_id_raw = request.form.get("topic_id", "").strip()
        new_topic_title = request.form.get("new_topic_title", "").strip()
        new_topic_description = request.form.get("new_topic_description", "").strip()
        try:
            rating = int(rating_raw) if rating_raw else None
        except ValueError:
            rating = None
        if rating is not None and rating not in range(1, 6):
            rating = None

        if not title or not body:
            flash("La reseña necesita título y contenido.", "warning")
            return redirect(url_for("admin_review_new"))

        topic_id = resolve_topic(db, topic_id_raw, new_topic_title, new_topic_description)
        db.execute(
            "INSERT INTO reviews(topic_id, title, author, rating, body, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (topic_id, title, author, rating, body, datetime.utcnow().isoformat(timespec="seconds")),
        )
        db.commit()
        flash("Reseña publicada correctamente.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_review_form.html", topics=topics_rows)


@app.route("/admin/logo", methods=["POST"])
@login_required
def admin_logo():
    file = request.files.get("logo")
    site_name = request.form.get("site_name", "").strip()
    if site_name:
        set_setting("site_name", site_name)
    if file and file.filename:
        if not allowed_file(file.filename, LOGO_EXTENSIONS):
            flash("El logo debe ser PNG, JPG, WEBP o SVG.", "warning")
            return redirect(url_for("admin_dashboard"))
        stored_name = "logo_" + unique_filename(file.filename)
        file.save(UPLOAD_DIR / stored_name)
        set_setting("logo_filename", stored_name)
    flash("Identidad visual actualizada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/material/<int:material_id>/delete", methods=["POST"])
@login_required
def admin_material_delete(material_id: int):
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if material is None:
        abort(404)
    for field in ("filename", "html_filename"):
        if material[field]:
            try:
                (UPLOAD_DIR / material[field]).unlink(missing_ok=True)
            except OSError:
                pass
    db.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    db.commit()
    flash("Material eliminado.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/review/<int:review_id>/delete", methods=["POST"])
@login_required
def admin_review_delete(review_id: int):
    db = get_db()
    db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    db.commit()
    flash("Reseña eliminada.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("index"))


@app.template_filter("date_display")
def date_display(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return value


if __name__ == "__main__":
    app.run(debug=True)
