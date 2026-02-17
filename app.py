import os
import sqlite3
import random
import requests  # Use standard requests instead of the buggy SDK
from flask import Flask, render_template, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

SAFE_RESPONSES = [
    "I hear you, bro. That sounds tough, but you've got this!",
    "Arre yaar, I'm always in your corner. Tell me more?",
    "Exam stress is real, buddy. Take a deep breath, I'm listening."
]

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
        api_key = os.environ.get("GEMINI_API_KEY")
        # FORCING THE STABLE V1 URL MANUALLY
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"You are 'Buddy', a chill college friend. Use casual language (bro, yaar). Max 2 sentences. User says: {user_message}"
                }]
            }]
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        res_json = response.json()

        # Extracting the text from the raw response
        bot_response = res_json['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        print(f"DIRECT API ERROR: {e}")
        bot_response = random.choice(SAFE_RESPONSES)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                        (user_message, bot_response, score))
            conn.commit()
    except:
        pass 

    return jsonify({"response": bot_response, "score": score})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))