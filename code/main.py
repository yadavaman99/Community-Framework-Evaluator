from flask import Flask, render_template, request, redirect, url_for, session
import wikipedia
import sqlite3
import json
import threading
import webview
import re

app = Flask(__name__)
app.secret_key = "smalteval_pro_key"

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("app_analysis.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            category TEXT,
            study_impact TEXT,
            safety TEXT,
            risks TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- UPDATED ANALYSIS LOGIC ----------------
def clean_text(text):
    text = text.lower()
    return re.sub(r'[^a-zA-Z0-9\s-]', ' ', text)

# Expanded Keywords for better YouTube/Duolingo detection
SOCIAL_KEYWORDS = ["social", "messenger", "chat", "photo-sharing", "multimedia", "ephemeral", "messaging", "stories", "snap", "filter"]
EDUCATION_KEYWORDS = ["curriculum", "syllabus", "textbook", "educational tool", "tutoring", "classroom", "e-learning", "academic", "course", "lesson", "study", "language", "physics", "math"]
ENTERTAINMENT_KEYWORDS = ["video", "streaming", "music", "entertainment", "media", "movie", "youtube", "watch", "content creator"]

def classify_app_type(text):
    text = clean_text(text)
    scores = {"Educational": 0, "Social Media": 0, "Entertainment": 0, "Gaming": 0, "Productivity": 0}
    
    for word in SOCIAL_KEYWORDS:
        if word in text: scores["Social Media"] += 3
    for word in EDUCATION_KEYWORDS:
        if word in text: scores["Educational"] += 3
    for word in ENTERTAINMENT_KEYWORDS:
        if word in text: scores["Entertainment"] += 4 # High weight for YouTube types

    # Trap Fix: University mentions in tech history
    if "university" in text and ("messaging" in text or "video" in text):
        scores["Educational"] -= 3 

    best_category = max(scores, key=scores.get)
    return [best_category] if scores[best_category] > 0 else ["General Utility"]

def calculate_study_rating(text):
    text = clean_text(text)
    edu_score = sum(2 for word in EDUCATION_KEYWORDS if word in text)
    distraction_score = sum(1 for word in (SOCIAL_KEYWORDS + ENTERTAINMENT_KEYWORDS) if word in text)
    
    final = edu_score - distraction_score
    if final >= 4: return "🔥 Highly Beneficial"
    elif final >= 1: return "✅ Good for Studies"
    return "❌ Low Study Value (Distraction Risk)"

def detect_risks(text):
    text = clean_text(text)
    safety, risks = [], []
    if any(x in text for x in ["addiction", "distract", "algorithm", "autoplay"]): risks.append("High Engagement/Addiction")
    if any(x in text for x in ["privacy", "data", "ads"]): risks.append("Ad-Tracking/Data Privacy")
    if any(x in text for x in ["learn", "educat", "language", "tutorial"]): safety.append("Educational Content")
    if "free" in text: safety.append("Free to use")
    
    if not risks: risks.append("No critical risks found")
    if not safety: safety.append("General utility features")
    return safety, risks

# ---------------- ROUTES ----------------

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        session['user_name'] = request.form.get("user_name")
        return redirect(url_for('index'))
    return render_template("join.html")

@app.route("/", methods=["GET", "POST"])
def index():
    if 'user_name' not in session: return redirect(url_for('join'))
    result = None
    if request.method == "POST":
        app_name = request.form["app_name"]
        try:
            search_results = wikipedia.search(app_name, results=1)
            if not search_results:
                return render_template("index.html", result={"error": "App not found"}, user_name=session['user_name'])
            
            page_title = search_results[0]
            summary = wikipedia.summary(page_title, sentences=5, auto_suggest=False)

            category = classify_app_type(summary)
            study_impact = calculate_study_rating(summary)
            safety, risks = detect_risks(summary)

            result = {"app_name": page_title, "category": category, "study_impact": study_impact, "safety": safety, "risks": risks}

            conn = sqlite3.connect("app_analysis.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO analysis (app_name, category, study_impact, safety, risks) VALUES (?, ?, ?, ?, ?)",
                           (page_title, json.dumps(category), study_impact, json.dumps(safety), json.dumps(risks)))
            conn.commit()
            conn.close()
        except Exception:
            result = {"error": "Search failed. Please be more specific."}
    return render_template("index.html", result=result, user_name=session['user_name'])

@app.route("/history")
def history():
    if 'user_name' not in session: return redirect(url_for('join'))
    conn = sqlite3.connect("app_analysis.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    stats = {"Educational": 0, "Social Media": 0, "Entertainment": 0, "Gaming": 0, "Productivity": 0}
    history_list = []
    for row in rows:
        cat = json.loads(row["category"])[0]
        if cat in stats: stats[cat] += 1
        history_list.append({"id": row["id"], "app_name": row["app_name"], "category": cat, "impact": row["study_impact"]})

    return render_template("history.html", history=history_list, stats=json.dumps(stats), user_name=session['user_name'])

@app.route("/compare", methods=["POST"])
def compare():
    ids = request.form.getlist("compare_ids")
    if len(ids) != 2: return redirect(url_for('history'))
    conn = sqlite3.connect("app_analysis.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM analysis WHERE id IN ({ids[0]}, {ids[1]})")
    apps = cursor.fetchall()
    conn.close()
    
    comparison_data = []
    for app in apps:
        comparison_data.append({"name": app["app_name"], "cat": json.loads(app["category"])[0], "impact": app["study_impact"], "safety": json.loads(app["safety"]), "risks": json.loads(app["risks"])})
    return render_template("compare.html", apps=comparison_data)

@app.route("/clear")
def clear():
    conn = sqlite3.connect("app_analysis.db")
    conn.cursor().execute("DELETE FROM analysis")
    conn.commit()
    conn.close()
    return redirect(url_for('history'))

@app.route("/reset")
def reset():
    session.pop('user_name', None)
    return redirect(url_for('join'))

def start_flask():
    app.run(port=5000)

if __name__ == "__main__":
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()
    webview.create_window("Smart Evaluator Pro", "http://127.0.0.1:5000", width=1000, height=800)
    webview.start()
