from flask import Flask, render_template, request, jsonify, session
import os
import sqlite3
import datetime
from history_analyzer import HistoryAnalyzer
from llm_engine import LLMEngine

app = Flask(__name__)
app.secret_key = os.urandom(24) # Secure secret key for sessions

# Initialize Engines
history_engine = HistoryAnalyzer()
llm_engine = LLMEngine()

# Database Setup
DB_NAME = "chatbot.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                bot_response TEXT,
                response_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

init_db()

def log_chat(user_msg, bot_resp, resp_type):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO chats (user_message, bot_response, response_type) VALUES (?, ?, ?)",
                         (user_msg, bot_resp, resp_type))
    except Exception as e:
        print(f"DB Error: {e}")

@app.route('/')
def index():
    # Clear session history on refresh if desired, or keep it
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"response": "Please say something!", "type": "warning"})

    # Session history management
    if 'history' not in session:
        session['history'] = []
    
    # 1. Check for Browsing History (Heuristic)
    # Simple check: multiple lines with http/https
    lines = user_message.split('\n')
    http_count = sum(1 for line in lines if "http" in line.lower())
    
    response_data = {}
    
    if http_count > 0:
        # Treat as History Analysis
        analysis_result = history_engine.analyze_history(user_message)
        
        # Format response for chat
        formatted_response = f"**Risk Level: {analysis_result['risk_level']}**\n\n"
        formatted_response += f"{analysis_result['summary']}\n\n"
        
        if analysis_result['detailed_analysis']:
            formatted_response += "**Issues Found:**\n"
            for issue in analysis_result['detailed_analysis']:
                formatted_response += f"- [{issue['risk']}] {issue['entry']}: {', '.join(issue['reasons'])}\n"
        
        if analysis_result['recommendations']:
            formatted_response += "\n**Recommendations:**\n"
            for rec in analysis_result['recommendations']:
                formatted_response += f"- {rec}\n"
                
        response_data = {
            "response": formatted_response,
            "type": "analysis"
        }
        
    else:
        # Treat as QA
        response_text = llm_engine.ask_llm(user_message, session['history'])
        response_data = {
            "response": response_text,
            "type": "qa"
        }
        
        # Update session history
        session['history'].append({"role": "user", "content": user_message})
        session['history'].append({"role": "assistant", "content": response_text})
        session.modified = True

    # Log to DB
    log_chat(user_message, response_data['response'], response_data['type'])

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, port=8000) # Run on 8000 to avoid conflict with Phishing Tool (5000)
