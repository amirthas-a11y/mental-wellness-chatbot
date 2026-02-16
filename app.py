import os
import sqlite3
import random
import google.generativeai as genai  # THE STABLE ONE
from flask import Flask, render_template, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "wellness_buddy_2026")
DB_PATH = "chat_history.db"

analyzer = SentimentIntensityAnalyzer()

# DETAILED EMERGENCY RESPONSES
FAMILY_RESPONSES = [
    "Missing home is so real, buddy. Hostel life can be lonely. What do you miss most about being with them?",
    "Family stuff is complicated, yaar. It hurts when you feel the love isn't matching up. Want to talk more about it?",
    "I'm sorry you're feeling disconnected from them. I'm here to listen. What's on your mind?"
]

ACADEMIC_RESPONSES = [
    "Project stress is the worst! I've been there. What's the specific error that's frustrating you?",
    "Don't let the code win, bro! Take a deep breath. What's the main thing you need to finish for the micro-project?",
    "Frustration is part of coding, yaar. Tell me exactly what happened with the code."
]

GENERAL_RESPONSES = [
    "I hear you, bro. That sounds tough, but you've got this!",
    "Arre yaar, I'm always in your corner. Tell me more?",
    "I'm listening, buddy. Go ahead, vent it all out."
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
    msg_lower = user_message.lower()
    
    if not user_message:
        return jsonify({"response": "I'm listening, bro.", "score": 0})

    vs = analyzer.polarity_scores(user_message)
    score = float(vs['compound'])

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        persona = "You are 'Buddy', a chill college friend. Use casual language (bro, yaar). Max 2 sentences."
        response = model.generate_content(f"{persona}\nUser: {user_message}")
        bot_response = response.text 
        
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        # KEYWORD LOGIC: Make Buddy ask detailed questions even if API fails
        if any(word in msg_lower for word in ["family", "home", "parents", "miss"]):
            bot_response = random.choice(FAMILY_RESPONSES)
        elif any(word in msg_lower for word in ["code", "project", "error", "frustrat", "micro"]):
            bot_response = random.choice(ACADEMIC_RESPONSES)
        else:
            bot_response = random.choice(GENERAL_RESPONSES)

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