import os
from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

# Upload folder
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# =========================
# HOME
# =========================
@app.route('/')
def home():
    return render_template('home.html')


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form['user_email']
        password = request.form['password']
        role = request.form['role']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        if role == "admin":
            cur.execute(
                "SELECT * FROM admin WHERE email=%s AND password=%s",
                (email, password)
            )
        else:
            cur.execute(
                "SELECT * FROM users WHERE email=%s AND password=%s AND role=%s",
                (email, password, role)
            )

        user = cur.fetchone()
        conn.close()

        if user:
            session['user'] = email
            session['role'] = role   # ✅ FIXED (IMPORTANT)

            print("LOGIN SUCCESS:", session)

            if session['role'] == "employee":
                return redirect('/employee_dashboard')
            elif session['role'] == "employer":
                return redirect('/dashboard')
            else:
                return redirect('/view_resources')

        else:
            return "Invalid Credentials"

    return render_template("login.html")


# =========================
# SIGNUP
# =========================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']
        gender = request.form['gender']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (name, email, phone, password, role, gender) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, email, phone, password, role, gender)
        )
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("signup.html")


# =========================
# EMPLOYER DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="freelance"
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (session['user'],))
    user = cursor.fetchone()
    conn.close()

    return render_template(
        'dashboard.html',
        role=user['role'],
        gender=user.get('gender'),
        phone=user.get('phone'),
        image=user.get('image')
    )


# =========================
# EMPLOYEE DASHBOARD (FIXED 🔥)
# =========================
@app.route('/employee_dashboard')
def employee_dashboard():
    print("SESSION DATA:", session)  # ✅ DEBUG

    if 'user' in session and session['role'] == 'employee':  # ✅ FIX 1

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cursor = conn.cursor(dictionary=True)

        # ✅ Fetch projects
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()

        # ✅ Fetch resources
        cursor.execute("SELECT * FROM resources")
        resources = cursor.fetchall()

        # ✅ Fetch employee details
        cursor.execute("SELECT gender, phone, image FROM users WHERE email=%s", (session['user'],))
        user_data = cursor.fetchone()

        # ✅ Store values safely
        if user_data:
            gender = user_data['gender'] if user_data['gender'] else ""
            phone = user_data['phone'] if user_data['phone'] else ""
            image = user_data['image'] if user_data['image'] else "employee_default.png"  # ✅ FIX 2
        else:
            gender = ""
            phone = ""
            image = "employee_default.png"  # ✅ default image

        return render_template(
            'employee_dashboard.html',
            projects=projects,
            resources=resources,
            gender=gender,
            phone=phone,
            image=image
        )

    else:
        return redirect('/login')

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# =========================
# VIEW PROJECTS
# =========================
@app.route('/view_projects', methods=['GET', 'POST'])
def view_projects():
    if 'user' in session:

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        if request.method == 'POST':
            search = request.form['search']

            cur.execute("""
                SELECT id, title, description, skills, budget, deadline, posted_date
                FROM projects
                WHERE (skills LIKE %s OR title LIKE %s)
                AND status='open'
            """, ('%' + search + '%', '%' + search + '%'))
        else:
            cur.execute("""
                SELECT id, title, description, skills, budget, deadline, posted_date
                FROM projects
                WHERE status='open'
            """)

        projects = cur.fetchall()

        # ✅ ADD THIS BLOCK (LOWEST BID LOGIC)
        project_bids = {}

        for p in projects:
            cur.execute("SELECT MIN(bid_amount) FROM applications WHERE project_id=%s", (p[0],))
            lowest = cur.fetchone()[0]

            project_bids[p[0]] = lowest if lowest else 0

        conn.close()

        return render_template(
            "view_projects.html",
            projects=projects,
            role=session.get('role'),
            project_bids=project_bids   # ✅ PASS THIS
        )

    return redirect('/login')


# =========================
# POST PROJECT
# =========================
@app.route('/post_project', methods=['GET', 'POST'])
def post_project():
    if 'user' in session and session['role'] == 'employer':

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            skills = request.form['skills']
            budget = request.form['budget']
            deadline = request.form['deadline']

            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="freelance"
            )
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO projects (title, description, skills, budget, deadline) VALUES (%s, %s, %s, %s, %s)",
                (title, description, skills, budget, deadline)
            )
            conn.commit()
            conn.close()

            return redirect('/dashboard')

        return render_template("post_project.html")

    return redirect('/login')


