import os
import sqlite3
from contextlib import closing
from functools import wraps
from urllib.parse import urlencode

from flask import Flask, g, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = os.path.join(os.path.dirname(__file__), "users.db")
LEVELS = frozenset({"pro", "noob"})
app = Flask(__name__, static_folder="web", static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-nur-lokal-bitte-aendern")


def parse_subject_levels(form):
    g = form.get("level_german")
    m = form.get("level_math")
    e = form.get("level_english")
    if g not in LEVELS or m not in LEVELS or e not in LEVELS:
        return None
    return g, m, e


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _ensure_subject_columns(db):
    cur = db.execute("PRAGMA table_info(users)")
    names = {row[1] for row in cur.fetchall()}
    for col in ("level_german", "level_math", "level_english"):
        if col not in names:
            db.execute(
                f"ALTER TABLE users ADD COLUMN {col} TEXT NOT NULL DEFAULT 'noob'"
            )
    db.commit()


def init_db():
    with closing(sqlite3.connect(DATABASE)) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        db.commit()
        _ensure_subject_columns(db)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            q = urlencode({"flash": "needlogin", "next": request.path})
            return redirect(f"/login.html?{q}")
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect("/dashboard.html")
    return send_from_directory(app.static_folder, "index.html")


@app.route("/dashboard.html")
@login_required
def dashboard_page():
    return send_from_directory(app.static_folder, "dashboard.html")


@app.route("/settings.html")
@login_required
def settings_page():
    return send_from_directory(app.static_folder, "settings.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect("/dashboard.html")

    if request.method == "GET":
        return redirect("/register.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    password2 = request.form.get("password_confirm") or ""

    if not username or len(username) < 3:
        return redirect("/register.html?flash=shortuser")
    if len(password) < 6:
        return redirect("/register.html?flash=shortpass")
    if password != password2:
        return redirect("/register.html?flash=mismatch")

    levels = parse_subject_levels(request.form)
    if levels is None:
        return redirect("/register.html?flash=levels")

    lg, lm, le = levels
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO users (username, password_hash, level_german, level_math, level_english)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, generate_password_hash(password), lg, lm, le),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return redirect("/register.html?flash=taken")

    row = db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    session.clear()
    session["user_id"] = row["id"]
    session["username"] = username
    return redirect("/dashboard.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/dashboard.html")

    if request.method == "GET":
        return redirect("/login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    db = get_db()
    row = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if row is None or not check_password_hash(row["password_hash"], password):
        return redirect("/login.html?flash=invalid")

    session.clear()
    session["user_id"] = row["id"]
    session["username"] = username

    next_url = (request.form.get("next") or request.args.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("/dashboard.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/?flash=logout")


@app.route("/profile", methods=["POST"])
@login_required
def profile_update():
    levels = parse_subject_levels(request.form)
    if levels is None:
        return redirect("/settings.html?flash=levels")
    lg, lm, le = levels
    db = get_db()
    db.execute(
        """
        UPDATE users SET level_german = ?, level_math = ?, level_english = ?
        WHERE id = ?
        """,
        (lg, lm, le, session["user_id"]),
    )
    db.commit()
    return redirect("/settings.html?flash=saved")


@app.route("/api/me")
def api_me():
    if not session.get("user_id"):
        return jsonify({}), 401
    db = get_db()
    row = db.execute(
        """
        SELECT username, level_german, level_math, level_english
        FROM users WHERE id = ?
        """,
        (session["user_id"],),
    ).fetchone()
    if row is None:
        return jsonify({}), 401
    return jsonify(
        username=row["username"],
        level_german=row["level_german"],
        level_math=row["level_math"],
        level_english=row["level_english"],
    )


with app.app_context():
    init_db()


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
