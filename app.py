from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_PATH = Path(__file__).with_name("students.db")

def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT,
                course TEXT NOT NULL,
                year INTEGER NOT NULL)
                """)

@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    with db() as connection:
        if query:
            term = f"%{query}%"
            students = connection.execute("""
                SELECT * FROM students
                WHERE roll_no LIKE ? OR full_name LIKE ?
                   OR email LIKE ? OR course LIKE ?
                ORDER BY full_name COLLATE NOCASE
            """, (term, term, term, term)).fetchall()
        else:
            students = connection.execute(
                "SELECT * FROM students ORDER BY full_name COLLATE NOCASE"
            ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    return render_template("index.html", students=students, total=total, query=query)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        data = read_form()
        error = validate(data)
        if error:
            flash(error, "error")
            return render_template("form.html", student=data, mode="Add")
        try:
            with db() as connection:
                connection.execute("""
                    INSERT INTO students (roll_no, full_name, email, course, year)
                    VALUES (?, ?, ?, ?, ?)
                """, (data["roll_no"], data["full_name"], data["email"],
                      data["course"], data["year"]))
            flash("Student added.", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("That roll number already exists.", "error")
            return render_template("form.html", student=data, mode="Add")
    return render_template("form.html", student={}, mode="Add")

@app.route("/edit/<int:student_id>", methods=["GET", "POST"])
def edit(student_id):
    with db() as connection:
        record = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if record is None:
        flash("Student not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data = read_form()
        error = validate(data)
        if error:
            flash(error, "error")
            data["id"] = student_id
            return render_template("form.html", student=data, mode="Edit")
        try:
            with db() as connection:
                connection.execute("""
                    UPDATE students
                    SET roll_no = ?, full_name = ?, email = ?, course = ?, year = ?
                    WHERE id = ?
                """, (data["roll_no"], data["full_name"], data["email"],
                      data["course"], data["year"], student_id))
            flash("Student updated.", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("That roll number already belongs to another student.", "error")
            data["id"] = student_id
            return render_template("form.html", student=data, mode="Edit")
    return render_template("form.html", student=dict(record), mode="Edit")

@app.route("/delete/<int:student_id>", methods=["POST"])
def delete(student_id):
    with db() as connection:
        connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
    flash("Student deleted.", "success")
    return redirect(url_for("index"))

def read_form():
    return {
        "roll_no": request.form.get("roll_no", "").strip(),
        "full_name": request.form.get("full_name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "course": request.form.get("course", "").strip(),
        "year": request.form.get("year", "").strip(),
    }

def validate(data):
    if not data["roll_no"] or not data["full_name"] or not data["course"] or not data["year"]:
        return "Please complete all required fields."
    try:
        year = int(data["year"])
        if year < 1 or year > 8:
            return "Year must be between 1 and 8."
        data["year"] = year
    except ValueError:
        return "Please select a valid year."
    return None

if __name__ == "__main__":
    init_db()
    app.run(debug=True)