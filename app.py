import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

# Initialize tools
analyzer = SentimentIntensityAnalyzer()
MODEL_ID = "gemini-2.0-flash" 

def init_db():
    """Creates the database table if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT,
                bot_response TEXT,
                sentiment_score REAL
            )
        ''')
        conn.commit()

# Initialize DB on startup
init_db()

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "I'm listening, bro. Go ahead.", "score": 0})

    try:
        # Get API Key from environment variable
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"response": "API Key missing! Check your environment variables.", "score": 0})

        client = genai.Client(api_key=api_key)
        
        # THE PERSONA: Casual, multilingual, supportive, and safe
        persona = (
            "You are 'Buddy', a chill, empathetic college companion. "
            "Use casual language (bro, yaar, buddy). Support students with hostel life, "
            "academic stress, and project deadlines. If they speak Hindi or Bengali, "
            "respond in kind naturally. Never judge. Keep it brief (2-3 sentences max)."
        )

        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        bot_response = response.text 

        # Real-time Sentiment Tracking
        score = analyzer.polarity_scores(user_message)['compound']

        # Save to DB for the tracker
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                (user_message, bot_response, score)
            )
            conn.commit()

        return jsonify({"response": bot_response, "score": score})

    except Exception as e:
        print(f"DEPLOYMENT ERROR: {e}") # This shows in your Render logs
        return jsonify({"response": "System's a bit tired. Let's try again in a sec?", "score": 0})

@app.route("/clear_history", methods=["POST"])
def clear_history():
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM chats")
            conn.commit()
        return jsonify({"status": "History Nuked! 100% Private."})
    except Exception as e:
        return jsonify({"status": "Error clearing history"}), 500

if __name__ == "__main__":
    # Important for Render deployment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)