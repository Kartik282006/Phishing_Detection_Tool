#!/usr/bin/env python3
"""
Flask backend for Phishing Attack Attribution & Risk Intelligence System.
Provides web UI and JSON API for URL analysis.
"""

import sqlite3
import datetime
import csv
import io
import re
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response, make_response
from flask_cors import CORS

from analysis_engine import analyze_url
from history_analyzer import HistoryAnalyzer
from llm_engine import LLMEngine

app = Flask(__name__)
app.secret_key = 'super_secure_secret_key_change_me' # Required for session

# Initialize Chatbot Engines
history_engine = HistoryAnalyzer()
llm_engine = LLMEngine()
# Enable CORS with specific configuration for Chrome extensions
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
DATABASE = 'database.db'

# Add explicit CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ─── Health probe (used by browser extension) ────────────────────────
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def api_health():
    """Lightweight liveness probe for the Chrome extension."""
    return jsonify({'status': 'ok', 'version': '2.0'}), 200

def init_db():
    """Create the scans table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            score INTEGER NOT NULL,
            level TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            response_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_scan(url, score, level):
    """Insert a new scan record into the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    c.execute('INSERT INTO scans (url, score, level, timestamp) VALUES (?, ?, ?, ?)',
              (url, score, level, timestamp))
    conn.commit()
    conn.close()

def get_recent_scans(limit=10):
    """Retrieve the most recent scans."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, url, score, level, timestamp FROM scans ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_scans():
    """Retrieve all scans (for history page)."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT url, score, level, timestamp FROM scans ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_scans_with_id():
    """Retrieve all scans with ID (for exports)."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT id, url, score, level, timestamp FROM scans ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_statistics():
    """Return total scans and count of High+Critical scans."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM scans')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM scans WHERE level IN ("High", "Critical")')
    high_critical = c.fetchone()[0]
    conn.close()
    return total, high_critical

@app.route('/')
def dashboard():
    """Render dashboard with stats and recent scans."""
    total, high_critical = get_statistics()
    recent = get_recent_scans()
    return render_template('dashboard.html',
                          total_scans=total,
                          high_critical_scans=high_critical,
                          recent_scans=recent)

@app.route('/history')
def history():
    """Render full scan history."""
    scans = get_all_scans()
    return render_template('history.html', scans=scans)

@app.route('/scan', methods=['POST'])
def scan_web():
    """Handle form submission from dashboard."""
    url = request.form.get('url', '').strip()
    if not url:
        return redirect(url_for('dashboard'))
    result = analyze_url(url)
    insert_scan(url, result['score'], result['level'])
    return redirect(url_for('dashboard'))

@app.route('/delete_scan/<int:scan_id>', methods=['POST'])
def delete_scan(scan_id):
    """Delete a specific scan record."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/clear_scans', methods=['POST'])
def clear_scans():
    """Delete ALL scan records."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('DELETE FROM scans')
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ─── Export Routes ───────────────────────────────────────────────

@app.route('/export/csv')
def export_csv():
    """Export all scans as a downloadable CSV file."""
    scans = get_all_scans_with_id()
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'phishing_scans_{now}.csv'

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'URL', 'Score', 'Level', 'Timestamp'])

    if scans:
        for row in scans:
            writer.writerow(row)
    else:
        writer.writerow(['', 'No scan records found', '', '', ''])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/export/pdf')
def export_pdf():
    """Export all scans as a downloadable PDF report."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    scans = get_all_scans_with_id()
    now = datetime.datetime.now()
    filename = f'phishing_scans_{now.strftime("%Y%m%d_%H%M%S")}.pdf'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=40, bottomMargin=40,
                            leftMargin=40, rightMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle('ReportTitle', parent=styles['Title'],
                                  fontSize=20, textColor=colors.HexColor('#1e293b'),
                                  spaceAfter=6)
    elements.append(Paragraph('Phishing Scan History Report', title_style))

    # Date
    date_style = ParagraphStyle('DateLine', parent=styles['Normal'],
                                 fontSize=10, textColor=colors.HexColor('#64748b'),
                                 spaceAfter=20)
    elements.append(Paragraph(f'Generated: {now.strftime("%Y-%m-%d %H:%M:%S")}', date_style))
    elements.append(Spacer(1, 12))

    # Table data
    header = ['ID', 'URL', 'Score', 'Level', 'Timestamp']
    if scans:
        # Truncate long URLs for PDF readability
        table_data = [header]
        for row in scans:
            url_text = row[1] if len(row[1]) <= 50 else row[1][:47] + '...'
            table_data.append([str(row[0]), url_text, str(row[2]), row[3], row[4]])
    else:
        table_data = [header, ['', 'No scan records found', '', '', '']]

    col_widths = [0.4*inch, 2.5*inch, 0.6*inch, 0.8*inch, 1.5*inch]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Style
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    # Alternating row colors
    for i in range(1, len(table_data)):
        bg = colors.HexColor('#f8fafc') if i % 2 == 0 else colors.HexColor('#e2e8f0')
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def api_analyze():
    """JSON API endpoint for URL analysis (v2: accepts page_signals from content script)."""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing URL'}), 400

    url = data['url'].strip()

    # Page-level signals collected by the extension's content script
    page_signals = data.get('page_signals', [])
    if not isinstance(page_signals, list):
        page_signals = []

    result = analyze_url(url, page_signals=page_signals)
    insert_scan(url, result['score'], result['level'])
    return jsonify(result)

# Chatbot Route
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"response": "Please say something!", "type": "warning"})

    # Session history management
    if 'history' not in session:
        session['history'] = []
    
    # 1. Check for specific voice commands
    lower_message = user_message.lower()
    response_data = {}
    is_command_handled = False
    
    # Command: Scan a URL
    if "scan" in lower_message:
        urls = re.findall(r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}', lower_message)
        if urls:
            target_url = urls[0] if urls[0].startswith("http") else "https://" + urls[0]
            result = analyze_url(target_url)
            insert_scan(target_url, result['score'], result['level'])
            spoken_domain = urls[0]
            formatted_response = f"I scanned {spoken_domain}. The risk score is {result['score']}, and the threat level is marked as {result['level']}."
            response_data = {"response": formatted_response, "type": "scan_command"}
            is_command_handled = True
            
    # Command: Show History
    elif "history" in lower_message and ("show" in lower_message or "my" in lower_message or "recent" in lower_message):
        recent = get_recent_scans(3)
        if not recent:
            formatted_response = "I couldn't find any recent scans in your history."
        else:
            formatted_response = "Here are your most recent scans: \n\n"
            for row in recent:
                formatted_response += f"• {row[1]} resulted in a **{row[3]}** risk.\n"
        response_data = {"response": formatted_response, "type": "history_command"}
        is_command_handled = True

    # 2. Check for Browsing History (Heuristic)
    lines = user_message.split('\n')
    http_count = sum(1 for line in lines if "http" in line.lower())
    
    if is_command_handled:
        pass # Response already generated by command handlers
        
    elif http_count > 0:
        # Treat as History Analysis
        analysis_result = history_engine.analyze_history(user_message)
        
        # Format response for chat using Markdown
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

    # Log to DB (Reuse DATABASE='database.db')
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO chats (user_message, bot_response, response_type) VALUES (?, ?, ?)",
                    (user_message, response_data['response'], response_data['type']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Chat DB Error: {e}")

    return jsonify(response_data)

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)