import os
import sqlite3
import uuid
import datetime
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
# This line tries to get the key from Render. 
# If Render doesn't have it, it uses your specific key (the second part).
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBoVYEgH8sSw5s-WtpblGxom4FTSfRxvIw")

# Configure the AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- APP SETUP ---
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "chats.db")

# Ensure Data Folder Exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            session_id TEXT, user_message TEXT, bot_response TEXT, 
            sentiment_score REAL, timestamp TEXT
        )
    """)
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

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "I didn't hear that."})

    # 1. Safety Check
    crisis_words = ["suicide", "kill myself", "die", "death", "end it"]
    if any(word in user_message.lower() for word in crisis_words):
        return jsonify({"response": "I am concerned for your safety. Please contact a crisis helpline immediately."})

    # 2. Sentiment
    score = analyzer.polarity_scores(user_message)["compound"]

    # 3. AI Response
    try:
        # Get history
        history = session.get("history", [])
        chat = model.start_chat(history=history)
        
        # System Instruction Prompt
        instruction = "You are a warm, empathetic mental health companion for students. Keep answers short (2 sentences)."
        full_prompt = f"{instruction}\n\nUser: {user_message}"
        
        response = chat.send_message(full_prompt)
        bot_response = response.text

        # Update History
        history.append({"role": "user", "parts": [user_message]})
        history.append({"role": "model", "parts": [bot_response]})
        session["history"] = history[-10:] # Keep last 10 messages

    except Exception as e:
        print(f"ERROR: {e}") # Print error to logs
        bot_response = "I'm having trouble connecting to the server. Please try again."

    # 4. Save to DB
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?, ?)", 
                  (session["session_id"], user_message, bot_response, score, str(datetime.datetime.now())))
        conn.commit()
        conn.close()
    except:
        pass

    return jsonify({"response": bot_response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)