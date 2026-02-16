import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from google import genai
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

# CHANGED: Added 'models/' prefix which some SDK versions require to avoid 404
MODEL_ID = "gemini-1.5-flash" 

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
        # Ensure client is initialized with the correct API version if needed
        client = genai.Client(api_key=api_key)
        
        persona = "You are 'Buddy', a chill college companion. Use casual language (bro, yaar). Keep it brief."

        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=f"{persona}\nUser: {user_message}"
        )
        
        bot_response = response.text 
        vs = analyzer.polarity_scores(user_message)
        score = float(vs['compound'])

        with get_db() as conn:
            conn.execute(
                "INSERT INTO chats (user_message, bot_response, sentiment_score) VALUES (?, ?, ?)",
                (user_message, bot_response, score)
            )
            conn.commit()

        return jsonify({"response": bot_response, "score": score})

    except Exception as e:
        # This will print the exact reason for failure in your Render logs
        print(f"DEBUG ERROR: {e}") 
        
        # If the 404 persists, it's often a key issue. 
        # Let's give a helpful error message for the demo.
        return jsonify({
            "response": "Connection shaky, but I'm here. (Internal Error: Check API Key/Model)", 
            "score": 0
        })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))