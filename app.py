import os
import sqlite3
import uuid
import datetime
from flask import Flask, render_template, request, jsonify, session
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "chats.db")

# Ensure data folder exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# Initialize Flask (It automatically looks for a 'templates' folder in the same directory)
app = Flask(__name__)
app.secret_key = "supersecretkey"

analyzer = SentimentIntensityAnalyzer()

# Initialize Database
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

@app.route("/")
def home():
    # This MUST match the filename inside your templates folder
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"response": "I didn't catch that. Could you say it again?"})

    sentiment = analyzer.polarity_scores(user_message)
    score = sentiment["compound"]

    # Crisis detection
    crisis_words = ["suicide", "kill myself", "self-harm", "hopeless", "end my life"]

    if any(word in user_message.lower() for word in crisis_words):
        bot_response = (
            "I'm really concerned about what you're sharing. "
            "You are not alone. Please consider reaching out to a trusted person "
            "or professional counselor immediately."
        )
    else:
        if score <= -0.5:
            bot_response = "It seems you're feeling very stressed. Try taking a deep breath. Would you like a simple relaxation exercise?"
        elif score < 0:
            bot_response = "I sense some stress. Talking about it might help. I'm here to listen."
        elif score < 0.5:
            bot_response = "Thank you for sharing. How else are you feeling today?"
        else:
            bot_response = "That's great to hear! Keep maintaining your positive mindset."

    # Save chat to database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO chats VALUES (?, ?, ?, ?, ?)",
                  (session["session_id"], user_message, bot_response, score, str(datetime.datetime.now())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

    return jsonify({"response": bot_response})

if __name__ == "__main__":
     port = int(os.environ.get("PORT", 10000))
     app.run(host="0.0.0.0", port=port)
