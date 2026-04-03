from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import threading
import webview
import os
import sys


def get_templates():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'templates')
    return "templates"

app = Flask(__name__, template_folder=get_templates())
app.secret_key = "eval_system_secure_key"

DB = "community_framework.db"


def create_table():
    connection = sqlite3.connect(DB)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            p_score REAL,
            d_score REAL,
            ux_score REAL,
            r_score REAL,
            total REAL,
            verdict TEXT,
            notes TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()

create_table()


def calculate_result(p, d, ux, r):
    value = (p * 0.4) + (d * 0.4) + (ux * 0.1) + (r * 0.1)
    return round(value, 2)

def decide_verdict(score):
    if score >= 4.0:
        return "EXCELLENT FRAMEWORK"
    elif score >= 3.0:
        return "STANDARD FRAMEWORK"
    else:
        return "NEEDS IMPROVEMENT"

def save_to_db(record):
    connection = sqlite3.connect(DB)
    connection.execute("""
        INSERT INTO reports 
        (app_name, p_score, d_score, ux_score, r_score, total, verdict, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, record)

    connection.commit()
    connection.close()


@app.route("/", methods=["GET", "POST"])
def main_page():
    if "user_name" not in session:
        return redirect(url_for("join_user"))

    response_data = None

    if request.method == "POST":
        p_score = float(request.form.get("p", 3.0))
        d_score = float(request.form.get("d", 3.0))
        ux_score = float(request.form.get("ux", 3.0))
        r_score = float(request.form.get("r", 3.0))

        app_title = request.form.get("app_name", "UNKNOWN").strip().upper()
        note_text = request.form.get("notes", "").strip()

        total_score = calculate_result(p_score, d_score, ux_score, r_score)
        final_verdict = decide_verdict(total_score)

        save_to_db((
            app_title,
            p_score, d_score, ux_score, r_score,
            total_score, final_verdict, note_text
        ))

        response_data = {
            "name": app_title,
            "scores": [p_score, d_score, ux_score, r_score],
            "total": total_score,
            "verdict": final_verdict
        }

    return render_template("index.html", result=response_data)

@app.route("/history")
def show_history():
    if "user_name" not in session:
        return redirect(url_for("join_user"))

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row

    records = connection.execute(
        "SELECT * FROM reports ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template("history.html", items=records)

@app.route("/delete/<int:item_id>")
def remove_entry(item_id):
    connection = sqlite3.connect(DB)
    connection.execute("DELETE FROM reports WHERE id = ?", (item_id,))
    connection.commit()
    connection.close()

    return redirect(url_for("show_history"))

@app.route("/join", methods=["GET", "POST"])
def join_user():
    if request.method == "POST":
        session["user_name"] = request.form.get("user_name")
        return redirect(url_for("main_page"))

    return render_template("join.html")

def run_server():
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=run_server).start()

    webview.create_window(
        "Framework Evaluation System",
        "http://127.0.0.1:5000",
        width=1100,
        height=850
    )
    webview.start()
