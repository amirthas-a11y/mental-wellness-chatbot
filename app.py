import os
import sqlite3
import uuid
from flask import Flask, render_template, request, jsonify, session
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv  # <--- Add this

# Load variables from .env file
load_dotenv() 

# --- CONFIGURATION ---
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Using the newest Gemini 3 model from your list
MODEL_ID = "gemini-3-flash-preview"

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

@app.before_request
def create_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "I didn't hear anything."})

    # Simple Crisis Check
    if any(word in user_message.lower() for word in ["suicide", "kill myself", "harm"]):
        return jsonify({"response": "I'm concerned about you. Please reach out to a professional or a crisis hotline immediately."})

    try:
        # Generate Response using new SDK syntax
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=user_message,
            config={'system_instruction': 'You are a supportive, brief mental health companion.'}
        )
        bot_response = response.text

        # Sentiment Analysis
        score = analyzer.polarity_scores(user_message)['compound']

        # Save to DB
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO chats (session_id, user_message, bot_response, sentiment_score) VALUES (?, ?, ?, ?)",
                         (session["session_id"], user_message, bot_response, score))

        return jsonify({"response": bot_response})

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"response": "I'm having a little trouble connecting. Try again in a second?"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))