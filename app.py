import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

# Initialize tools
analyzer = SentimentIntensityAnalyzer()

# Use the most stable model string for the SDK
MODEL_ID = "gemini-1.5-flash"

def init_db():
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

init_db()

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_data = request.json
    user_message = user_data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"response": "I'm listening, bro. Go ahead.", "score": 0})

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        persona = (
            "You are 'Buddy', a chill, empathetic college companion. "
            "Use casual language (bro, yaar, buddy). Support students with hostel life, "
            "academic stress, and project deadlines. Keep it brief (2 sentences max)."
        )

        # Generating content using the stable model ID
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        bot_response = response.text 

        # Calculate sentiment
        vs = analyzer.polarity_scores(user_message)
        score = float(vs['compound'])

        # Save to DB
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                (user_message, bot_response, score)
            )
            conn.commit()

        return jsonify({"response": bot_response, "score": score})

    except Exception as e:
        print(f"ERROR: {e}")
        # EMERGENCY FALLBACK: If API fails, Buddy still responds!
        return jsonify({
            "response": "Arre yaar, my brain is a bit jammed from the exams. But I'm listening—tell me what's on your mind?",
            "score": 0
        })

@app.route("/clear_history", methods=["POST"])
def clear_history():
    with get_db() as conn:
        conn.execute("DELETE FROM chats")
        conn.commit()
    return jsonify({"status": "History Nuked!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)