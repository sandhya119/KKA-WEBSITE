import os
import sqlite3
from flask import send_file
import pandas as pd
import re
from datetime import datetime,timedelta
from collections import defaultdict
from PIL import Image
from fpdf import FPDF
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime, timedelta

app = Flask(__name__, template_folder="templates", static_folder="static")

load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

DB_PATH = "database.db"

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS family_details (
        family_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        nearest_city TEXT,
        details TEXT,
        num_children INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS interests (
        interest_id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        interest TEXT NOT NULL,
        FOREIGN KEY (family_id) REFERENCES family_details(family_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        file_path TEXT NOT NULL,
        category TEXT CHECK(category IN ('upcoming', 'past')) NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS event_registrations (
        registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        num_people INTEGER NOT NULL,
        adults INTEGER NOT NULL,
        children INTEGER NOT NULL,
        FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
    );
                         
    CREATE TABLE IF NOT EXISTS extra_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        file_path TEXT NOT NULL,
        FOREIGN KEY (event_id) REFERENCES gallery(id) ON DELETE CASCADE
        );                 
                   

    ''')
def update_db_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.executescript('''
    ALTER TABLE events ADD COLUMN date TEXT;
    ALTER TABLE events ADD COLUMN time TEXT;
    ALTER TABLE events ADD COLUMN publish_date_from TEXT;
    ALTER TABLE events ADD COLUMN publish_date_to TEXT;
    ALTER TABLE events ADD COLUMN cutoff_date TEXT;
    ALTER TABLE events ADD COLUMN guest_limit INTEGER;
    ''')
        # Check and add missing columns one by one
# Drop publish_date_to column if it exists
    try:
        cursor.execute("ALTER TABLE events DROP COLUMN publish_date_to;")
    except sqlite3.OperationalError:
        print("Column 'publish_date_to' does not exist or cannot be dropped.")

    # Ensure all required columns exist
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN date TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE events ADD COLUMN time TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE events ADD COLUMN publish_date_from TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE events ADD COLUMN cutoff_date TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE events ADD COLUMN guest_limit INTEGER;")
    except sqlite3.OperationalError:
        pass
     # Ensure 'event_datetime' column exists
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN event_datetime TEXT;")
    except sqlite3.OperationalError:
        print("Column 'event_datetime' already exists.")

    conn.commit()
    conn.close()

# Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect('events.db')
cursor = conn.cursor()

# Create the events table if it does not exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('upcoming', 'past')),
        date TEXT,
        time TEXT,
        publish_date_from TEXT,
        cutoff_date TEXT,
        guest_limit INTEGER,
        file_path TEXT,
        extra_images TEXT
    )
''')

conn.commit()
conn.close()

print("✅ Table 'events' created successfully!")

def check_event_availability(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT guest_limit, cutoff_date FROM events WHERE event_id = ?", (event_id,))
    event = cursor.fetchone()
    
    if not event:
        return False, "Event not found."
    
    guest_limit, cutoff_date = event
    
    cursor.execute("SELECT COUNT(*) FROM event_registrations WHERE event_id = ?", (event_id,))
    current_count = cursor.fetchone()[0]
    
    conn.close()
    
    if guest_limit and current_count >= guest_limit:
        return False, "Registration is closed as the guest limit has been reached."
    
    if cutoff_date and datetime.strptime(cutoff_date, "%Y-%m-%d") < datetime.today():
        return False, "Registration is closed as the cutoff date has passed."
    
    return True, "Registration open."
def register_for_event(event_id, name, email, phone, num_people):
    available, message = check_event_availability(event_id)
    if not available:
        return {"success": False, "message": message}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO event_registrations (event_id, name, email, phone, num_people)
        VALUES (?, ?, ?, ?, ?)
    """, (event_id, name, email, phone, num_people))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Registration successful!"}

# Insert admin user if not exists (Move this OUTSIDE the function)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT * FROM admins WHERE email = ?", ("info@karavalkonkans.org.au",))
if not cursor.fetchone():
    hashed_password = generate_password_hash("karavalkonkans@2025", method="pbkdf2:sha256")
    cursor.execute("INSERT INTO admins (email, password) VALUES (?, ?)", ("info@karavalkonkans.org.au", hashed_password))
conn.commit()

# Fetch all images from the database and resize them (Move this OUTSIDE the function)
cursor.execute("SELECT file_path FROM gallery")
images = cursor.fetchall()
for img_path in images:
    full_path = os.path.join(UPLOAD_FOLDER, img_path[0])  # Get full path
    if os.path.exists(full_path):
        img = Image.open(full_path)
        img = img.resize((500, 500))  # Resize to 500x500px
        img.save(full_path)
        print("✅ All images resized successfully!")

conn.close()

init_db()

# Function to add a new user to the database
def add_user(name, email, password, phone, city, details, num_children, interests):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Hash password before storing
    hashed_password = generate_password_hash(password)

    # Insert user details
    cursor.execute('''
        INSERT INTO users (name, email, password, phone) 
        VALUES (?, ?, ?, ?)
    ''', (name, email, hashed_password, phone))
    
    user_id = cursor.lastrowid  # Get the user ID of the newly inserted user

    # Insert family details
    cursor.execute('''
        INSERT INTO family_details (user_id, nearest_city, details, num_children) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, city, details, int(num_children or 0)))  # Ensure num_children is an integer

    family_id = cursor.lastrowid  # Get family ID

    # Insert interests
    if interests:
        for interest in interests.split(","):  # Assuming interests are comma-separated
            cursor.execute('''
                INSERT INTO interests (family_id, interest) 
                VALUES (?, ?)
            ''', (family_id, interest.strip()))

    conn.commit()
    conn.close()
def get_event_from_db(event_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access
    cursor = conn.cursor()

    cursor.execute("""
        SELECT event_id, title, description, file_path, category, date, time, 
               publish_date_from, cutoff_date, guest_limit,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
        FROM events e
        WHERE event_id = ?;
    """, (event_id,))

    event = cursor.fetchone()
    conn.close()

    if not event:
        return None  # No event found

    # Convert cutoff_date to a datetime object
    cutoff_date = event["cutoff_date"]
    today = datetime.today().strftime('%Y-%m-%d')

    show_register_button = True  # Default: Allow registration

    if cutoff_date and cutoff_date < today:
        show_register_button = False  # ❌ Hide register button

    return {
        "event_id": event["event_id"],
        "title": event["title"],
        "description": event["description"],
        "file_path": event["file_path"],
        "category": event["category"],
        "date": event["date"],
        "time": event["time"],
        "cutoff_date": event["cutoff_date"],
        "show_register_button": show_register_button  # ✅ Pass correct value
    }


# def get_upcoming_events(show_all=False):  # Add a parameter to control visibility
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()

#     today_date = datetime.today().strftime('%Y-%m-%d')

#     # Show all events for the admin panel
#     if show_all:
#         cursor.execute("""
#             SELECT event_id, title, description, file_path, category, date, time, 
#                    COALESCE(publish_date_from, 'Not Provided') AS publish_date_from,
#                    COALESCE(cutoff_date, 'Not Provided') AS cutoff_date,
#                    COALESCE(guest_limit, 'Not Provided') AS guest_limit
#             FROM events 
#             WHERE category = 'upcoming' 
#             ORDER BY date ASC;
#         """)
#     else:
#         # Only show events that are published (for regular users)
#         cursor.execute("""
#             SELECT event_id, title, description, file_path, category, date, time, 
#                    COALESCE(publish_date_from, 'Not Provided') AS publish_date_from,
#                    COALESCE(cutoff_date, 'Not Provided') AS cutoff_date,
#                    COALESCE(guest_limit, 'Not Provided') AS guest_limit
#             FROM events 
#             WHERE category = 'upcoming' 
#             AND (publish_date_from IS NULL OR publish_date_from <= ?) 
#             ORDER BY date ASC;
#         """, (today_date,))

#     events = cursor.fetchall()
#     conn.close()

#     formatted_events = [
#         {
#             "event_id": event["event_id"],
#             "title": event["title"],
#             "description": event["description"],
#             "file_path": event["file_path"],
#             "category": event["category"],
#             "date": event["date"],
#             "time": event["time"],
#             "publish_date_from": event["publish_date_from"],
#             "cutoff_date": event["cutoff_date"],
#             "guest_limit": event["guest_limit"],
#         }
#         for event in events
#     ]

#     return formatted_events
def get_upcoming_events(show_all=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today = datetime.today().strftime('%Y-%m-%d')

    if show_all:
        query = """
        SELECT event_id, title, description, file_path, category, date, time, 
               publish_date_from, cutoff_date, guest_limit,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
        FROM events e
        WHERE category = 'upcoming'
        ORDER BY date ASC;
        """
        cursor.execute(query)
    else:
        query = """
        SELECT event_id, title, description, file_path, category, date, time, 
               publish_date_from, cutoff_date, guest_limit,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
        FROM events e
        WHERE category = 'upcoming'
        AND (publish_date_from IS NOT NULL AND publish_date_from <= ?)  
        AND (date IS NOT NULL AND date >= ?)  -- ✅ Keep event until event date
        ORDER BY date ASC;
        """
        cursor.execute(query, (today, today))

    events = cursor.fetchall()
    conn.close()

    formatted_events = []
    for event in events:
        cutoff_date = event["cutoff_date"]
        guest_limit = event["guest_limit"]
        registered_count = event["registered_count"]
        event_date = event["date"]

        status = ""
        show_register_button = True  # ✅ Default: Show register button

        # ✅ Hide register button if cutoff date has passed
        if cutoff_date and cutoff_date != "Not Provided":
            cutoff_date_dt = datetime.strptime(cutoff_date, "%Y-%m-%d")
            if today > cutoff_date:
                status = "⚠️ Registration Closed"
                show_register_button = False  # ✅ Hide button

        # ✅ Guest limit reached status
        if guest_limit and guest_limit != "Not Provided" and registered_count >= int(guest_limit):
            status = "⚠️ Guest Limit Reached"
            show_register_button = False  # ✅ Hide button if full

        formatted_events.append({
            "event_id": event["event_id"],
            "title": event["title"],
            "description": event["description"],
            "file_path": event["file_path"],
            "category": event["category"],
            "date": event["date"],
            "time": event["time"],
            "publish_date_from": event["publish_date_from"],
            "cutoff_date": event["cutoff_date"],
            "guest_limit": event["guest_limit"],
            "status": status,
            "show_register_button": show_register_button  # ✅ Pass this to the template
        })

    return formatted_events

def connect_db():
    """Establish a database connection and return the connection object."""
    return sqlite3.connect('events.db')

@app.route('/upload_past_content', methods=['POST'])
def upload_past_content():
    title = request.form['title']
    description = request.form['description']
    category = "past"

    files = request.files.getlist('extra_images')

    image_paths = []
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_paths.append(f"uploads/{filename}")  # ✅ Correct relative path

    image_paths_str = ",".join(image_paths)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (title, description, category, file_path, extra_images) VALUES (?, ?, ?, ?, ?)",
        (title, description, category, image_paths[0] if image_paths else "", image_paths_str)
    )
    conn.commit()
    conn.close()

    flash("Past event uploaded successfully!", "success")
    return redirect(url_for('admin_panel'))




# def get_upcoming_events(show_all=False):
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()

#     today = datetime.today().strftime('%Y-%m-%d')

#     if show_all:
#         query = """
#         SELECT event_id, title, description, file_path, category, date, time, 
#                publish_date_from,  -- Removed COALESCE() for debugging
#                cutoff_date,
#                guest_limit,
#                (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
#         FROM events e
#         WHERE category = 'upcoming'
#         ORDER BY date ASC;
#         """
#         cursor.execute(query)
#     else:
#         query = """
#         SELECT event_id, title, description, file_path, category, date, time, 
#                publish_date_from,
#                cutoff_date,
#                guest_limit,
#                (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
#         FROM events e
#         WHERE category = 'upcoming'
#         AND (publish_date_from IS NOT NULL AND publish_date_from <= ?)  
#         AND date >= ?
#         ORDER BY date ASC;
#         """
#         cursor.execute(query, (today, today))

#     events = cursor.fetchall()
#     conn.close()

#     formatted_events = []
#     for event in events:
#         print(f"DEBUG: Event ID {event['event_id']} - Publish Date: {event['publish_date_from']}")  # Debugging output

#         formatted_events.append({
#             "event_id": event["event_id"],
#             "title": event["title"],
#             "description": event["description"],
#             "file_path": event["file_path"],
#             "category": event["category"],
#             "date": event["date"],
#             "time": event["time"],
#             "publish_date_from": event["publish_date_from"],  # Ensure it's included
#             "cutoff_date": event["cutoff_date"],
#             "guest_limit": event["guest_limit"],
#         })

#     return formatted_events



# def get_upcoming_events(show_all=False):
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()

#     today = datetime.today().strftime('%Y-%m-%d')
#     three_days_after = (datetime.today() + timedelta(days=3)).strftime('%Y-%m-%d')

#     if show_all:
#         query = """
#             SELECT event_id, title, description, file_path, category, date, time, 
#                    COALESCE(publish_date_from, 'Not Provided') AS publish_date_from,
#                    COALESCE(cutoff_date, 'Not Provided') AS cutoff_date,
#                    COALESCE(guest_limit, 'Not Provided') AS guest_limit,
#                    (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
#             FROM events e
#             WHERE category = 'upcoming'
#             ORDER BY date ASC;
#         """
#         cursor.execute(query)
#     else:
#         query = """
#             SELECT event_id, title, description, file_path, category, date, time, 
#                    COALESCE(publish_date_from, 'Not Provided') AS publish_date_from,
#                    COALESCE(cutoff_date, 'Not Provided') AS cutoff_date,
#                    COALESCE(guest_limit, 'Not Provided') AS guest_limit,
#                    (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.event_id) AS registered_count
#             FROM events e
#             WHERE category = 'upcoming'
#             AND (publish_date_from IS NULL OR publish_date_from <= ?)
#             ORDER BY date ASC;
#         """
#         cursor.execute(query, (today,))

#     events = cursor.fetchall()
#     conn.close()

#     formatted_events = []
#     for event in events:
#         cutoff_date = event["cutoff_date"]
#         guest_limit = event["guest_limit"]
#         registered_count = event["registered_count"]

#         status = ""

#         # Check if deadline is over
#         if cutoff_date and cutoff_date != "Not Provided":
#             if today <= cutoff_date <= three_days_after:
#                 status = "⚠️ Deadline Over"

#         # Check if guest limit is reached
#         if guest_limit and guest_limit != "Not Provided":
#             if registered_count >= int(guest_limit):
#                 status = "⚠️ Guest Limit Reached"

#         formatted_events.append({
#             "event_id": event["event_id"],
#             "title": event["title"],
#             "description": event["description"],
#             "file_path": event["file_path"],
#             "category": event["category"],
#             "date": event["date"],
#             "time": event["time"],
#             "publish_date_from": event["publish_date_from"],
#             "cutoff_date": event["cutoff_date"],
#             "guest_limit": event["guest_limit"],
#             "status": status  # ✅ Store status in the event data
#         })

#     return formatted_events


@app.route('/delete-expired-events', methods=['POST'])
def delete_expired_events():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.today().date()
    three_days_ago = today - timedelta(days=3)

    cursor.execute("""
        DELETE FROM events WHERE cutoff_date <= ?;
    """, (three_days_ago,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Expired events deleted successfully!"})



@app.route('/get-event/<int:event_id>', methods=['GET'])
def get_event(event_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT event_id, title, description, date, time, publish_date_from, cutoff_date 
        FROM events WHERE event_id = ?
    """, (event_id,))
    
    event = cursor.fetchone()
    conn.close()

    if event:
        event_data = {
            "event_id": event["event_id"],
            "title": event["title"],
            "description": event["description"],
            "date": event["date"],
            "time": event["time"],
            "publish_date_from": event["publish_date_from"].strftime('%Y-%m-%d') if event["publish_date_from"] else None,
            "cutoff_date": event["cutoff_date"].strftime('%Y-%m-%d') if event["cutoff_date"] else None,
        }
        return jsonify(event_data)
    else:
        return jsonify({"error": "Event not found"}), 404


@app.route('/check-event-status/<int:event_id>', methods=['GET'])
def check_event_status(event_id):
    available, message = check_event_availability(event_id)
    return jsonify({"available": available, "message": message})


@app.route('/')
def home():
    return render_template('index.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            stored_hashed_password = user[1]  # Retrieve hashed password
            if check_password_hash(stored_hashed_password, password):
                session['user_id'] = user[0]  # Store user ID in session
                flash("Login successful!", "success")
                return redirect(url_for('home'))  # Redirect to home page
            else:
                flash("Incorrect email or password!", "danger")
        else:
            flash("Incorrect email or password!", "danger")

    return render_template('login.html')



# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        city = request.form['city']
        details = request.form.get('family_details', '')
        num_children = request.form.get('children_count', 0)
        interests = request.form.get('interests', '')

        # Check if the email already exists
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        conn.close()

        if existing_user:
            flash("Email already exists! Please use a different email.", "danger")
            return redirect(url_for('register'))  # Redirect back to registration page

        # Add user to the database
        add_user(name, email, password, phone, city, details, num_children, interests)

        flash("Registration successful!", "success")
        return redirect(url_for('home'))  # Redirect to home after successful registration

    return render_template('JoinFamReg.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot-password.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for('home'))

# @app.route('/upload_event', methods=['POST'])
# def upload_event():
#     title = request.form.get('title', '')
#     description = request.form.get('description', '')
#     category = request.form.get('category', '')
#     date = request.form.get('date', '')
#     time = request.form.get('time', '')
#     publish_date_from = request.form.get('publish_date_from', None)  # Allow NULL
#     cutoff_date = request.form.get('cutoff_date', None)
#     guest_limit = request.form.get('guest_limit', 0)
#     main_image = request.files.get('main_image')

#     if not title or not category or not main_image:
#         flash("Please fill in all required fields!", "danger")
#         return redirect(url_for('admin_panel'))

#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     main_filename = secure_filename(main_image.filename)
#     main_filepath = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
#     main_image.save(main_filepath)

#     # ✅ Insert event with `publish_date_from` (Ensure NULL is handled correctly)
#     cursor.execute("""
#         INSERT INTO events (title, description, category, date, time, publish_date_from, cutoff_date, 
#         guest_limit, file_path) 
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#     """, (title, description, category, date, time, publish_date_from, cutoff_date, guest_limit, f"uploads/{main_filename}"))

#     conn.commit()
#     conn.close()

#     flash("Event uploaded successfully!", "success")
#     return redirect(url_for('admin_panel'))
@app.route('/upload_event', methods=['POST'])
def upload_event():
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    category = request.form.get('category', '')
    event_date = request.form.get('date', '')
    event_time = request.form.get('time', '')
    publish_date_from = request.form.get('publish_date_from', None)
    cutoff_date = request.form.get('cutoff_date', None)
    guest_limit = request.form.get('guest_limit', 0)
    main_image = request.files.get('main_image')

    if not title or not category or not main_image:
        flash("Please fill in all required fields!", "danger")
        return redirect(url_for('admin_panel'))

    # Save the main image
    main_filename = secure_filename(main_image.filename)
    main_filepath = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
    main_image.save(main_filepath)

    # Insert event details into database (without event_datetime)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (title, description, category, date, time, publish_date_from, cutoff_date, guest_limit, file_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, category, event_date, event_time, publish_date_from, cutoff_date, guest_limit, f"uploads/{main_filename}"))

    conn.commit()
    conn.close()

    flash("Event uploaded successfully!", "success")
    return redirect(url_for('admin_panel'))

# @app.route('/upload_event', methods=['POST'])
# def upload_event():
#     title = request.form.get('title', '')
#     description = request.form.get('description', '')
#     category = request.form.get('category', '')
#     event_date = request.form.get('date', '')
#     event_time = request.form.get('time', '')
#     publish_date_from = request.form.get('publish_date_from', None)  # Allow NULL
#     cutoff_date = request.form.get('cutoff_date', None)
#     guest_limit = request.form.get('guest_limit', 0)
#     main_image = request.files.get('main_image')

#     if not title or not category or not main_image:
#         flash("Please fill in all required fields!", "danger")
#         return redirect(url_for('admin_panel'))

#     # Combine the event date and time into a datetime object if needed for sorting or manipulation
#     event_datetime = f"{event_date} {event_time}"
#     event_datetime_obj = datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')

#     # Save the main image to the filesystem
#     main_filename = secure_filename(main_image.filename)
#     main_filepath = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
#     main_image.save(main_filepath)

#     # Save the event details into the database
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     cursor.execute("""
#         INSERT INTO events (title, description, category, date, time, publish_date_from, cutoff_date, 
#         guest_limit, file_path, event_datetime)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#     """, (title, description, category, event_date, event_time, publish_date_from, cutoff_date, guest_limit, 
#           f"uploads/{main_filename}", event_datetime_obj))

#     conn.commit()
#     conn.close()

#     flash("Event uploaded successfully!", "success")
#     return redirect(url_for('admin_panel'))


# @app.route('/upcoming-events')
# def upcoming_events():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("SELECT event_id, title, description, file_path ,category, uploaded_at FROM events")
#     events = cursor.fetchall()
#     conn.close()
#     return render_template('upevents.html', events=events)
@app.route('/upcoming-events')
def upcoming_events():
    events = get_upcoming_events()
    return render_template('upevents.html', events=events)

@app.route('/past-events')
def past_events():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT title, description, file_path, extra_images FROM events WHERE category='past' ORDER BY uploaded_at DESC")
    events = cursor.fetchall()

    past_events_data = []
    for event in events:
        images = event["extra_images"].split(",") if event["extra_images"] else []
        
        # ✅ Remove duplicates by converting list to a set and back to a list
        unique_images = list(set(images))

        # ✅ Also remove the main image from extra images to prevent duplication
        if event["file_path"] in unique_images:
            unique_images.remove(event["file_path"])
        
        past_events_data.append({
            "title": event["title"],
            "description": event["description"],
            "main_image": event["file_path"],
            "extra_images": unique_images  # ✅ Only unique extra images
        })

    conn.close()
    return render_template('Past_Events.html', events=past_events_data)

@app.route('/EventReg/<int:event_id>', methods=['GET', 'POST'])  #  Ensure both GET & POST are allowed
def event_register(event_id):
    if 'user_id' not in session:
        flash("Please log in to register for an event!", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch user details from the session user_id
    cursor.execute("SELECT name, email, phone FROM users WHERE user_id = ?", (session['user_id'],))
    user = cursor.fetchone()

    # Fetch event title from the database
    cursor.execute("SELECT title FROM events WHERE event_id = ?", (event_id,))
    event = cursor.fetchone()

    conn.close()

    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for('home'))

    event_title = event[0]  # Extract event title

    if request.method == 'POST':  #  Ensure POST request is handled
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        num_people = request.form['people']
        num_adults = request.form['adults']
        num_children = request.form['children']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT name, email, phone FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({"success": False, "message": "You must be a registered user to sign up for events."}), 400

        db_name, db_email, db_phone = user
        if db_name != name or db_email != email or db_phone != phone:
            conn.close()
            return jsonify({"success": False, "message": "Entered details do not match our records."}), 400
        
                # Check if user has already registered for this event
        cursor.execute("SELECT COUNT(*) FROM event_registrations WHERE email = ? AND event_id = ?", (email, event_id))
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            conn.close()
            return jsonify({"success": False, "message": "You have already registered for this event."}), 400

        # Save registration
        try:
            query = """
            INSERT INTO event_registrations (event_id, name, email, phone, num_people, adults, children)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (event_id, name, email, phone, num_people, num_adults, num_children))
            conn.commit()
            conn.close()

            return jsonify({"success": True, "message": "Registration successful!"}), 200  #  Return JSON response

        except Exception as e:
            conn.close()
            return jsonify({"success": False, "message": "Registration failed. Please try again later."}), 500

    #  Ensure GET requests return the registration form
    return render_template('EventReg.html', event_id=event_id, event_title=event_title)





@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Restrict access to only the predefined admin email
        if email != "info@karavalkonkans.org.au":
            flash("Access denied!", "danger")
            return redirect(url_for('admin_login'))

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT admin_id, password FROM admins WHERE email = ?", (email,))
            admin = cursor.fetchone()

        if admin and check_password_hash(admin[1], password):
            session['admin_id'] = admin[0]
            flash("Admin login successful!", "success")
            return redirect(url_for('admin_panel'))
        else:
            flash("Incorrect admin email or password!", "danger")

    return render_template('admin-login.html')




@app.route('/admin', methods=["GET", "POST"])
def admin_panel():
    # Ensure the admin is logged in
    if 'admin_id' not in session:
        flash("Please log in as an admin to access this page.", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column name access
    cursor = conn.cursor()

    # Handle POST request (for news uploads)
    if request.method == "POST":
        # Detect news upload form by checking for the "content" field.
        if "content" in request.form:
            title = request.form["title"]
            description = request.form["description"]
            content = request.form["content"]
            images = request.files.getlist("images")

            # Insert the news article into the news table
            cursor.execute("INSERT INTO news (title, description, content) VALUES (?, ?, ?)",
                           (title, description, content))
            news_id = cursor.lastrowid

            # Save each uploaded image
            for image in images:
                if image and image.filename:
                    filename = f"{news_id}_{secure_filename(image.filename)}"
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    image.save(filepath)
                    cursor.execute("INSERT INTO news_images (news_id, image_filename) VALUES (?, ?)",
                                   (news_id, filename))
            conn.commit()
            flash("News uploaded successfully!", "success")
            return redirect(url_for('admin_panel'))

    # --- Fetch all necessary data for the admin dashboard ---

    # User registrations (with family details)
    cursor.execute("""
    SELECT u.user_id, u.name, u.email, u.phone, 
           COALESCE(f.nearest_city, 'N/A') AS nearest_city, 
           COALESCE(f.details, 'N/A') AS details, 
           COALESCE(f.num_children, 0) AS num_children
    FROM users u
    LEFT JOIN family_details f ON u.user_id = f.user_id;
""")
    registrations = [dict(row) for row in cursor.fetchall()]

     # Fetch upcoming events
    upcoming_events = get_upcoming_events(show_all=True)

    cursor.execute("""
    SELECT event_id, title, description, file_path, date, time 
    FROM events 
    WHERE category='upcoming' 
    ORDER BY uploaded_at DESC;
""")
    # upcoming_events = [dict(row) for row in cursor.fetchall()]

    # Fetch past events properly
    cursor.execute("SELECT * FROM events WHERE category = 'past' ORDER BY uploaded_at DESC")
    past_events = cursor.fetchall()
    # Event registrations with event details
    cursor.execute('''
        SELECT er.registration_id, er.event_id, e.title, er.name, er.email, er.phone, er.num_people
        FROM event_registrations er
        JOIN events e ON er.event_id = e.event_id
        ORDER BY er.registration_id DESC;
    ''')
    event_registrations = [dict(row) for row in cursor.fetchall()]

    # Total registered users and event registrations
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(num_people), 0) FROM event_registrations")
    total_event_registrations = cursor.fetchone()[0]

    cursor.execute("""
    SELECT e.title, COALESCE(SUM(er.num_people), 0) AS count
    FROM event_registrations er
    JOIN events e ON er.event_id = e.event_id
    GROUP BY e.title;
""")
    event_chart_data = [dict(row) for row in cursor.fetchall()]

    # Event registrations by city
    cursor.execute('''
        SELECT COALESCE(f.nearest_city, 'None') AS city, COALESCE(SUM(er.num_people), 0) AS count
        FROM event_registrations er
        JOIN users u ON er.email = u.email
        LEFT JOIN family_details f ON u.user_id = f.user_id
        GROUP BY f.nearest_city;
    ''')
    event_city_chart_data = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
    SELECT g.id, g.title, g.description, g.file_path, 
           GROUP_CONCAT(e.file_path) AS extra_images
    FROM gallery g
    LEFT JOIN extra_images e ON g.id = e.event_id
    GROUP BY g.id
    ORDER BY g.uploaded_at DESC;
""")
    gallery_images = [dict(row) for row in cursor.fetchall()]

    # News articles with concatenated image filenames (if any)
    cursor.execute("""
        SELECT n.id, n.title, n.description, 
               COALESCE(GROUP_CONCAT(i.image_filename), '') AS images
        FROM news n
        LEFT JOIN news_images i ON n.id = i.news_id
        GROUP BY n.id ORDER BY n.id DESC;
    """)
    raw_news = cursor.fetchall()
    news_articles = []
    for news in raw_news:
        news_articles.append({
            "id": news["id"],
            "title": news["title"],
            "description": news["description"],
            "images": news["images"].split(",") if news["images"] else []
        })

    conn.close()

    return render_template("admin.html",
                           registrations=registrations,
                           upcoming_events=upcoming_events,
                           past_events=past_events,
                           event_registrations=event_registrations,
                           total_users=total_users,
                           total_event_registrations=total_event_registrations,
                           event_chart_data=event_chart_data,
                           event_city_chart_data=event_city_chart_data,
                           gallery_images=gallery_images,
                           news_articles=news_articles,
                           current_date=datetime.today().date())


@app.route('/update-event', methods=['POST'])
def update_event():
    data = request.json
    event_id = data.get("event_id")
    title = data.get("title")
    description = data.get("description")
    publish_date_from = data.get("publish_date_from") or None
    cutoff_date = data.get("cutoff_date") or None
    guest_limit = data.get("guest_limit") or None
    event_date = data.get("date") or None
    event_time = data.get("time") or None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE events 
        SET title = ?, description = ?, publish_date_from = ?, cutoff_date = ?, 
            guest_limit = ?, date = ?, time = ?
        WHERE event_id = ?
    """, (title, description, publish_date_from, cutoff_date, guest_limit, event_date, event_time, event_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Event updated successfully!"})

def check_event_dates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, title, publish_date_from, cutoff_date FROM events")
    rows = cursor.fetchall()
    conn.close()

    print("DEBUG: Checking Events in DB:")
    for row in rows:
        print(row)  # ✅ Print all rows to verify stored values

def admin_dashboard():
    upcoming_events = get_upcoming_events()
    return render_template('admin.html', upcoming_events=upcoming_events, current_date=datetime.today().date())


# Admin Logout Route
@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_id', None)
    flash("Admin logged out successfully!", "info")
    return redirect(url_for('admin_login'))

@app.route('/fetch-event-registrations')
def fetch_event_registrations():
    if 'admin_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch correct event registrations
    query = '''
    SELECT er.registration_id, er.event_id, er.name, er.email, er.phone, er.num_people, e.title
    FROM event_registrations er
    JOIN events e ON er.event_id = e.event_id
    '''
    
    cursor.execute(query)
    event_registrations = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "registration_id": reg[0],
            "event_id": reg[1],
            "name": reg[2],
            "email": reg[3],
            "phone": reg[4],
            "num_people": reg[5],
            "event_title": reg[6]
        } 
        for reg in event_registrations
    ])

# @app.route('/get-event-registrations')
# def get_event_registrations():
#     if 'admin_id' not in session:
#         return jsonify({"error": "Unauthorized"}), 403

#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     # Fetch all event registrations with event details
#     query = '''
#     SELECT er.registration_id, er.name, er.email, er.phone, er.num_people, er.adults, er.children, 
#            e.event_id, e.title
#     FROM event_registrations er
#     JOIN events e ON er.event_id = e.event_id
#     ORDER BY er.registration_id DESC
#     '''
    
#     cursor.execute(query)
#     event_registrations = cursor.fetchall()
    
#     conn.close()

#     # Convert list of tuples into JSON format
#     return jsonify([
#         {
#             "registration_id": reg[0],
#             "name": reg[1],
#             "email": reg[2],
#             "phone": reg[3],
#             "num_people": reg[4],
#             "adults": reg[5],
#             "children": reg[6],
#             "event_id": reg[7],
#             "event_title": reg[8]
#         } 
#         for reg in event_registrations
#     ])
@app.route('/get-all-event-registrations')
def get_all_event_registrations():
    if 'admin_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch registrations grouped by event
    query = '''
    SELECT e.event_id, e.title, er.name, er.email, er.phone, er.num_people, er.adults, er.children
    FROM event_registrations er
    JOIN events e ON er.event_id = e.event_id
    ORDER BY e.event_id
    '''
    
    cursor.execute(query)
    event_registrations = cursor.fetchall()
    conn.close()

    event_dict = {}
    for reg in event_registrations:
        event_id, title, name, email, phone, num_people, adults, children = reg
        if event_id not in event_dict:
            event_dict[event_id] = {"title": title, "registrations": []}
        event_dict[event_id]["registrations"].append({
            "name": name, "email": email, "phone": phone,
            "num_people": num_people, "adults": adults, "children": children
        })

    return jsonify(event_dict)

@app.route('/export-upcoming-event-registrations/<int:event_id>')
def export_upcoming_event_registrations(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch registrations including user_id
    cursor.execute('''
        SELECT e.title, u.user_id, er.name, er.email, er.phone, er.num_people, er.adults, er.children
        FROM event_registrations er
        JOIN events e ON er.event_id = e.event_id
        JOIN users u ON er.email = u.email
        WHERE e.event_id = ? AND e.category = 'upcoming'
    ''', (event_id,))
    
    registrations = cursor.fetchall()
    conn.close()

    if not registrations:
        return jsonify({"error": "No registrations found for this upcoming event"}), 404

    event_title = registrations[0][0].replace(" ", "_")  # Sanitize filename

    # Ensure directory exists
    reports_dir = "static/reports"
    os.makedirs(reports_dir, exist_ok=True)

    file_path = os.path.join(reports_dir, f"{event_title}_registrations.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, f"Upcoming Event: {event_title}", ln=True, align="C")
    pdf.ln(10)

    # pdf.set_font("Arial", size=12)
    # pdf.cell(30, 10, "User ID", border=1)
    # pdf.cell(40, 10, "Name", border=1)
    # pdf.cell(50, 10, "Email", border=1)
    # pdf.cell(30, 10, "Phone", border=1)
    # pdf.cell(20, 10, "People", border=1)
    # pdf.cell(20, 10, "Adults", border=1)
    # pdf.cell(20, 10, "Children", border=1)
    # pdf.ln()

    # pdf.set_font("Arial", size=10)
    # for row in registrations:
    #     formatted_user_id = f"KKA{row[1]}"  # Convert user ID to KKA format
    #     pdf.cell(30, 10, formatted_user_id, border=1)  # User ID
    #     pdf.cell(40, 10, row[2], border=1)  # Name
    #     pdf.cell(50, 10, row[3], border=1)  # Email
    #     pdf.cell(30, 10, row[4], border=1)  # Phone
    #     pdf.cell(20, 10, str(row[5]), border=1)  # People
    #     pdf.cell(20, 10, str(row[6]), border=1)  # Adults
    #     pdf.cell(20, 10, str(row[7]), border=1)  # Children
    #     pdf.ln()

    # pdf.output(file_path)

    # return send_file(file_path, as_attachment=True)
    pdf.set_font("Arial", size=12)

    # Adjust column widths to fit the page properly
    column_widths = [25, 35, 50, 35, 15, 15, 15]  # Adjusted sizes for uniform spacing

    headers = ["User ID", "Name", "Email", "Phone", "People", "Adults", "Children"]

    # Print headers
    for i in range(len(headers)):
        pdf.cell(column_widths[i], 10, headers[i], border=1, align="C")

    pdf.ln()

    pdf.set_font("Arial", size=10)
    for row in registrations:
        formatted_user_id = f"KKA{row[1]}"  # Convert user ID to KKA format
        data = [formatted_user_id, row[2], row[3], row[4], str(row[5]), str(row[6]), str(row[7])]
        
        for i in range(len(data)):
            pdf.cell(column_widths[i], 10, data[i], border=1, align="C")

        pdf.ln()

    pdf.output(file_path)

    return send_file(file_path, as_attachment=True)

@app.route('/check-event-category/<int:event_id>')
def check_event_category(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM events WHERE event_id = ?", (event_id,))
    event = cursor.fetchone()
    conn.close()
    return jsonify({"category": event[0] if event else "unknown"})

@app.route('/get-upcoming-event-registrations')
def get_upcoming_event_registrations():
    if 'admin_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch registrations grouped by event (only upcoming events), including user_id
    query = '''
    SELECT e.event_id, e.title, u.user_id, er.name, er.email, er.phone, er.num_people, er.adults, er.children
    FROM event_registrations er
    JOIN events e ON er.event_id = e.event_id
    JOIN users u ON er.email = u.email
    WHERE e.category = 'upcoming'
    ORDER BY e.event_id
    '''
    
    cursor.execute(query)
    event_registrations = cursor.fetchall()
    conn.close()

    event_dict = {}
    for reg in event_registrations:
        event_id, title, user_id, name, email, phone, num_people, adults, children = reg
        formatted_user_id = f"KKA{user_id}"  # Convert user ID to KKA format
        
        if event_id not in event_dict:
            event_dict[event_id] = {"title": title, "registrations": []}
        
        event_dict[event_id]["registrations"].append({
            "user_id": formatted_user_id,  # Add formatted User ID
            "name": name,
            "email": email,
            "phone": phone,
            "num_people": num_people,
            "adults": adults,
            "children": children
        })

    return jsonify(event_dict)


@app.route('/admin/data')
def get_admin_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    data = cursor.fetchall()
    conn.close()
    
    print("Admin data fetched:", data)  # Debugging
    return jsonify(data)

@app.route('/event_registrations')
def event_registrations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT registration_id, event_id, title, name, email, phone, num_people, adults, children
        FROM event_registrations
        JOIN events ON event_registrations.event_id = events.event_id
    ''')
    registrations = cursor.fetchall()
    conn.close()

    return render_template('event_registrations.html', registrations=registrations)

# Home Page
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')



# @app.route('/gallery')
# def gallery():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
    
#     # Fetch gallery images from the new gallery table
#     cursor.execute("SELECT id, title, description, file_path FROM gallery")
#     gallery_images = [dict(id=row[0], title=row[1], description=row[2], file_path=row[3]) for row in cursor.fetchall()]
    
#     conn.close()
#     return render_template('gallery.html', gallery_images=gallery_images)

# @app.route('/upload_gimages', methods=['POST'])
# def upload_gimages():
#     if request.method == 'POST':
#         title = request.form['title']
#         description = request.form['description']
#         image = request.files['image']

#         if image and title and description:
#             image_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
#             image.save(image_path)

#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             cursor.execute("INSERT INTO gallery (title, description, file_path) VALUES (?, ?, ?)", 
#                            (title, description, f"uploads/{image.filename}"))
#             conn.commit()
#             conn.close()

#     return redirect(url_for('gallery'))
@app.route("/gallery")
def gallery():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, file_path, 
               COALESCE(uploaded_at, datetime('now', 'localtime')) 
        FROM gallery ORDER BY uploaded_at DESC
    """)
    images = cursor.fetchall()
    
    gallery_by_date = {}
    for image in images:
        uploaded_at = image[4]
        date = uploaded_at.split(" ")[0]
        
        cursor.execute("SELECT file_path FROM extra_images WHERE event_id = ?", (image[0],))
        extra_images = [row[0] for row in cursor.fetchall()]
        
        if date not in gallery_by_date:
            gallery_by_date[date] = []
        
        gallery_by_date[date].append({
            "id": image[0],
            "title": image[1],
            "description": image[2],
            "file_path": image[3],
            "extra_images": extra_images
        })
    
    conn.close()
    return render_template("gallery.html", gallery_by_date=gallery_by_date)

@app.route("/upload_gimages", methods=["POST"])
def upload_gimages():
    title = request.form["title"]
    description = request.form["description"]
    # uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uploaded_at = request.form.get("uploaded_at") 
    main_image = request.files["main_image"]
    extra_images = request.files.getlist("extra_images")
    
    # If no date is provided, fallback to current timestamp
    if not uploaded_at or len(uploaded_at) < 10:
        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not main_image:
        return "Main image is required", 400
    
    filename = secure_filename(main_image.filename)
    main_image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    main_image.save(main_image_path)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO gallery (title, description, file_path, uploaded_at) 
        VALUES (?, ?, ?, ?)
    """, (title, description, f"uploads/{filename}", uploaded_at))
    event_id = cursor.lastrowid
    
    for image in extra_images[:20]:  # Limit to 20 images
        if image.filename:
            extra_filename = secure_filename(image.filename)
            extra_path = os.path.join(app.config["UPLOAD_FOLDER"], extra_filename)
            image.save(extra_path)
            cursor.execute("""
                INSERT INTO extra_images (event_id, file_path) VALUES (?, ?)
            """, (event_id, f"uploads/{extra_filename}"))
    
    conn.commit()
    conn.close()
    return redirect(url_for("gallery"))

@app.route("/gallery_details/<int:event_id>")
def gallery_details(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ✅ Fetch the latest title & description every time the page loads
    cursor.execute("SELECT id, title, description, file_path FROM gallery WHERE id = ?", (event_id,))
    event = cursor.fetchone()

    if not event:
        conn.close()
        return "Event not found", 404

    cursor.execute("SELECT file_path FROM extra_images WHERE event_id = ?", (event_id,))
    extra_images = [row[0] for row in cursor.fetchall()]
    
    conn.close()

    return render_template("gallery_details.html", event={
        "id": event[0],
        "title": event[1],
        "description": event[2],
        "file_path": event[3],
        "extra_images": extra_images
    })



# @app.route('/delete_image/<int:image_id>', methods=['POST'])
# def delete_image(image_id):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
    
#     # Get the file path before deleting
#     cursor.execute("SELECT file_path FROM gallery WHERE id = ?", (image_id,))
#     image_data = cursor.fetchone()
    
#     if image_data:
#         image_path = os.path.join("static", image_data[0])
#         if os.path.exists(image_path):
#             os.remove(image_path)

#         cursor.execute("DELETE FROM gallery WHERE id = ?", (image_id,))
#         conn.commit()
    
#     conn.close()
#     return redirect(url_for('gallery'))
@app.route('/delete-image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the file path before deleting
    cursor.execute("SELECT file_path FROM gallery WHERE id = ?", (image_id,))
    image_data = cursor.fetchone()
    
    if image_data:
        image_path = os.path.join(app.static_folder, image_data[0])
        if os.path.exists(image_path):
            os.remove(image_path)  # ✅ Delete the image file

        cursor.execute("DELETE FROM gallery WHERE id = ?", (image_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Image deleted successfully!"})
    
    conn.close()
    return jsonify({"success": False, "error": "Image not found!"})




uploads_folder = "static/uploads"
for file in os.listdir(uploads_folder):
    print(file)
# Connect to the database
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# News page (List all news)
@app.route("/")
@app.route("/news")
def news():
    conn = get_db_connection()
    
    # Fetch news with images
    news_articles = conn.execute("""
        SELECT n.id, n.title, n.description, GROUP_CONCAT(i.image_filename) AS images
        FROM news n
        LEFT JOIN news_images i ON n.id = i.news_id
        GROUP BY n.id ORDER BY n.id DESC
    """).fetchall()
    
    conn.close()

    # Convert images column to lists
    formatted_news = []
    for news in news_articles:
        formatted_news.append({
            "id": news["id"],
            "title": news["title"],
            "description": news["description"],
            "images": news["images"].split(",") if news["images"] else []
        })

    return render_template("news.html", news=formatted_news)


# Admin Panel (Upload News)
@app.route("/admin", methods=["GET", "POST"])
def upload_news():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        content = request.form["content"]
        images = request.files.getlist("images")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert news article into 'news' table
        cursor.execute("INSERT INTO news (title, description, content) VALUES (?, ?, ?)", 
                       (title, description, content))
        news_id = cursor.lastrowid  # Get the last inserted news ID

        # Save images & insert file paths
        for image in images:
            if image and image.filename:
                filename = f"{news_id}_{image.filename}"
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                image.save(filepath)

                # Insert image filename into 'news_images' table
                cursor.execute("INSERT INTO news_images (news_id, image_filename) VALUES (?, ?)", 
                               (news_id, filename))

        conn.commit()
        conn.close()

        # return redirect(url_for("upload_news"))  # Redirect back to admin panel
        return redirect(url_for("news"))
    
    
@app.route("/admin")
def admin_portal():
    conn = get_db_connection()
    news_articles = conn.execute("""
        SELECT n.id, n.title, n.description, 
               COALESCE(GROUP_CONCAT(i.image_filename), '') AS images
        FROM news n
        LEFT JOIN news_images i ON n.id = i.news_id
        GROUP BY n.id ORDER BY n.id DESC
    """).fetchall()
    conn.close()

    # Convert images column to lists
    formatted_news = []
    for news in news_articles:
        print(news)  # ✅ Debugging: Print each news entry
        formatted_news.append({
            "id": news["id"],
            "title": news["title"],
            "description": news["description"],
            "images": news["images"].split(",") if news["images"] else []  # Fix: Ensure images are a list
        })

    print("Formatted News:", formatted_news)  # ✅ Check output in console

    return render_template("admin.html", news_articles=formatted_news)  # Fix: Pass formatted_news instead




# News details page
@app.route("/news/<int:news_id>")
def news_details(news_id):
    conn = get_db_connection()
    news_item = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    images = conn.execute("SELECT image_filename FROM news_images WHERE news_id = ?", (news_id,)).fetchall()
    conn.close()

    return render_template("news_details.html", news=news_item, images=images)


# Delete News Article
@app.route("/delete-news/<int:news_id>", methods=["DELETE"])
def delete_news(news_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete the news entry
    cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "News deleted successfully!"})


@app.route('/contact')
def contact():
    return render_template('contact.html')

# @app.route('/delete-event', methods=['POST'])
# def delete_event():
#     try:
#         data = request.json
#         event_id = data.get('id')
#         if not event_id:
#             return jsonify({"success": False, "error": "No event ID provided."})

#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
#         conn.commit()
#         conn.close()

#         return jsonify({"success": True, "message": "Event deleted successfully!"})

#     except Exception as e:
#         print("Delete Event Error:", str(e))
#         return jsonify({"success": False, "error": str(e)})


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in to view your profile.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allow access as dictionary
    cursor = conn.cursor()

    # Fetch user details
    cursor.execute('''
         SELECT u.user_id, u.name, u.email, u.phone, 
               COALESCE(f.nearest_city, 'Not Provided') AS nearest_city, 
               COALESCE(f.details, 'No family details available') AS details, 
               COALESCE(f.num_children, 0) AS num_children, 
               COALESCE(GROUP_CONCAT(i.interest), '') AS interests
        FROM users u
        LEFT JOIN family_details f ON u.user_id = f.user_id
        LEFT JOIN interests i ON f.family_id = i.family_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    ''', (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        flash("User not found!", "danger")
        return redirect(url_for('home'))

    # Convert user data into a dictionary
    user_info = {
        "user_id": f"KKA{user_data['user_id']}",
        "name": user_data["name"],
        "email": user_data["email"],
        "phone": user_data["phone"],
        "nearest_city": user_data["nearest_city"],
        "details": user_data["details"],
        "num_children": user_data["num_children"],
        "interests": user_data["interests"] or "No interests listed"
    }

    # Fetch registered events
    cursor.execute('''
        SELECT e.title, e.uploaded_at 
        FROM event_registrations er
        JOIN events e ON er.event_id = e.event_id
        WHERE er.email = ?
    ''', (user_data["email"],))
    user_events = [{"title": row["title"], "date": row["uploaded_at"]} for row in cursor.fetchall()]

    conn.close()
    return render_template('profile.html', user_data=user_info, user_events=user_events)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please log in first."}), 401

    user_id = session['user_id']
    data = request.form
    name = data.get('name')
    phone = data.get('phone')
    city = data.get('city')
    family_details = data.get('family_details')
    num_children = data.get('num_children', 0)
    interests = data.get('interests')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update user details
    cursor.execute('''
        UPDATE users SET name = ?, phone = ? WHERE user_id = ?
    ''', (name, phone, user_id))

    # Update family details
    cursor.execute('''
        UPDATE family_details SET nearest_city = ?, details = ?, num_children = ? WHERE user_id = ?
    ''', (city, family_details, num_children, user_id))

    # Update interests
    cursor.execute("DELETE FROM interests WHERE family_id IN (SELECT family_id FROM family_details WHERE user_id = ?)", (user_id,))
    if interests:
        for interest in interests.split(","):
            cursor.execute("INSERT INTO interests (family_id, interest) VALUES ((SELECT family_id FROM family_details WHERE user_id = ?), ?)", (user_id, interest.strip()))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Profile updated successfully!"})

@app.route('/get-user-details')
def get_user_details():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, phone FROM users WHERE user_id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "name": user[0], "email": user[1], "phone": user[2]})
    else:
        return jsonify({"success": False, "message": "User not found"}), 404

@app.route('/delete-event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Event deleted successfully!"})

@app.route("/get_gallery_details/<int:image_id>")
def get_gallery_details(image_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch the gallery image details
    cursor.execute("SELECT id, title, description FROM gallery WHERE id = ?", (image_id,))
    gallery = cursor.fetchone()

    if not gallery:
        conn.close()
        return jsonify({"success": False, "message": "Image not found!"}), 404

    # Fetch extra images for the gallery
    cursor.execute("SELECT id, file_path FROM extra_images WHERE event_id = ?", (image_id,))
    extra_images = [{"id": row[0], "file_path": row[1]} for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "success": True,
        "id": gallery[0],
        "title": gallery[1],
        "description": gallery[2],
        "extra_images": extra_images,
        "edit_mode": True  # ✅ Fix for add images section
    })

@app.route('/delete_extra_image/<int:image_id>', methods=['DELETE'])
def delete_extra_image(image_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get the file path before deleting
    cursor.execute("SELECT file_path FROM extra_images WHERE id = ?", (image_id,))
    image_data = cursor.fetchone()

    if image_data:
        image_path = os.path.join(app.static_folder, image_data[0])
        if os.path.exists(image_path):
            os.remove(image_path)  # ✅ Delete the file

        cursor.execute("DELETE FROM extra_images WHERE id = ?", (image_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Image successfully deleted!"})

    conn.close()
    return jsonify({"success": False, "message": "Image not found!"})

@app.route("/add_gallery_images/<int:event_id>", methods=["POST"])
def add_gallery_images(event_id):
    extra_images = request.files.getlist("extra_images")

    if not extra_images:
        return jsonify({"success": False, "message": "No images uploaded"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for image in extra_images:
        if image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(filepath)

            cursor.execute(
                "INSERT INTO extra_images (event_id, file_path) VALUES (?, ?)", 
                (event_id, f"uploads/{filename}")
            )

    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Extra images added successfully!"})

@app.route('/edit_gallery_image', methods=['POST'])
def edit_gallery_image():
    image_id = request.form.get("image_id")
    title = request.form.get("title")
    description = request.form.get("description")

    if not image_id or not title or not description:
        return jsonify({"success": False, "message": "Missing fields!"})

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE gallery SET title = ?, description = ? WHERE id = ?", (title, description, image_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Gallery details updated successfully!"})
@app.route('/event_details/<int:event_id>')
def event_details(event_id):
    event = get_event_from_db(event_id)  # Fetch event from database
    
    if not event:
        print(f"Debug: No event found with ID {event_id}")  # Debugging
        return "Event not found", 404
    
    print(f"Debug: Retrieved event - {event}")  # Debugging output
    return render_template('upevent_details.html', event=event)

if __name__ == '__main__':
    app.run(debug=True)