# =========================
# APPLY PROJECT (BID)
# =========================
@app.route('/apply_project', methods=['POST'])
def apply_project():

    if 'user' in session and session['role'] == 'employee':

        project_id = request.form['project_id']
        bid = request.form['bid']

        employee = session['user']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor()

        # get employee name
        cur.execute(
            "SELECT name FROM users WHERE email=%s",
            (employee,)
        )

        name = cur.fetchone()[0]

        # ✅ CHECK IF EMPLOYEE ALREADY BIDDED
        cur.execute("""
            SELECT * FROM applications
            WHERE project_id=%s AND employee_email=%s
        """, (project_id, employee))

        existing = cur.fetchone()

        # ✅ IF ALREADY EXISTS → UPDATE BID
        if existing:

            cur.execute("""
                UPDATE applications
                SET bid_amount=%s
                WHERE project_id=%s AND employee_email=%s
            """, (bid, project_id, employee))

        # ✅ ELSE → INSERT NEW BID
        else:

            cur.execute("""
                INSERT INTO applications
                (project_id, employee_email, employee_name, bid_amount)
                VALUES (%s, %s, %s, %s)
            """, (project_id, employee, name, bid))

        conn.commit()

        conn.close()

        return "success"

    return "failed"


# =========================
# VIEW APPLICATIONS
# =========================
@app.route('/view_applications')
def view_applications():

    if 'user' in session and session['role'] == 'employer':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor(dictionary=True)

        cur.execute("""

            SELECT
                applications.id,
                applications.project_id,
                projects.title,
                projects.deadline,
                projects.posted_date,
                projects.progress,
                users.name,
                users.email,
                users.phone,
                users.gender,
                applications.bid_amount

            FROM applications

            JOIN projects
            ON applications.project_id = projects.id

            JOIN users
            ON applications.employee_email = users.email

            WHERE projects.status='assigned'

            ORDER BY applications.bid_amount ASC

        """)

        data = cur.fetchall()

        conn.close()

        return render_template(
            "applications.html",
            data=data
        )

    return redirect('/login')


# =========================
# EDIT PROFILE
# =========================
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' in session:

        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            gender = request.form['gender']
            password = request.form['password']

            file = request.files['profile_pic']
            image_name = None

            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_name = filename

            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="freelance"
            )
            cur = conn.cursor()

            if image_name:
                cur.execute("""
                    UPDATE users
                    SET name=%s, phone=%s, gender=%s, password=%s, image=%s
                    WHERE email=%s
                """, (name, phone, gender, password, image_name, session['user']))
            else:
                cur.execute("""
                    UPDATE users
                    SET name=%s, phone=%s, gender=%s, password=%s
                    WHERE email=%s
                """, (name, phone, gender, password, session['user']))

            conn.commit()
            conn.close()

            if session['role'] == 'employee':
                return redirect('/employee_dashboard')
            else:
                return redirect('/dashboard')

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        cur.execute("SELECT name, phone, gender, password, image FROM users WHERE email=%s", (session['user'],))
        data = cur.fetchone()
        conn.close()

        return render_template("edit_profile.html", data=data)

    return redirect('/login')


# =========================
# DELETE PROJECT
# =========================
@app.route('/delete_project/<int:id>')
def delete_project(id):
    if 'user' in session and session['role'] == 'employer':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        cur.execute("DELETE FROM projects WHERE id = %s", (id,))
        conn.commit()
        conn.close()

        return redirect('/view_projects')

    return redirect('/login')


# =========================
# ADMIN RESOURCE
# =========================
@app.route('/post_resource', methods=['GET', 'POST'])
def post_resource():
    if 'user' in session and session['role'] == 'admin':

        if request.method == 'POST':
            title = request.form.get('title')
            skills = request.form.get('skills')
            video = request.files.get('video')

            if video and video.filename != "":
                filename = secure_filename(video.filename)
                video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database="freelance"
                )
                cur = conn.cursor()

                cur.execute(
                    "INSERT INTO resources (title, skills, video_file) VALUES (%s, %s, %s)",
                    (title, skills, filename)
                )

                conn.commit()
                conn.close()

            return redirect('/view_resources')

        return render_template('post_resource.html')

    return redirect('/login')


@app.route('/view_resources')
def view_resources():
    if 'user' in session:

        search = request.args.get('search')

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        if search:
            cur.execute("SELECT * FROM resources WHERE skills LIKE %s", ('%' + search + '%',))
        else:
            cur.execute("SELECT * FROM resources")

        data = cur.fetchall()
        conn.close()

        return render_template('view_resources.html', data=data)

    return redirect('/login')


