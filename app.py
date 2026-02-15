import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

load_dotenv() 

# --- CONFIGURATION ---
MODEL_ID = "gemma-3-27b-it" 
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")

# Database Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "chats.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS chats (
            session_id TEXT, user_message TEXT, bot_response TEXT, 
            sentiment_score REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")

init_db()
analyzer = SentimentIntensityAnalyzer()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message: return jsonify({"response": "..."})

    try:
        # Initialize client inside the route to ensure API key is fresh
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=user_message
        )
        
        bot_response = response.text 
        score = analyzer.polarity_scores(user_message)['compound']

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO chats (session_id, user_message, bot_response, sentiment_score) VALUES (?, ?, ?, ?)",
                         (session.get("session_id", "anon"), user_message, bot_response, score))

        return jsonify({"response": bot_response})

    except Exception as e:
        # This helps us see errors in Render Logs if something breaks later
        print(f"ERROR: {e}")
        return jsonify({"response": "I'm having a brief connection moment. Please try again in a few seconds!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))