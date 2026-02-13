import os
import sqlite3
import uuid
import datetime
import google.generativeai as genai  # <--- NEW: AI Library
from flask import Flask, render_template, request, jsonify, session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
# 🔴 IMPORTANT: Replace with your actual API Key from Google AI Studio
GENAI_API_KEY = "AIzaSyBoVYEgH8sSw5s-WtpblGxom4FTSfRxvIw"

# Configure the AI
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# System instructions: Tells the AI how to behave
SYSTEM_INSTRUCTION = (
    "You are a compassionate, empathetic mental wellness companion for college students. "
    "Your name is 'Wellness Companion'. "
    "Keep your responses short (2-3 sentences max), warm, and supportive. "
    "Never give medical diagnoses. "
    "If the user seems stressed, offer simple breathing or grounding techniques. "
    "If the user mentions self-harm or suicide, kindly but firmly urge them to seek professional help immediately."
)

# --- PATH SETUP ---
# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "chats.db")

# Ensure data folder exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Initialize Flask
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
    # Initialize history for the AI memory
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

    # --- 1. LOCAL SAFETY CHECK (Must stay for your Project Grade!) ---
    # We check for crisis keywords LOCALLY to ensure the red safety box triggers.
    crisis_words = ["suicide", "kill myself", "self-harm", "hopeless", "end my life", "die", "death"]
    
    if any(word in user_message.lower() for word in crisis_words):
        bot_response = (
            "I'm hearing a lot of pain in your words, and I want you to be safe. "
            "Please, reach out to the crisis support number on the left immediately. "
            "You are not alone."
        )
        sentiment_score = -0.9
        # Don't send this to AI, handle it immediately for safety
        save_chat(user_message, bot_response, sentiment_score)
        return jsonify({"response": bot_response})

    # --- 2. SENTIMENT ANALYSIS (For the Mood Tracker Graph) ---
    sentiment = analyzer.polarity_scores(user_message)
    sentiment_score = sentiment["compound"]

    # --- 3. GENERATE REAL AI RESPONSE ---
    try:
        # Retrieve history to give the AI context
        history = session.get("history", [])
        
        # Start chat with history
        chat_session = model.start_chat(history=history)
        
        # Send message with system instruction
        full_prompt = f"{SYSTEM_INSTRUCTION}\n\nUser: {user_message}"
        response = chat_session.send_message(full_prompt)
        
        bot_response = response.text
        
        # Update history (keep only last 5 exchanges to save memory)
        # We need to convert objects to dictionaries for session storage if needed, 
        # but Gemini uses a specific object format. 
        # For simplicity in this session storage, we recreate the history object next time.
        # A simpler way for session storage is just appending text:
        history.append({"role": "user", "parts": [user_message]})
        history.append({"role": "model", "parts": [bot_response]})
        
        if len(history) > 10: 
            history = history[-10:]
            
        session["history"] = history

    except Exception as e:
        print(f"AI Error: {e}")
        # Fallback if AI fails (e.g., no internet or quota limit)
        if sentiment_score < -0.5:
             bot_response = "I'm having trouble connecting to my brain, but I sense you are stressed. Take a deep breath."
        else:
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
    # This keeps your Render configuration perfect
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)