@app.route('/delete_resource/<int:id>', methods=['POST'])
def delete_resource(id):
    if 'user' in session and session['role'] == 'admin':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )
        cur = conn.cursor()

        cur.execute("DELETE FROM resources WHERE id = %s", (id,))
        conn.commit()
        conn.close()

        return redirect('/view_resources')

    return redirect('/login')

#=========================
# employee_project
#=========================
@app.route('/employee_projects')
def employee_projects():

    if 'user' in session and session['role'] == 'employee':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cursor = conn.cursor(dictionary=True)

        # ✅ SHOW ONLY OPEN PROJECTS
        cursor.execute("""
            SELECT * FROM projects
            WHERE status='open'
        """)

        projects = cursor.fetchall()

        # ✅ LOWEST BID LOGIC
        project_bids = {}

        for p in projects:

            cursor.execute(
                "SELECT MIN(bid_amount) AS lowest_bid FROM applications WHERE project_id=%s",
                (p['id'],)
            )

            result = cursor.fetchone()

            lowest = result['lowest_bid'] if result['lowest_bid'] else 0

            project_bids[p['id']] = lowest

        conn.close()

        return render_template(
            'view_projects.html',

            projects=[
                (
                    p['id'],
                    p['title'],
                    p['description'],
                    p['skills'],
                    p['budget'],
                    p['deadline'],
                    p['posted_date']
                ) for p in projects
            ],

            role='employee',
            project_bids=project_bids
        )

    else:
        return redirect('/login')
    
# =========================
# VIEW BIDS
# =========================
@app.route('/view_bids/<int:project_id>')
def view_bids(project_id):

    if 'user' in session and session['role'] == 'employer':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor()

        # Get project title
        cur.execute("SELECT title FROM projects WHERE id=%s", (project_id,))
        project = cur.fetchone()

        # Get all bids
        cur.execute("""
            SELECT 
                users.name,
                users.gender,
                users.phone,
                users.email,
                applications.bid_amount
            FROM applications
            JOIN users 
            ON applications.employee_email = users.email
            WHERE applications.project_id=%s
            ORDER BY CAST(applications.bid_amount AS UNSIGNED) ASC
        """, (project_id,))

        bids = cur.fetchall()

        conn.close()

        return render_template(
    'view_bids.html',
    bids=bids,
    project=project,
    project_id=project_id
)

    return redirect('/login')

# =========================
# ASSIGN TASK
# =========================
@app.route('/assign_task/<int:project_id>/<email>')
def assign_task(project_id, email):

    if 'user' in session and session['role'] == 'employer':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor()

        # assign employee
        cur.execute("""
            UPDATE projects
            SET assigned_to=%s,
                status='assigned'
            WHERE id=%s
        """, (email, project_id))

        conn.commit()
        conn.close()

        return redirect('/view_projects')

    return redirect('/login')

# =========================
# CLOSE PROJECT
# =========================
@app.route('/close_project/<int:project_id>')
def close_project(project_id):

    if 'user' in session and session['role'] == 'employer':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor()

        cur.execute("""
            UPDATE projects
            SET status='closed'
            WHERE id=%s
        """, (project_id,))

        conn.commit()
        conn.close()

        return redirect('/view_projects')

    return redirect('/login')

# =========================
# MY TASKS
# =========================
@app.route('/my_tasks')
def my_tasks():

    if 'user' in session and session['role'] == 'employee':

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor(dictionary=True)

        cur.execute("""

            SELECT 
                projects.*,
                applications.bid_amount

            FROM projects

            JOIN applications
            ON projects.id = applications.project_id

            WHERE projects.assigned_to=%s
            AND projects.status='assigned'
            AND applications.employee_email=%s

        """, (session['user'], session['user']))

        tasks = cur.fetchall()

        conn.close()

        return render_template(
            'my_tasks.html',
            tasks=tasks
        )

    return redirect('/login')

# =========================
# VIEW STATUS
# =========================
@app.route('/view_status/<int:project_id>')
def view_status(project_id):

    if 'user' in session:

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT title, progress
            FROM projects
            WHERE id=%s
        """, (project_id,))

        project = cur.fetchone()

        conn.close()

        return render_template(
            'view_status.html',
            project=project
        )

    return redirect('/login')

# =========================
# UPDATE PROGRESS
# =========================
@app.route('/update_progress', methods=['POST'])
def update_progress():

    if 'user' in session and session['role'] == 'employee':

        project_id = request.form['project_id']
        progress = request.form['progress']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="freelance"
        )

        cur = conn.cursor()

        cur.execute("""
            UPDATE projects
            SET progress=%s
            WHERE id=%s
        """, (progress, project_id))

        conn.commit()

        conn.close()

        return redirect('/my_tasks')

    return redirect('/login')

# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)