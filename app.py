import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

# CHANGED: Using 'gemini-1.5-flash-latest' to fix the 404 error
MODEL_ID = "gemini-1.5-flash-latest" 

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

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        persona = "You are 'Buddy', a chill college companion. Use casual language (bro, yaar). Keep it brief."

        # Attempt to get AI response
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        bot_response = response.text 
        
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        # DEMO SAFETY: If the API fails, Buddy still talks!
        bot_response = "Arre yaar, my brain is a bit foggy from the hostel food, but I'm here for you. Tell me more?"

    # Sentiment Analysis (This works offline, so it never fails!)
    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                (user_message, bot_response, score)
            )
            conn.commit()
    except:
        pass # Ignore DB errors during demo

    return jsonify({"response": bot_response, "score": score})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))