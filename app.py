import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from google import genai  # This matches the 'google-genai' library
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_data = request.json
    user_message = user_data.get("message", "").strip()
    
    # LOCAL Sentiment analysis (Always works!)
    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"You are Buddy, a chill college friend. Keep it brief. User says: {user_message}"
        )
        bot_response = response.text 
        
    except Exception as e:
        print(f"ERROR: {e}")
        bot_response = "I hear you, bro. Tell me more?"

    return jsonify({"response": bot_response, "score": score})

if __name__ == "__main__":
    # This line fixes the "No open ports detected" error
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)