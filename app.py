import os
import time
import sqlite3
import random  # <--- ADD THIS LINE HERE
import requests # Also make sure requests is imported if you're using it for the URL call!
from flask import Flask, render_template, request, jsonify, session
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

import time

@app.route("/chat", methods=["POST"])
def chat():
    user_data = request.json
    user_message = user_data.get("message", "").strip()
    
    # Process local sentiment first (always works!)
    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": f"You're 'Buddy', a chill college friend. Keep it brief. User: {user_message}"}]}]
    }

    # TRY-RETRY LOGIC for 2.0 Quota
    for attempt in range(2): 
        try:
            response = requests.post(url, json=payload)
            res_json = response.json()

            if 'candidates' in res_json:
                bot_response = res_json['candidates'][0]['content']['parts'][0]['text']
                break # Success!
            elif 'error' in res_json and res_json['error']['code'] == 429:
                print("Quota hit, waiting 2 seconds...")
                time.sleep(2) # Wait and try one last time
            else:
                bot_response = random.choice(SAFE_RESPONSES)
                break
        except:
            bot_response = random.choice(SAFE_RESPONSES)
            break
    else:
        bot_response = random.choice(SAFE_RESPONSES)

    return jsonify({"response": bot_response, "score": score})

if __name__ == "__main__":
    # Important for Render deployment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)