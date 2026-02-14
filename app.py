import os
import sqlite3
import uuid
import datetime
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
# Use the fallback key if Render's secret key isn't found
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBoVYEgH8sSw5s-WtpblGxom4FTSfRxvIw")

genai.configure(api_key=API_KEY)

# Use the stable 'gemini-pro' model
model = genai.GenerativeModel('gemini-pro')

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "chats.db")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

app = Flask(__name__)
app.secret_key = "supersecretkey"

analyzer = SentimentIntensityAnalyzer()

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            session_id TEXT,
            user_message TEXT,
            bot_response TEXT,
            sentiment_score REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
        return jsonify({"response": "I didn't catch that. Could you say it again?"})

    # --- 1. LOCAL SAFETY CHECK ---
    crisis_words = ["suicide", "kill myself", "self-harm", "hopeless", "end my life", "die", "death"]
    
    if any(word in user_message.lower() for word in crisis_words):
        bot_response = (
            "I'm hearing a lot of pain in your words, and I want you to be safe. "
            "Please, reach out to the crisis support number on the left immediately. "
            "You are not alone."
        )
        sentiment_score = -0.9
        save_chat(user_message, bot_response, sentiment_score)
        return jsonify({"response": bot_response})

    # --- 2. SENTIMENT ANALYSIS ---
    sentiment = analyzer.polarity_scores(user_message)
    sentiment_score = sentiment["compound"]

    # --- 3. GENERATE REAL AI RESPONSE ---
    try:
        # Retrieve history
        history = session.get("history", [])
        
        # Start chat with history
        chat_session = model.start_chat(history=history)
        
        # SYSTEM INSTRUCTION (Manually added only for the current turn to avoid confusion)
        system_instruction = (
            "You are a compassionate, empathetic mental wellness companion for college students. "
            "Your name is 'Wellness Companion'. "
            "Keep your responses short (2-3 sentences max), warm, and supportive. "
            "If the user says 'hi', simply welcome them warmly. "
            "Never give medical diagnoses."
        )

        # We combine the instruction + user message, but we DON'T save the instruction to history
        full_prompt = f"{system_instruction}\n\nUser said: {user_message}"
        
        response = chat_session.send_message(full_prompt)
        bot_response = response.text
        
        # Update history with just the CLEAN message (no instructions)
        history.append({"role": "user", "parts": [user_message]})
        history.append({"role": "model", "parts": [bot_response]})
        
        if len(history) > 10: 
            history = history[-10:]
            
        session["history"] = history

    except Exception as e:
        # IMPORTANT: This prints the REAL error to the logs so we can see it
        print(f"------------ AI ERROR ------------\n{e}\n----------------------------------")
        bot_response = "I'm having a little trouble connecting right now. Can you try again?"

    # --- 4. SAVE & RETURN ---
    save_chat(user_message, bot_response, sentiment_score)
    return jsonify({"response": bot_response})

def save_chat(user_msg, bot_resp, score):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?, ?)",
                  (session["session_id"], user_msg, bot_resp, score, str(datetime.datetime.now())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)