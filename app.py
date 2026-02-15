import os
import sqlite3
import uuid
import datetime
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
# PASTE YOUR NEW KEY BELOW where it says PASTE_HERE
# (Keep the quote marks!)
MY_NEW_KEY = "PASTE_HERE" 

# We try the environment key first, then your new hardcoded key
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBQqtyaDWPESpJSXBk67kwjXPM8e9pf6CU")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "chats.db")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS chats (
            session_id TEXT, user_message TEXT, bot_response TEXT, 
            sentiment_score REAL, timestamp TEXT)""")
    conn.commit()
    conn.close()

init_db()
analyzer = SentimentIntensityAnalyzer()

@app.before_request
def create_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    if "history" not in session:
        session["history"] = []

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "I didn't hear that."})

    # Local Safety Check
    crisis_words = ["suicide", "kill myself", "die", "death"]
    if any(word in user_message.lower() for word in crisis_words):
        return jsonify({"response": "Please seek help immediately. You are not alone."})

    sentiment_score = analyzer.polarity_scores(user_message)["compound"]

    try:
        history = session.get("history", [])
        chat = model.start_chat(history=history)
        
        system_instruction = "You are a supportive mental health companion. Keep answers short."
        full_prompt = f"{system_instruction}\n\nUser: {user_message}"
        
        response = chat.send_message(full_prompt)
        bot_response = response.text

        history.append({"role": "user", "parts": [user_message]})
        history.append({"role": "model", "parts": [bot_response]})
        session["history"] = history[-10:]

    except Exception as e:
        # --- DEBUG MODE: SHOW ERROR IN CHAT ---
        print(f"AI ERROR: {e}")
        # This puts the ACTUAL error on your screen
        bot_response = f"SYSTEM ERROR: {str(e)}"

    return jsonify({"response": bot_response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)