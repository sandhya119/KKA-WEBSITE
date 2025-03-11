import os
import sqlite3
from flask import send_file
import pandas as pd
from fpdf import FPDF
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

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
    file_path TEXT NOT NULL
    );
    
                     

    ''')

    # Insert admin user if not exists
    cursor.execute("SELECT * FROM admins WHERE email = ?", ("info@karavalkonkans.org.au",))
    if not cursor.fetchone():
        hashed_password = generate_password_hash("karavalkonkans@2025", method="pbkdf2:sha256")
        cursor.execute("INSERT INTO admins (email, password) VALUES (?, ?)",
                       ("info@karavalkonkans.org.au", hashed_password))
    conn.commit()
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

@app.route('/upload-content', methods=['POST'])
def upload_content():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        file = request.files['file']

        if not title or not category or not file:
            flash("Please fill in all fields!", "danger")
            return redirect(url_for('admin_panel'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO events (title, description, file_path, category) VALUES (?, ?, ?, ?)",
                           (title, description, f"uploads/{filename}", category))
            conn.commit()
            conn.close()

            flash("Content uploaded successfully!", "success")
        else:
            flash("Invalid file type!", "danger")
            

    return redirect(url_for('admin_panel'))

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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, title, description, file_path,category FROM events WHERE category='upcoming' ORDER BY uploaded_at DESC")
    events = cursor.fetchall()
    conn.close()
    return render_template('upevents.html', events=events)


@app.route('/past-events')
def past_events():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, file_path FROM events WHERE category='past' ORDER BY uploaded_at DESC")
    events = cursor.fetchall()
    conn.close()
    return render_template('Past_Events.html', events=events)


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



@app.route('/admin')
def admin_panel():
    if 'admin_id' not in session:
        flash("Please log in as an admin to access this page.", "danger")
        return redirect(url_for('admin_login'))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Fetch user registrations with family details and interests
        query = '''
        SELECT 
        u.user_id AS UserID, 
    u.name AS Name, 
    u.email AS Email, 
    u.phone AS Phone,
    f.nearest_city AS NearestCity, 
    f.details AS Details, 
    f.num_children AS NumberOfChildren
FROM users u
LEFT JOIN family_details f ON u.user_id = f.user_id;
        '''
        cursor.execute(query)
        registrations = cursor.fetchall()

        # Fetch upcoming events
        cursor.execute("SELECT event_id, title, description FROM events WHERE category='upcoming' ORDER BY uploaded_at DESC")
        upcoming_events = cursor.fetchall()

         # Fetch past events
        cursor.execute("SELECT title, description, event_id FROM events WHERE category='past' ORDER BY uploaded_at DESC")
        past_events = cursor.fetchall()

        # Fetch event registrations with event details
        cursor.execute('''
        SELECT er.registration_id, er.event_id, e.title, er.name, er.email, er.phone, er.num_people
        FROM event_registrations er
        JOIN events e ON er.event_id = e.event_id
        ORDER BY er.registration_id DESC
        ''')
        event_registrations = cursor.fetchall()

        #new
        # Fetch total registered users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(num_people), 0) FROM event_registrations")
        total_event_registrations = cursor.fetchone()[0]

        # Fetch event-wise registration counts (each event's total attendees)
        cursor.execute('''
            SELECT e.title, COALESCE(SUM(er.num_people), 0)
            FROM event_registrations er
            JOIN events e ON er.event_id = e.event_id
            GROUP BY e.title
        ''')
        event_chart_data = cursor.fetchall()

        cursor.execute('''
            SELECT COALESCE(f.nearest_city, 'None'), COALESCE(SUM(er.num_people), 0)
            FROM event_registrations er
            JOIN users u ON er.email = u.email
            LEFT JOIN family_details f ON u.user_id = f.user_id
            GROUP BY f.nearest_city
        ''')
        event_city_chart_data = cursor.fetchall()

        # Fetch gallery images
        cursor.execute("SELECT id, title, description, file_path FROM gallery")
        gallery_images = cursor.fetchall()

         # Fetch news articles
    cursor.execute("SELECT id, title, description FROM news ORDER BY id DESC")
    news_articles = cursor.fetchall()
    conn.close()

    formatted_news = [{"id": row[0], "title": row[1], "description": row[2]} for row in news_articles]


    return render_template(
        "admin.html",
        registrations=registrations,
        upcoming_events=upcoming_events,
        past_events=past_events,
        event_registrations=event_registrations,  # Pass event registrations to the template
        total_users=total_users,
        total_event_registrations=total_event_registrations,
        event_chart_data=event_chart_data,
        event_city_chart_data=event_city_chart_data,
        gallery_images=gallery_images,
        news_articles=formatted_news
    )


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



@app.route('/gallery')
def gallery():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch gallery images from the new gallery table
    cursor.execute("SELECT id, title, description, file_path FROM gallery")
    gallery_images = [dict(id=row[0], title=row[1], description=row[2], file_path=row[3]) for row in cursor.fetchall()]
    
    conn.close()
    return render_template('gallery.html', gallery_images=gallery_images)

@app.route('/upload_gimages', methods=['POST'])
def upload_gimages():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image = request.files['image']

        if image and title and description:
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
            image.save(image_path)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO gallery (title, description, file_path) VALUES (?, ?, ?)", 
                           (title, description, f"uploads/{image.filename}"))
            conn.commit()
            conn.close()

    return redirect(url_for('gallery'))

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


import os

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
    cursor = conn.cursor()

    # Fetch user details
    cursor.execute('''
        SELECT u.user_id, u.name, u.email, u.phone, f.nearest_city, f.details, f.num_children, 
               GROUP_CONCAT(i.interest) AS interests
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

    # Convert tuple to dictionary
    user_info = {
        "user_id": f"KKA{user_data[0]}",
        "name": user_data[1],
        "email": user_data[2],
        "phone": user_data[3],
        "nearest_city": user_data[4],
        "details": user_data[5],
        "num_children": user_data[6],
        "interests": user_data[7] or ""
    }

    # Fetch registered events
    cursor.execute('''
        SELECT e.title, e.uploaded_at 
        FROM event_registrations er
        JOIN events e ON er.event_id = e.event_id
        WHERE er.email = ?
    ''', (user_data[2],))
    user_events = [{"title": row[0], "date": row[1]} for row in cursor.fetchall()]

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



if __name__ == '__main__':
    app.run(debug=True)