from flask import Flask, render_template, url_for, flash, request, redirect, session, send_from_directory
import sqlite3, os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'secret_key'  # Secret key for session management


# Initialize the database
def init_db():
    conn = sqlite3.connect('placement_db.db', timeout=0)
    c = conn.cursor()

    # Create applicants table
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            usn TEXT UNIQUE,
            number TEXT,
            email TEXT,
            tenth_percentage REAL,
            twelfth_percentage REAL,
            diploma_percentage TEXT,
            cgpa REAL,
            password TEXT
        )
    ''')

    # Create coordinators table
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS coordinators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            user_id TEXT UNIQUE,
            department TEXT,
            email TEXT,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS posted_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            job_title TEXT,
            job_description TEXT,
            location TEXT,
            salary TEXT,
            job_expiry_date TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_usn TEXT,
            job_id INTEGER,
            FOREIGN KEY (student_usn) REFERENCES applicants (usn),
            FOREIGN KEY (job_id) REFERENCES posted_jobs (id)
        )
    ''')

    conn.commit()
    conn.close()

# Route for the home page
@app.route('/')
def home():
    return render_template('home.html')

# Route for student registration
@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        # Get the form data
        name = request.form['name']
        usn = request.form['usn']
        number = request.form['number']
        email = request.form['email']
        tenth_percentage = request.form['tenth_percentage']
        twelfth_percentage = request.form['twelfth_percentage']
        diploma_percentage = request.form['diploma_percentage']
        cgpa = request.form['cgpa']
        password = request.form['password']
        
        # Connect to the database
        conn = sqlite3.connect('placement_db.db')
        c = conn.cursor()
        
        # Check if the USN or Email already exists in the database
        c.execute('SELECT * FROM applicants WHERE usn = ? OR email = ?', (usn, email))
        existing_user = c.fetchone()  # Fetch one record

        if existing_user:
            # If user exists, flash a message and redirect back to registration page
            flash('User with this USN or Email already exists. Please use a different one.', 'error')
            return redirect(url_for('register_student'))
        
        # Insert the new student record into the database
        c.execute(''' 
            INSERT INTO applicants (name, usn, number, email, tenth_percentage, twelfth_percentage, diploma_percentage, cgpa, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, usn, number, email, tenth_percentage, twelfth_percentage, diploma_percentage, cgpa, password))
        
        conn.commit()
        conn.close()

        # Flash a success message and redirect to the login page
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login_student'))

    # For GET request, render the registration form
    return render_template('student_reg.html')

# Route for student login
@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        usn = request.form['usn']
        password = request.form['password']

        conn = sqlite3.connect('placement_db.db')
        c = conn.cursor()
        c.execute('SELECT * FROM applicants WHERE usn = ? AND password = ?', (usn, password))
        student = c.fetchone()
        conn.close()

        if student:
            # Store student ID and USN in session
            #session['student_id'] = student[0]  # Store student ID in session (assuming it's the first column)
            session['usn'] = student[2]  # Store USN in session (assuming it's the third column)            
            return redirect(url_for('student_dashboard'))  # Redirect to student dashboard
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('student_login.html')


# Route for coordinator registration
@app.route('/register-coordinator', methods=['GET', 'POST'])
def register_coordinator():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        user_id = request.form['user_id']
        department = request.form['department']
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Insert data into the database
            conn = sqlite3.connect('placement_db.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO coordinators (name, user_id, department, email, password)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, user_id, department, email, password))
            conn.commit()
            conn.close()
            
            flash('Coordinator registered successfully!', 'success')
            return redirect('/login-coordinator')
        except sqlite3.IntegrityError:
            flash('User ID or Email already exists. Please use unique values.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    # Render the registration form
    return render_template('coordinator_reg.html')

# Route for coordinator login
@app.route('/login-coordinator', methods=['GET', 'POST'])
def login_coordinator():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        # Validate credentials
        conn = sqlite3.connect('placement_db.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM coordinators WHERE user_id = ? AND password = ?', (user_id, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # Store user_id in session
            session['user_id'] = user[2]  # Assuming the user_id is at index 2            
            return redirect('/dashboard')
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('coordinator_login.html')

#Function to delete jobs
from datetime import datetime
def delete_expired_jobs():
    # Get the current system time
    current_time = datetime.now()
    
    # Connect to the database
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()
    
    # Fetch all jobs from the database
    cursor.execute('SELECT id, job_expiry_date FROM posted_jobs')
    jobs = cursor.fetchall()
    
    # Iterate through each job and check if it is expired
    for job in jobs:
        id, job_expiry_date = job
        job_expiry_datetime = datetime.strptime(job_expiry_date, '%Y-%m-%dT%H:%M')
        
        # If the job expiry time has passed, delete it
        if current_time > job_expiry_datetime:
            cursor.execute('DELETE FROM posted_jobs WHERE id = ?', (id,))
            print(f"Deleted expired job with ID {id} at {current_time}")
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()


# Route for the dashboard
@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in (session contains user_id)
    if 'user_id' not in session:
        flash('You need to log in first.', 'error')
        return redirect('/login-coordinator')

    # Fetch the coordinator's profile details based on user_id stored in session
    user_id = session['user_id']
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM coordinators WHERE user_id = ?', (user_id,))
    coordinator = cursor.fetchone()
    conn.close()

    if coordinator:
        # Pass coordinator details to the template
        delete_expired_jobs()
        return render_template('dashboard.html', coordinator=coordinator)
    else:
        flash('Coordinator not found.', 'error')
        return redirect('/login-coordinator')
    
@app.route('/update_profile', methods=['GET','POST'])
def update_profile():
    # Check if the coordinator is logged in (assuming coordinator ID is in session)
    if 'user_id' not in session:        
        return redirect(url_for('login_coordinator'))

    user_id = session['user_id']

    # Fetch form data
    name = request.form['name']
    department = request.form['department']
    email = request.form['email']

    # Update the coordinator's profile in the database
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE coordinators
        SET name = ?, department = ?, email = ?
        WHERE user_id = ?
    ''', (name, department, email, user_id))
    conn.commit()
    conn.close()
   
    return redirect(url_for('dashboard'))  # Update with the actual route for coordinator dashboard


