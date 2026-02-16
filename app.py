import os
import sqlite3
import random
from flask import Flask, render_template, request, jsonify
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

# THIS IS THE MOST STABLE MODEL STRING
MODEL_ID = "gemini-1.5-flash" 

SAFE_RESPONSES = [
    "I hear you, bro. That sounds tough, but you've got this!",
    "Arre yaar, I'm always in your corner. Tell me more?",
    "Exam stress is real, buddy. Take a deep breath, I'm listening.",
    "Hostel life can be a rollercoaster, right? I'm here to listen.",
    "That's a lot to handle. Remember, one step at a time, bro."
]

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
        return jsonify({"response": "I'm listening, bro.", "score": 0})

    # Sentiment is LOCAL - it will always work for your chart!
    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        # Initialize client specifically for the stable v1 API
        client = genai.Client(api_key=api_key)
        
        persona = "You are 'Buddy', a chill college companion. Use casual language (bro, yaar). Keep it brief."

        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        bot_response = response.text 
        
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        # If Google fails, Buddy uses the "Emergency" list
        bot_response = random.choice(SAFE_RESPONSES)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                (user_message, bot_response, score)
            )
            conn.commit()
    except:
        pass 

    return jsonify({"response": bot_response, "score": score})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))