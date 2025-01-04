from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
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

    # Check if the entry already exists (case-insensitive)
    conn = sqlite3.connect('compatibility.db')
    c = conn.cursor()
    c.execute("SELECT score FROM entries WHERE LOWER(your_name) = LOWER(?) AND LOWER(crush_name) = LOWER(?)", 
              (your_name, crush_name))
    result = c.fetchone()

    if result:
        # If entry exists, fetch the compatibility score
        compatibility = int(result[0])
    else:
        # If entry doesn't exist, calculate compatibility score
        combined = f"{your_name.lower()}-{crush_name.lower()}"
        score = md5(combined.encode()).hexdigest()[:4]
        compatibility = int(score, 16) % 100

        # Insert the new entry into the database
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

@app.route('/dashboard/edit', methods=['GET', 'POST'])
def edit_entry():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = sqlite3.connect('compatibility.db')
    c = conn.cursor()

    if request.method == 'POST':
        entry_id = request.form['id']
        your_name = request.form['yourName'].strip()
        crush_name = request.form['crushName'].strip()
        score = request.form['score'].strip()

        # Update entry in the database
        c.execute("UPDATE entries SET your_name = ?, crush_name = ?, score = ? WHERE id = ?", 
                  (your_name, crush_name, score, entry_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))

    # Fetch the specific entry to edit
    entry_id = request.args.get('id')
    c.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    entry = c.fetchone()
    conn.close()
    
    if entry:
        return render_template('edit.html', entry=entry)
    else:
        return "Entry not found", 404

@app.route('/logout')
def logout():
    # Log out the admin and clear session
    session.pop('admin', None)
    return redirect(url_for('home'))

# Route to download the compatibility.db file
@app.route('/db')
def download_db():
    return send_from_directory(directory=".", filename="compatibility.db", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
