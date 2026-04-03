from flask
import Flask, render_template, request, redirect, url_for, session
import sqlite3, threading, webview, os, sys

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
else:
    template_folder = 'templates'

app = Flask(__name__, template_folder=template_folder)
app.secret_key = "comm_framework_eval_2026_omni"

def init_db():
    conn = sqlite3.connect("community_framework.db")

    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT, p_score REAL, d_score REAL, ux_score REAL, r_score REAL, plag_score REAL,
        total REAL, verdict TEXT, notes TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if 'user_name' not in session: return redirect(url_for('join'))
    result = None
    if request.method == "POST":
        p, d, ux, r, plag = [float(request.form.get(k, 3.0)) for k in ['p', 'd', 'ux', 'r', 'plag']]
        name = request.form.get("app_name", "UNKNOWN").strip().upper()
        notes = request.form.get("notes", "").strip()
        

        total = round((p * 0.35) + (d * 0.35) + (ux * 0.10) + (r * 0.10) + ((6 - plag) * 0.10), 2)
        
        if total >= 4.0: verdict = "HIGHLY EDUCATIONAL"
        elif total >= 3.0: verdict = "MODERATELY EDUCATIONAL"
        else: verdict = "LOW EDUCATIONAL VALUE"

        conn = sqlite3.connect("community_framework.db")
        conn.execute("""INSERT INTO reports (app_name, p_score, d_score, ux_score, r_score, plag_score, total, verdict, notes) 
                     VALUES (?,?,?,?,?,?,?,?,?)""", (name, p, d, ux, r, plag, total, verdict, notes))
        conn.commit()
        conn.close()
        
        result = {"name": name, "scores": [p, d, ux, r, plag], "total": total, "verdict": verdict, "notes": notes}

    return render_template("index.html", result=result)

@app.route("/history")
def history():
    if 'user_name' not in session: return redirect(url_for('join'))
    conn = sqlite3.connect("community_framework.db")
    conn.row_factory = sqlite3.Row
    items = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("history.html", items=items)

@app.route("/delete/<int:id>")
def delete_item(id):
    conn = sqlite3.connect("community_framework.db")
    conn.execute("DELETE FROM reports WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('history'))

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        session['user_name'] = request.form.get("user_name")
        return redirect(url_for('index'))
    return render_template("join.html")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(port=5000, use_reloader=False)).start()
    webview.create_window("Community Framework Evaluation", "http://127.0.0.1:5000", width=1100, height=900)
    webview.start()