from datetime import datetime, timedelta

@app.route('/post-job', methods=['POST'])
def post_job():
    # Get job details from the form
    company_name = request.form['company_name']
    job_title = request.form['job_title']
    job_description = request.form['job_description']
    location = request.form['location']
    salary = request.form['salary']
    
    # Get expiry date from form or set default (e.g., 30 days from now)
    expiry_date = request.form.get('job_expiry_date')  # Use form input if provided
    if not expiry_date:  # Default to 30 days if no date provided
        expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Store the job details in the database
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posted_jobs (company_name, job_title, job_description, location, salary, job_expiry_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (company_name, job_title, job_description, location, salary, expiry_date))
    conn.commit()
    conn.close()

    # Redirect to posted jobs page    
    return redirect(url_for('posted_jobs'))



@app.route('/posted-jobs')
def posted_jobs():
    # Fetch posted jobs from the database
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posted_jobs')
    jobs = cursor.fetchall()
    conn.close()

    return render_template('posted_jobs.html', jobs=jobs)

@app.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # If the method is POST, update the job
    if request.method == 'POST':
        company_name = request.form['company_name']
        job_title = request.form['job_title']
        job_description = request.form['job_description']
        location = request.form['location']
        salary = request.form['salary']

        # Update the job in the database
        cursor.execute(''' 
            UPDATE posted_jobs
            SET company_name = ?, job_title = ?, job_description = ?, location = ?, salary = ?
            WHERE id = ?
        ''', (company_name,job_title, job_description, location, salary, job_id))
        conn.commit()
        conn.close()
        
        return redirect(url_for('posted_jobs'))

    # If method is GET, fetch the job details to pre-fill the form
    cursor.execute('SELECT * FROM posted_jobs WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    conn.close()

    return render_template('edit_job.html', job=job)

@app.route('/delete-job/<int:job_id>', methods=['GET', 'POST'])
def delete_job(job_id):
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # Delete the job from the database
    cursor.execute('DELETE FROM posted_jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('posted_jobs'))

@app.route('/student_dashboard', methods=['GET', 'POST'])
def student_dashboard():
    if 'usn' not in session:
        flash('You need to log in first.', 'error')
        return redirect(url_for('login_student'))

    student_usn = session['usn']
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # Fetch student details
    cursor.execute('SELECT * FROM applicants WHERE usn = ?', (student_usn,))
    student = cursor.fetchone()
    if not student:        
        return redirect(url_for('login_student'))

    # Fetch available jobs
    cursor.execute('SELECT * FROM posted_jobs')
    available_jobs = cursor.fetchall()
    conn.close()

    return render_template('student_dashboard.html', student=student, available_jobs=available_jobs)

@app.route('/student_update', methods=['POST'])
def student_update():
    if 'usn' not in session:        
        return redirect(url_for('login_student'))

    student_usn = session['usn']
    updated_name = request.form['name']
    updated_email = request.form['email']
    updated_cgpa = request.form['cgpa']

    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # Update the student's profile
    cursor.execute('''
        UPDATE applicants 
        SET name = ?, email = ?, cgpa = ? 
        WHERE usn = ?
    ''', (updated_name, updated_email, updated_cgpa, student_usn))
    conn.commit()
    conn.close()
    
    return redirect(url_for('student_dashboard'))

@app.route('/apply_job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    if 'usn' not in session:
        flash('You need to log in first.', 'error')
        return redirect(url_for('login_student'))

    student_usn = session['usn']
    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # Check if already applied
    cursor.execute('SELECT * FROM applied_jobs WHERE student_usn = ? AND job_id = ?', (student_usn, job_id))
    if cursor.fetchone():
        flash('You have already applied for this job.', 'info')
    else:
        cursor.execute('INSERT INTO applied_jobs (student_usn, job_id) VALUES (?, ?)', (student_usn, job_id))
        conn.commit()
        

    conn.close()
    return redirect(url_for('student_dashboard'))

@app.route('/applied-jobs', methods=['GET'])
def applied_jobs():
    if 'usn' not in session:        
        return redirect(url_for('login_student'))

    student_usn = session['usn']

    conn = sqlite3.connect('placement_db.db')
    cursor = conn.cursor()

    # Fetch jobs the student has applied for
    cursor.execute('''
        SELECT pj.company_name,pj.job_title, pj.job_description, pj.location, pj.salary
        FROM applied_jobs aj
        INNER JOIN posted_jobs pj ON aj.job_id = pj.id
        WHERE aj.student_usn = ?
    ''', (student_usn,))
    applied_jobs = cursor.fetchall()

    conn.close()

    return render_template('applied_jobs.html', applied_jobs=applied_jobs)

@app.route('/search_company', methods=['GET'])
def search_page():
    return render_template('applied_students.html')  # Render the search form page

@app.route('/search_company', methods=['POST', 'GET'])
def search_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name')

        conn = sqlite3.connect('placement_db.db')
        c = conn.cursor()

        # Fetch job IDs for the given company name
        c.execute('SELECT id, job_title FROM posted_jobs WHERE company_name = ?', (company_name,))
        jobs = c.fetchall()
        job_ids = [job[0] for job in jobs]
        job_titles = {job[0]: job[1] for job in jobs}  # Map job_id to job_title

        # Fetch student_usn for the job IDs
        if job_ids:
            c.execute('SELECT student_usn, job_id FROM applied_jobs WHERE job_id IN ({})'.format(
                ','.join(['?'] * len(job_ids))), job_ids)
            applied_students = c.fetchall()

            student_usns = [student[0] for student in applied_students]
            job_map = {student[0]: student[1] for student in applied_students}  # Map usn to job_id

            # Fetch student details
            if student_usns:
                c.execute('''
                    SELECT name, usn, number, email, tenth_percentage, twelfth_percentage, diploma_percentage, cgpa
                    FROM applicants
                    WHERE usn IN ({})
                '''.format(','.join(['?'] * len(student_usns))), student_usns)

                students = [
                    [job_titles[job_map[student[1]]]] + list(student) for student in c.fetchall()
                ]
            else:
                students = []
        else:
            students = []

        conn.close()
        return render_template('applied_students.html', students=students, company_name=company_name)
    return redirect(url_for('dashboard'))

import os
import pandas as pd
import sqlite3
from flask import send_file, Response

@app.route('/download_excel/<company_name>', methods=['GET'])
def download_excel(company_name):
    # Connect to the SQLite database
    conn = sqlite3.connect('placement_db.db')
    c = conn.cursor()

    # Fetch job IDs for the given company name
    c.execute('SELECT id, job_title FROM posted_jobs WHERE company_name = ?', (company_name,))
    jobs = c.fetchall()
    job_ids = [job[0] for job in jobs]
    job_titles = {job[0]: job[1] for job in jobs}  # Map job_id to job_title

    # Fetch student_usn for the job IDs
    if job_ids:
        c.execute('SELECT student_usn, job_id FROM applied_jobs WHERE job_id IN ({})'.format(
            ','.join(['?'] * len(job_ids))), job_ids)
        applied_students = c.fetchall()

        student_usns = [student[0] for student in applied_students]
        job_map = {student[0]: student[1] for student in applied_students}  # Map usn to job_id

        # Fetch student details
        if student_usns:
            c.execute(''' 
                SELECT name, usn, number, email, tenth_percentage, twelfth_percentage, diploma_percentage, cgpa
                FROM applicants
                WHERE usn IN ({})
            '''.format(','.join(['?'] * len(student_usns))), student_usns)

            students = [
                [job_titles[job_map[student[1]]]] + list(student) for student in c.fetchall()
            ]
        else:
            students = []
    else:
        students = []

    conn.close()

    if not students:
        return Response("No data available to export.", status=404)

    # Define column names and create a DataFrame
    columns = [
        "Job Title", "NAME", "USN", "Phone Number",
        "Email", "10th Percentage", 
        "12th Percentage", "Diploma Percentage", "CGPA"
    ]
    df = pd.DataFrame(students, columns=columns)

    # Determine the system's Downloads folder path
    downloads_folder = os.path.join(os.path.expanduser("~"), 'Downloads')

    # Define the file path within the Downloads folder
    file_path = os.path.join(downloads_folder, f"{company_name}_applied_students.xlsx")

    # Save the DataFrame to an Excel file
    df.to_excel(file_path, index=False)

    # Serve the file for download
    return send_file(file_path, as_attachment=True, download_name=f"{company_name}_applied_students.xlsx")
    
    
init_db()    
    
