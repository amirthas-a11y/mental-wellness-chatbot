import os
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chats.db" # Updated to match your file name

analyzer = SentimentIntensityAnalyzer()
MODEL_ID = "gemini-1.5-flash" # Higher quota for demo

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_data = request.json
    user_message = user_data.get("message", "").strip()
    session_id = user_data.get("session_id", str(uuid.uuid4()))
    
    if not user_message:
        return jsonify({"response": "I'm listening, bro. Go ahead.", "score": 0})

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        persona = "You are 'Buddy', a chill college companion. Use casual language (bro, yaar). Keep it brief."

        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        
        bot_response = response.text 
        vs = analyzer.polarity_scores(user_message)
        score = float(vs['compound'])

        # Log to Database matching your exact schema
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (session_id, user_message, bot_response, sentiment_score, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, user_message, bot_response, score, datetime.now().isoformat())
            )
            conn.commit()

        return jsonify({"response": bot_response, "score": score, "session_id": session_id})

    except Exception as e:
        if "429" in str(e):
            return jsonify({"response": "Too many requests! Wait 30 seconds, buddy.", "score": 0})
        return jsonify({"response": "Connection shaky, but I'm here.", "score": 0})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))