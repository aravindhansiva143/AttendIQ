from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from datetime import date, datetime
import time
import os
import sys

app = Flask(__name__)
app.secret_key = 'attendiq_2026'
app.config['TEMPLATES_AUTO_RELOAD'] = True  # ← NEW
app.jinja_env.auto_reload = True             # ← NEW

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Aravind123',
    'database': 'attendance_db'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def setup_database():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        course VARCHAR(100),
        password VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        roll_no VARCHAR(20),
        registered_date DATE DEFAULT (CURRENT_DATE),
        password VARCHAR(100) DEFAULT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_date DATE,
        subject VARCHAR(100),
        teacher_name VARCHAR(100),
        total_checks INT DEFAULT 5,
        status VARCHAR(20) DEFAULT 'ongoing',
        start_time DATETIME,
        end_time DATETIME
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id INT,
        student_id INT,
        student_name VARCHAR(100),
        roll_no VARCHAR(20),
        detected_count INT DEFAULT 0,
        total_checks INT DEFAULT 5,
        percentage FLOAT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'ABSENT',
        session_date DATE,
        UNIQUE KEY unique_att (session_id, student_id)
    )''')
    conn.commit()
    cur.close(); conn.close()
    print("Database ready.")

# ── TEACHER PAGES ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register-teacher-page')
def register_teacher_page():
    return render_template('register_teacher.html')

@app.route('/register-student-page')
def register_student_page():
    if 'teacher_id' not in session:
        return redirect('/')
    return render_template('register_student.html',
        teacher_name=session.get('teacher_name'))

@app.route('/dashboard')
def dashboard():
    if 'teacher_id' not in session:
        return redirect('/')
    return render_template('dashboard.html',
        teacher_name=session.get('teacher_name'),
        teacher_course=session.get('teacher_course'))

@app.route('/session-page')
def session_page():
    if 'teacher_id' not in session:
        return redirect('/')
    return render_template('session.html',
        teacher_name=session.get('teacher_name'),
        teacher_course=session.get('teacher_course'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ── STUDENT PAGES ─────────────────────────────────────────────
@app.route('/student-login-page')
def student_login_page():
    return render_template('student_login.html')

@app.route('/student-dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/')
    return render_template('student_dashboard.html',
        student_name=session.get('student_name'),
        student_roll=session.get('student_roll'))

@app.route('/student-logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    session.pop('student_roll', None)
    return redirect('/')

# ── TEACHER AUTH ──────────────────────────────────────────────
@app.route('/api/register-teacher', methods=['POST'])
def register_teacher():
    data    = request.get_json()
    name    = data.get('name','').strip()
    course  = data.get('course','').strip()
    pwd     = data.get('password','').strip()
    confirm = data.get('confirm','').strip()
    if not name or not course or not pwd:
        return jsonify({'success':False,'message':'All fields required.'})
    if pwd != confirm:
        return jsonify({'success':False,'message':'Passwords do not match.'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM teachers WHERE name=%s", (name,))
        if cur.fetchone():
            return jsonify({'success':False,'message':'Teacher already exists.'})
        cur.execute("INSERT INTO teachers (name,course,password) VALUES (%s,%s,%s)", (name,course,pwd))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'success':True,'message':'Registered successfully!'})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    name = data.get('name','').strip()
    pwd  = data.get('password','').strip()
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM teachers WHERE name=%s AND password=%s", (name,pwd))
        t = cur.fetchone(); cur.close(); conn.close()
        if t:
            session['teacher_id']     = t['id']
            session['teacher_name']   = t['name']
            session['teacher_course'] = t['course']
            return jsonify({'success':True,'teacher':t['name'],'course':t['course']})
        return jsonify({'success':False,'message':'Invalid name or password.'})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

# ── STUDENT AUTH ──────────────────────────────────────────────
@app.route('/api/student-login', methods=['POST'])
def student_login():
    data     = request.get_json()
    roll_no  = data.get('roll_no', '').strip()
    password = data.get('password', '').strip()
    if not roll_no or not password:
        return jsonify({'success': False, 'message': 'Roll No and password are required.'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students WHERE roll_no=%s AND password=%s", (roll_no, password))
        student = cur.fetchone()
        cur.close(); conn.close()
        if student:
            session['student_id']   = student['id']
            session['student_name'] = student['name']
            session['student_roll'] = student['roll_no']
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid Roll No or Password.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/student-self-register', methods=['POST'])
def student_self_register():
    data     = request.get_json()
    name     = data.get('name','').strip()
    roll_no  = data.get('roll_no','').strip()
    password = data.get('password','').strip()
    confirm  = data.get('confirm','').strip()
    if not name or not roll_no or not password:
        return jsonify({'success':False,'message':'All fields are required.'})
    if password != confirm:
        return jsonify({'success':False,'message':'Passwords do not match.'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM students WHERE roll_no=%s", (roll_no,))
        if cur.fetchone():
            return jsonify({'success':False,'message':f'Roll No {roll_no} is already registered.'})
        cur.execute("INSERT INTO students (name, roll_no, password, registered_date) VALUES (%s,%s,%s,%s)",
                    (name, roll_no, password, str(date.today())))
        student_id = cur.lastrowid
        conn.commit(); cur.close(); conn.close()
        project_dir = os.path.dirname(os.path.abspath(__file__))
        folder_name = f"{student_id}_{name}"
        face_folder = os.path.join(project_dir, 'database', 'faces', folder_name)
        os.makedirs(face_folder, exist_ok=True)
        return jsonify({'success':True,'message':f'Registered successfully! Welcome {name}.','student_id': student_id})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

# ── STUDENT REGISTRATION BY TEACHER ──────────────────────────
@app.route('/api/register-student', methods=['POST'])
def register_student():
    if 'teacher_id' not in session:
        return jsonify({'success':False,'message':'Not logged in'})
    data     = request.get_json()
    name     = data.get('name','').strip()
    roll_no  = data.get('roll_no','').strip()
    password = data.get('password','').strip()
    if not name or not roll_no or not password:
        return jsonify({'success':False,'message':'Name, Roll No and Password are all required.'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM students WHERE roll_no=%s", (roll_no,))
        if cur.fetchone():
            return jsonify({'success':False,'message':f'Roll No {roll_no} already registered.'})
        cur.execute("INSERT INTO students (name, roll_no, password, registered_date) VALUES (%s,%s,%s,%s)",
                    (name, roll_no, password, str(date.today())))
        student_id = cur.lastrowid
        conn.commit(); cur.close(); conn.close()
        project_dir = os.path.dirname(os.path.abspath(__file__))
        folder_name = f"{student_id}_{name}"
        face_folder = os.path.join(project_dir, 'database', 'faces', folder_name)
        os.makedirs(face_folder, exist_ok=True)
        return jsonify({'success':True,
                        'message':f'{name} registered! Face folder: database/faces/{folder_name}/',
                        'student_id': student_id, 'folder': folder_name})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

@app.route('/api/face-count/<int:student_id>')
def face_count(student_id):
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT name FROM students WHERE id=%s", (student_id,))
        student = cur.fetchone(); cur.close(); conn.close()
        if not student:
            return jsonify({'count': 0})
        project_dir = os.path.dirname(os.path.abspath(__file__))
        folder_name = f"{student_id}_{student['name']}"
        face_folder = os.path.join(project_dir, 'database', 'faces', folder_name)
        if not os.path.exists(face_folder):
            return jsonify({'count': 0})
        count = len([f for f in os.listdir(face_folder) if f.lower().endswith(('.jpg','.jpeg','.png'))])
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)})

@app.route('/api/capture-face/<int:student_id>', methods=['POST'])
def capture_face(student_id):
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT name FROM students WHERE id=%s", (student_id,))
        student = cur.fetchone(); cur.close(); conn.close()
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'})

        project_dir = os.path.dirname(os.path.abspath(__file__))
        folder_name = f"{student_id}_{student['name']}"
        face_folder = os.path.join(project_dir, 'database', 'faces', folder_name)
        os.makedirs(face_folder, exist_ok=True)

        import tempfile
        tmp_dir     = tempfile.gettempdir()
        script_path = os.path.join(tmp_dir, 'attendiq_face_cap.py')
        path_file   = os.path.join(tmp_dir, 'attendiq_face_path.txt')

        with open(path_file, 'w', encoding='utf-8') as f:
            f.write(face_folder)

        student_name = student['name']
        script = f"""import cv2, os

# Read face folder path from file (avoids path escaping issues)
with open(r"{path_file}", encoding='utf-8') as f:
    face_folder = f.read().strip()

name = "{student_name}"
os.makedirs(face_folder, exist_ok=True)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Cannot open camera!")
    input("Press Enter to close...")
    exit()

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
count = 0
needed = 5

print("="*50)
print(f"  Face Registration: {{name}}")
print(f"  SPACE = capture photo")
print(f"  Q = quit")
print(f"  Need {{needed}} photos")
print("="*50)

while count < needed:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80,80))
    for (x,y,w,h) in faces:
        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
    cv2.rectangle(frame, (0,0), (640,50), (20,20,20), -1)
    cv2.putText(frame, f"{{name}}  |  Photos: {{count}}/{{needed}}", (10,22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,180), 2)
    cv2.putText(frame, "SPACE=capture  Q=quit", (10,42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)
    if len(faces) == 0:
        cv2.putText(frame, "No face - move closer!", (10,85), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,255), 2)
    else:
        cv2.putText(frame, "Face detected! Press SPACE", (10,85), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,0), 2)
    cv2.imshow("AttendIQ - Face Registration", frame)
    key = cv2.waitKey(1)
    if key == 32:
        if len(faces) > 0:
            x,y,w,h = faces[0]
            img_path = os.path.join(face_folder, f"{{count+1}}.jpg")
            cv2.imwrite(img_path, frame[y:y+h, x:x+w])
            count += 1
            print(f"  Photo {{count}}/{{needed}} saved!")
        else:
            print("  No face detected! Move closer.")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\\nDone! {{count}} photos saved for {{name}}")
input("\\nPress Enter to close this window...")
"""
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        import subprocess
        python_exe = sys.executable
        subprocess.Popen(
            ['cmd', '/k', python_exe, script_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return jsonify({'success': True, 'message': 'Camera window opened! Press SPACE to capture 5 photos, Q to quit.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete-student', methods=['POST'])
def delete_student():
    if 'teacher_id' not in session:
        return jsonify({'success':False,'message':'Not logged in'})
    data = request.get_json()
    student_id = data.get('student_id')
    if not student_id:
        return jsonify({'success':False,'message':'Student ID required.'})
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute('SET FOREIGN_KEY_CHECKS=0')
        cur.execute("DELETE FROM attendance WHERE student_id=%s", (student_id,))
        cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
        cur.execute('SET FOREIGN_KEY_CHECKS=1')
        conn.commit(); cur.close(); conn.close()
        return jsonify({'success':True,'message':'Student deleted.'})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

# ── STUDENT ATTENDANCE API ────────────────────────────────────
@app.route('/api/student-attendance')
def student_attendance():
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.session_date, s.subject, s.teacher_name,
                   a.detected_count, a.total_checks, a.percentage, a.status
            FROM attendance a
            LEFT JOIN sessions s ON a.session_id = s.id
            WHERE a.student_id = %s
            ORDER BY a.session_date DESC
        """, (session['student_id'],))
        rows = cur.fetchall()
        total_sessions = len(rows)
        present_count  = sum(1 for r in rows if r['status'] == 'PRESENT')
        absent_count   = total_sessions - present_count
        overall_pct    = round((present_count / total_sessions * 100), 1) if total_sessions > 0 else 0
        for r in rows:
            if r.get('session_date'): r['session_date'] = str(r['session_date'])
        cur.close(); conn.close()
        return jsonify({'records': rows, 'total_sessions': total_sessions,
                        'present_count': present_count, 'absent_count': absent_count,
                        'overall_percentage': overall_pct})
    except Exception as e:
        return jsonify({'error': str(e)})

# ── SESSION ───────────────────────────────────────────────────
@app.route('/api/start-session', methods=['POST'])
def start_session_api():
    if 'teacher_id' not in session:
        return jsonify({'success':False,'message':'Not logged in'})
    data         = request.get_json()
    subject      = data.get('subject', session.get('teacher_course','General'))
    total_checks = int(data.get('total_checks', 5))
    interval     = int(data.get('interval', 10))
    teacher_name = session.get('teacher_name')
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""INSERT INTO sessions (session_date,subject,teacher_name,total_checks,status,start_time)
            VALUES (%s,%s,%s,%s,'ongoing',%s)""",
            (str(date.today()), subject, teacher_name, total_checks, datetime.now()))
        session_id = cur.lastrowid
        conn.commit()
        cur.execute("SELECT id, name, roll_no FROM students")
        for s in cur.fetchall():
            cur.execute("""INSERT IGNORE INTO attendance
                (session_id,student_id,student_name,roll_no,detected_count,total_checks,percentage,status,session_date)
                VALUES (%s,%s,%s,%s,0,%s,0.0,'ABSENT',%s)""",
                (session_id, s[0], s[1], s[2], total_checks, str(date.today())))
        conn.commit(); cur.close(); conn.close()
        session['active_session_id'] = session_id
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bat = os.path.join(project_dir, 'start_camera.bat')
        cmd = f'start cmd /c "{bat} {session_id} {interval}"'
        os.system(cmd)
        print(f"Camera launched for session {session_id}")
        return jsonify({'success':True,'session_id':session_id})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success':False,'message':str(e)})

@app.route('/api/end-session', methods=['POST'])
def end_session():
    data       = request.get_json()
    session_id = data.get('session_id') or session.get('active_session_id')
    if not session_id:
        return jsonify({'success':False,'message':'No active session'})
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT total_checks FROM sessions WHERE id=%s", (session_id,))
        s  = cur.fetchone(); tc = s['total_checks'] if s else 5
        cur.execute("SELECT id,detected_count FROM attendance WHERE session_id=%s", (session_id,))
        for r in cur.fetchall():
            pct    = round((r['detected_count'] / tc) * 100, 1)
            status = 'PRESENT' if r['detected_count'] >= (tc / 2) else 'ABSENT'
            cur.execute("UPDATE attendance SET percentage=%s,status=%s WHERE id=%s", (pct,status,r['id']))
        cur.execute("UPDATE sessions SET status='completed',end_time=%s WHERE id=%s", (datetime.now(),session_id))
        conn.commit()
        cur.execute("""SELECT student_name,roll_no,detected_count,total_checks,percentage,status
            FROM attendance WHERE session_id=%s ORDER BY student_name""", (session_id,))
        results = cur.fetchall(); cur.close(); conn.close()
        session.pop('active_session_id', None)
        return jsonify({'success':True,'results':results})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)})

@app.route('/api/session-status/<int:session_id>')
def session_status(session_id):
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT student_name,roll_no,detected_count,total_checks,percentage,status
            FROM attendance WHERE session_id=%s ORDER BY student_name""", (session_id,))
        rows = cur.fetchall(); cur.close(); conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/api/camera-status')
def camera_status():
    return jsonify({'running': True})

# ── DATA ──────────────────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as total FROM students")
        total_students = cur.fetchone()['total']
        cur.execute("""SELECT
            SUM(CASE WHEN status='PRESENT' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status='ABSENT'  THEN 1 ELSE 0 END) as absent_count,
            COUNT(*) as total_records FROM attendance WHERE session_date=%s""", (str(date.today()),))
        today = cur.fetchone()
        cur.execute("SELECT COUNT(*) as total FROM sessions WHERE session_date=%s", (str(date.today()),))
        today_sessions = cur.fetchone()['total']
        cur.close(); conn.close()
        present = today['present_count'] or 0
        absent  = today['absent_count']  or 0
        total_r = today['total_records'] or 0
        rate    = round((present/total_r*100),1) if total_r > 0 else 0
        return jsonify({'total_students':total_students,'present':present,'absent':absent,
                        'attendance_rate':rate,'today_sessions':today_sessions})
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/api/attendance')
def api_attendance():
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT a.student_name,a.roll_no,a.detected_count,a.total_checks,
            a.percentage,a.status,a.session_date,s.subject,s.teacher_name
            FROM attendance a LEFT JOIN sessions s ON a.session_id=s.id
            ORDER BY a.session_date DESC, a.student_name""")
        rows = cur.fetchall(); cur.close(); conn.close()
        for r in rows:
            if r.get('session_date'): r['session_date'] = str(r['session_date'])
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/api/students')
def api_students():
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students ORDER BY name")
        rows = cur.fetchall(); cur.close(); conn.close()
        for r in rows:
            if r.get('registered_date'): r['registered_date'] = str(r['registered_date'])
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/api/sessions')
def api_sessions():
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall(); cur.close(); conn.close()
        for r in rows:
            for k in ['start_time','end_time','session_date']:
                if r.get(k): r[k] = str(r[k])
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error':str(e)})

if __name__ == '__main__':
    setup_database()
    print("="*40)
    print("  AttendIQ — http://localhost:5000")
    print("="*40)
    app.run(debug=True, port=5000, threaded=True)  # ← debug=True