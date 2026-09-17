from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from functools import wraps

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "kfc.db")
UPLOAD_FOLDER = os.path.join(BASE, "static", "uploads")

app = Flask(__name__)
app.secret_key = os.environ.get("KFC_SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def setup():
    con = db()

    con.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS fighters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        division TEXT,
        record TEXT,
        achievement TEXT,
        description TEXT,
        age INTEGER,
        photo TEXT
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        caption TEXT
    )
    """)

    existing = con.execute(
        "SELECT id FROM users WHERE username=?",
        ("admin",)
    ).fetchone()

    if not existing:
        con.execute(
            "INSERT INTO users (username,password) VALUES (?,?)",
            ("admin", generate_password_hash("KFCadmin2026!"))
        )

    con.commit()
    con.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        con.close()

        if user and check_password_hash(user["password"], password):
            session["admin"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Incorrect username or password.")

    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def dashboard():

    con = db()

    fighters = con.execute(
        "SELECT * FROM fighters ORDER BY id DESC"
    ).fetchall()

    news = con.execute(
        "SELECT * FROM news ORDER BY id DESC"
    ).fetchall()

    photos = con.execute(
        "SELECT * FROM photos ORDER BY id DESC"
    ).fetchall()

    con.close()

    return render_template(
        "dashboard.html",
        fighters=fighters,
        news=news,
        photos=photos
    )

@app.route("/admin/fighter/add", methods=["POST"])
@login_required
def add_fighter():

    name = request.form.get("name", "")
    division = request.form.get("division", "")
    record = request.form.get("record", "")
    achievement = request.form.get("achievement", "")
    description = request.form.get("description", "")
    age = request.form.get("age", type=int)
    photo = request.files.get("photo")
    photo_filename = None

    if photo and photo.filename:
        photo_filename = secure_filename(photo.filename)
        photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    if name:
        con = db()
        con.execute("""
        INSERT INTO fighters
        (name,division,record,achievement,description,age,photo)
        VALUES (?,?,?,?,?,?,?)
        """, (name, division, record, achievement, description, age, photo_filename))
        con.commit()
        con.close()

    return redirect(url_for("dashboard"))

@app.route("/admin/fighter/delete/<int:id>")
@login_required
def delete_fighter(id):

    con = db()
    con.execute("DELETE FROM fighters WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect(url_for("dashboard"))

@app.route("/admin/news/add", methods=["POST"])
@login_required
def add_news():

    title = request.form.get("title", "")
    content = request.form.get("content", "")

    if title and content:
        con = db()
        con.execute(
            "INSERT INTO news (title,content) VALUES (?,?)",
            (title, content)
        )
        con.commit()
        con.close()

    return redirect(url_for("dashboard"))

@app.route("/admin/news/delete/<int:id>")
@login_required
def delete_news(id):

    con = db()
    con.execute("DELETE FROM news WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect(url_for("dashboard"))

@app.route("/admin/photo/upload", methods=["POST"])
@login_required
def upload_photo():

    photo = request.files.get("photo")
    caption = request.form.get("caption", "")

    if photo and photo.filename:

        filename = secure_filename(photo.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        photo.save(path)

        con = db()
        con.execute(
            "INSERT INTO photos (filename,caption) VALUES (?,?)",
            (filename, caption)
        )
        con.commit()
        con.close()

    return redirect(url_for("dashboard"))

@app.route("/admin/photo/delete/<int:id>")
@login_required
def delete_photo(id):

    con = db()

    photo = con.execute(
        "SELECT * FROM photos WHERE id=?",
        (id,)
    ).fetchone()

    if photo:
        path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            photo["filename"]
        )

        if os.path.exists(path):
            os.remove(path)

        con.execute(
            "DELETE FROM photos WHERE id=?",
            (id,)
        )

    con.commit()
    con.close()

    return redirect(url_for("dashboard"))

@app.route("/")
def home():
    return send_from_directory(os.path.dirname(app.root_path), "index.html")

setup()

if __name__ == "__main__":  
    app.run(host="0.0.0.0", port=8080, debug=False)
