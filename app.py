import os
import sqlite3
import random
import google.generativeai as genai  # SWITCHED TO STABLE
from flask import Flask, render_template, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

# Safety Responses (Buddy will use these if the API fails)
SAFE_RESPONSES = [
    "I hear you, bro. That sounds tough, but you've got this!",
    "Arre yaar, I'm always in your corner. Tell me more?",
    "Exam stress is real, buddy. Take a deep breath, I'm listening."
]

# Configure the STABLE API
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

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

    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    try:
        # This call uses the STABLE v1 API path
        model = genai.GenerativeModel('gemini-1.5-flash')
        persona = "You are 'Buddy', a chill college friend. Use casual language (bro, yaar). Max 2 sentences."
        
        response = model.generate_content(f"{persona}\nUser: {user_message}")
        bot_response = response.text 
        
    except Exception as e:
        print(f"STABLE API ERROR: {e}")
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