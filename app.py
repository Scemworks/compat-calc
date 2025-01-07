from flask import Flask, request, render_template, redirect, url_for, session, send_from_directory
from hashlib import md5
import psycopg2
import psycopg2.extras
import secrets

# Initialize Flask app and secret key
app = Flask(__name__, static_folder='templates/static')
app.secret_key = secrets.token_hex(16)  # Generates a random secret key for security

# PostgreSQL connection URL
DATABASE_URL = "postgresql://neondb_owner:QvSk0z8duBXm@ep-gentle-lab-a1be155t-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Initialize Database
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS entries (
        id SERIAL PRIMARY KEY, 
        your_name TEXT NOT NULL, 
        crush_name TEXT NOT NULL, 
        score TEXT NOT NULL
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
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute("SELECT score FROM entries WHERE LOWER(your_name) = LOWER(%s) AND LOWER(crush_name) = LOWER(%s)", 
              (your_name, crush_name))
    result = c.fetchone()

    if result:
        # If entry exists, fetch the compatibility score
        compatibility = int(result['score'])
    else:
        # If entry doesn't exist, calculate compatibility score
        combined = f"{your_name.lower()}-{crush_name.lower()}"
        score = md5(combined.encode()).hexdigest()[:4]
        compatibility = int(score, 16) % 100

        # Insert the new entry into the database
        c.execute("INSERT INTO entries (your_name, crush_name, score) VALUES (%s, %s, %s)",
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
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    c.execute("SELECT * FROM entries")
    entries = c.fetchall()
    conn.close()
    
    return render_template('dashboard.html', entries=entries)

@app.route('/dashboard/edit', methods=['GET', 'POST'])
def edit_entry():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        entry_id = request.form['id']
        your_name = request.form['yourName'].strip()
        crush_name = request.form['crushName'].strip()
        score = request.form['score'].strip()

        # Update entry in the database
        c.execute("UPDATE entries SET your_name = %s, crush_name = %s, score = %s WHERE id = %s", 
                  (your_name, crush_name, score, entry_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))

    # Fetch the specific entry to edit
    entry_id = request.args.get('id')
    c.execute("SELECT * FROM entries WHERE id = %s", (entry_id,))
    entry = c.fetchone()
    conn.close()
    
    if entry:
        return render_template('edit.html', entry=entry)
    else:
        return "Entry not found", 404

@app.route('/dashboard/delete', methods=['POST'])
def delete_entry():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    entry_id = request.form['id']  # Get the ID of the entry to delete

    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    # Log out the admin and clear session
    session.pop('admin', None)
    return redirect(url_for('home'))