from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    #--------Users Table --------#
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
            )
    ''')
                   
    #--------Items Table --------#
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            photo TEXT,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
            )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

#--------Home Page --------#
@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                flash("Username and password required.", "error")
                return redirect(url_for('index'))
            
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                                (username, password)).fetchone()
            conn.close()

            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f"Welcome, {username}!", "success")
                return redirect(url_for('index'))
            else:
                flash("Invalid username or password.", "error")
                return redirect(url_for('index'))

        elif action == 'register':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            if not username or not email or not password:
                flash("All fields are required.", "error")
                return redirect(url_for('index'))
            
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                             (username, email, password))
                conn.commit()
                flash("Registration successful! Please login.", "success")
            except sqlite3.IntegrityError:
                flash("Username already exists.", "error")
            finally:
                conn.close()
            return redirect(url_for('index'))

    return render_template('index.html')

#--------Logout --------#
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

#--------Report Lost Item --------#
@app.route('/report_lost', methods=['GET', 'POST'])
def report_lost():

    if 'user_id' not in session:
        flash("You must log in first to report a lost item.", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('item_name')
        description = request.form.get('description')

        if not name or not description:
            flash("name and description are required.", "error")
            return redirect(url_for('report_lost'))
        photo_file = request.files.get('photo')
        filename = None

        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = get_db_connection()
        conn.execute("INSERT INTO items (user_id, name, description, photo, status) VALUES (?, ?, ?, ?, ?)",
                     (session['user_id'], name, description, filename, 'lost'))
        conn.commit()
        conn.close()
        flash("Lost item reported successfully!", "success")
        return redirect(url_for('my_items'))
    
    return render_template('report_lost.html')


#--------Report Found Item --------#
@app.route('/report_found', methods=['GET', 'POST'])
def report_found():

    if 'user_id' not in session:
        flash("You must log in first to report a found item.", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('item_name')
        description = request.form.get('description')

        if not name or not description:
            flash("name and description are required.", "error")
            return redirect(url_for('report_found'))
        photo_file = request.files.get('photo')
        filename = None

        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = get_db_connection()
        conn.execute("INSERT INTO items (user_id, name, description, photo, status) VALUES (?, ?, ?, ?, ?)",
                     (session['user_id'], name, description, filename, 'found'))
        conn.commit()
        conn.close()
        flash("Found item reported successfully!", "success")
        return redirect(url_for('my_items'))
    
    return render_template('report_found.html')

#--------My Items --------#
@app.route('/my_items', methods=['GET', 'POST'])
def my_items():

    if 'user_id' not in session:
        flash("You must log in first to view your items.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()

    #-------Edit Item --------#
    if request.method == 'POST' and 'item_id' in request.form:
        item_id = request.form.get('item_id')
        name = request.form.get('item_name')
        description = request.form.get('description')
        status = request.form.get('status')
        photo_file = request.files.get('photo')

        if not name or not description or status not in ['lost','found']:
            flash("All fields required and status must be lost/found.", "error")
            return redirect(url_for('my_items'))

        item = conn.execute("SELECT * FROM items WHERE id=? AND user_id=?",
                            (item_id, session['user_id'])).fetchone()
        if not item:
            flash("Item not found.", "error")
            return redirect(url_for('my_items'))

        filename = item['photo']
        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn.execute("UPDATE items SET name=?, description=?, photo=?, status=? WHERE id=?",
                     (name, description, filename, status, item_id))
        conn.commit()
        flash("Item updated successfully!", "success")
        return redirect(url_for('my_items'))

    items = conn.execute("SELECT * FROM items WHERE user_id=?", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_items.html', items=items)

#--------Delete Item --------#
@app.route('/delete_item_inline/<int:item_id>', methods=['POST'])
def delete_item_inline(item_id):

    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM items WHERE id=? AND user_id=?", (item_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Item deleted successfully!", "success")
    return redirect(url_for('my_items'))

#--------Search Items --------#
@app.route('/search', methods=['GET'])
def search():

    query = request.args.get('query')
    results = []

    if query:
        conn = get_db_connection()
        results = conn.execute("SELECT * FROM items WHERE name LIKE ? OR description LIKE ?",
                               (f'%{query}%', f'%{query}%')).fetchall()
        conn.close()
    return render_template('search.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)    

