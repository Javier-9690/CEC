import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

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
    "mp3", "wav", "m4a", "ogg",
    "png", "jpg", "jpeg", "webp", "gif",
}
LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
PDF_KINDS = {"guia", "presentacion"}
KIND_LABELS = {
    "guia": "Guía de estudio",
    "presentacion": "Presentación PDF",
    "podcast": "Podcast",
}


def create_app() -> Flask:
    app = Flask(__name__)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "120")) * 1024 * 1024

    with app.app_context():
        init_db()

    @app.context_processor
    def inject_globals():
        return {
            "site_logo": get_setting("logo_filename"),
            "site_name": get_setting("site_name") or "Centro de Estudios",
            "kind_labels": KIND_LABELS,
        }

    return app


app = create_app()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            kind TEXT NOT NULL CHECK(kind IN ('guia', 'presentacion', 'podcast')),
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            mime_type TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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


@app.route("/")
def index():
    db = get_db()
    latest_materials = db.execute(
        "SELECT * FROM materials ORDER BY datetime(created_at) DESC LIMIT 6"
    ).fetchall()
    latest_reviews = db.execute(
        "SELECT * FROM reviews ORDER BY datetime(created_at) DESC LIMIT 3"
    ).fetchall()
    counts = {
        "guia": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='guia'").fetchone()["c"],
        "presentacion": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='presentacion'").fetchone()["c"],
        "podcast": db.execute("SELECT COUNT(*) AS c FROM materials WHERE kind='podcast'").fetchone()["c"],
        "resena": db.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"],
    }
    return render_template("index.html", latest_materials=latest_materials, latest_reviews=latest_reviews, counts=counts)


@app.route("/biblioteca")
def library():
    selected_kind = request.args.get("tipo", "").strip()
    db = get_db()
    if selected_kind in KIND_LABELS:
        rows = db.execute(
            "SELECT * FROM materials WHERE kind = ? ORDER BY datetime(created_at) DESC",
            (selected_kind,),
        ).fetchall()
    else:
        selected_kind = ""
        rows = db.execute("SELECT * FROM materials ORDER BY datetime(created_at) DESC").fetchall()
    return render_template("library.html", materials=rows, selected_kind=selected_kind)


@app.route("/material/<int:material_id>")
def material_detail(material_id: int):
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if material is None:
        abort(404)
    return render_template("material_detail.html", material=material)


@app.route("/presentacion/<int:material_id>")
def presentation_viewer(material_id: int):
    db = get_db()
    material = db.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if material is None or material["kind"] not in PDF_KINDS or not material["filename"].lower().endswith(".pdf"):
        abort(404)
    return render_template("presentation_viewer.html", material=material)


@app.route("/podcasts")
def podcasts():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM materials WHERE kind='podcast' ORDER BY datetime(created_at) DESC"
    ).fetchall()
    return render_template("podcasts.html", podcasts=rows)


@app.route("/resenas")
def reviews():
    db = get_db()
    rows = db.execute("SELECT * FROM reviews ORDER BY datetime(created_at) DESC").fetchall()
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
    materials = db.execute("SELECT * FROM materials ORDER BY datetime(created_at) DESC LIMIT 12").fetchall()
    reviews_rows = db.execute("SELECT * FROM reviews ORDER BY datetime(created_at) DESC LIMIT 12").fetchall()
    return render_template("admin_dashboard.html", materials=materials, reviews=reviews_rows)


@app.route("/admin/upload", methods=["GET", "POST"])
@login_required
def admin_upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        kind = request.form.get("kind", "").strip()
        file = request.files.get("file")

        if not title or kind not in KIND_LABELS or not file or file.filename == "":
            flash("Completa título, tipo y archivo.", "warning")
            return redirect(url_for("admin_upload"))

        if not allowed_file(file.filename):
            flash("Formato no permitido. Usa PDF, audio o imagen compatible.", "danger")
            return redirect(url_for("admin_upload"))

        ext = file.filename.rsplit(".", 1)[1].lower()
        if kind in PDF_KINDS and ext != "pdf":
            flash("Las guías y presentaciones deben subirse en PDF para poder visualizarse en línea.", "warning")
            return redirect(url_for("admin_upload"))
        if kind == "podcast" and ext not in {"mp3", "wav", "m4a", "ogg"}:
            flash("Los podcasts deben ser archivos de audio: MP3, WAV, M4A u OGG.", "warning")
            return redirect(url_for("admin_upload"))

        stored_name = unique_filename(file.filename)
        file.save(UPLOAD_DIR / stored_name)
        db = get_db()
        db.execute(
            "INSERT INTO materials(title, description, kind, filename, original_filename, mime_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, description, kind, stored_name, file.filename, file.mimetype, datetime.utcnow().isoformat(timespec="seconds")),
        )
        db.commit()
        flash("Material publicado correctamente.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_upload.html")


@app.route("/admin/review/new", methods=["GET", "POST"])
@login_required
def admin_review_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        body = request.form.get("body", "").strip()
        rating_raw = request.form.get("rating", "").strip()
        try:
            rating = int(rating_raw) if rating_raw else None
        except ValueError:
            rating = None
        if rating is not None and rating not in range(1, 6):
            rating = None

        if not title or not body:
            flash("La reseña necesita título y contenido.", "warning")
            return redirect(url_for("admin_review_new"))

        db = get_db()
        db.execute(
            "INSERT INTO reviews(title, author, rating, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (title, author, rating, body, datetime.utcnow().isoformat(timespec="seconds")),
        )
        db.commit()
        flash("Reseña publicada correctamente.", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_review_form.html")


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
    try:
        (UPLOAD_DIR / material["filename"]).unlink(missing_ok=True)
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
