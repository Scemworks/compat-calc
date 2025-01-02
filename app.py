from flask import Flask, request, render_template, redirect, url_for, session
from hashlib import md5
import sqlite3
import secrets

# Initialize Flask app and secret key
app = Flask(__name__, static_folder='templates/static')
app.secret_key = secrets.token_hex(16)  # Generates a random secret key for security

# Initialize Database
def init_db():
    conn = sqlite3.connect('compatibility.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY, 
        your_name TEXT, 
        crush_name TEXT, 
        score TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def home():
    return render_template('index.html')  # Flask will look in the 'templates' folder

@app.route('/calculate', methods=['POST'])
def calculate():
    your_name = request.form['yourName'].strip()
    crush_name = request.form['crushName'].strip()
    
    # Ensure names are not empty
    if not your_name or not crush_name:
        return "Both names are required!", 400

    # Calculate compatibility score based on name combination
    combined = f"{your_name.lower()}-{crush_name.lower()}"
    score = md5(combined.encode()).hexdigest()[:4]
    compatibility = int(score, 16) % 100

    # Store result in the database
    conn = sqlite3.connect('compatibility.db')
    c = conn.cursor()
    
    # Check if the entry already exists (case-insensitive)
    c.execute("SELECT id FROM entries WHERE LOWER(your_name) = LOWER(?) AND LOWER(crush_name) = LOWER(?)", 
              (your_name, crush_name))
    result = c.fetchone()

    if result:
        # If entry exists, update the compatibility score
        c.execute("UPDATE entries SET score = ? WHERE id = ?", (str(compatibility), result[0]))
    else:
        # If entry doesn't exist, insert the new entry into the database
        c.execute("INSERT INTO entries (your_name, crush_name, score) VALUES (?, ?, ?)",
                  (your_name, crush_name, str(compatibility)))
    
    conn.commit()
    conn.close()

    # Generate a message based on the compatibility score
    message = "You are highly compatible!" if compatibility > 50 else "You might need to work on your relationship."

    # Return the result to the user
    return render_template('result.html', yourName=your_name, crushName=crush_name, compatibility=compatibility, message=message)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # Check admin credentials
        stored_password = '6d8c60f665759445ea282e026c307c3e'  # md5 hash of 'admin@crushcompatcalc'
        if request.form['username'] == 'admin' and md5(request.form['password'].encode()).hexdigest() == stored_password:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials", 401
    return render_template('admin.html')

@app.route('/dashboard')
def dashboard():
    # Ensure only admins can access the dashboard
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    # Fetch all entries from the database
    conn = sqlite3.connect('compatibility.db')
    c = conn.cursor()
    c.execute("SELECT * FROM entries")
    entries = c.fetchall()
    conn.close()
    
    return render_template('dashboard.html', entries=entries)

@app.route('/logout')
def logout():
    # Log out the admin and clear session
    session.pop('admin', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
