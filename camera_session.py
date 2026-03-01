"""
camera_session.py - OpenCV LBPH face recognition (NO DeepFace)
Usage: python camera_session.py --session_id 1 --interval 10
"""

import cv2
import sys
import os
import argparse
import time
import numpy as np
import mysql.connector
from datetime import datetime, date

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "Aravind123",
    "database": "attendance_db"
}

FACES_DIR            = "database/faces"
CONFIDENCE_THRESHOLD = 85

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def load_students():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id, name, roll_no FROM students")
    rows = {row[0]: {"name": row[1], "roll_no": row[2] or ""} for row in cur.fetchall()}
    conn.close()
    print(f"Loaded {len(rows)} students")
    return rows

def get_total_checks(session_id):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT total_checks FROM sessions WHERE id=%s", (session_id,))
        row = cur.fetchone(); conn.close()
        return row[0] if row else 5
    except:
        return 5

def mark_present(session_id, student_id, info, total_checks):
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id, detected_count FROM attendance WHERE session_id=%s AND student_id=%s",
                    (session_id, student_id))
        existing = cur.fetchone()
        if existing:
            new_count  = existing[1] + 1
            percentage = round((new_count / total_checks) * 100, 1)
            status     = "PRESENT" if new_count >= (total_checks / 2) else "ABSENT"
            cur.execute("UPDATE attendance SET detected_count=%s, percentage=%s, status=%s WHERE id=%s",
                        (new_count, percentage, status, existing[0]))
        else:
            cur.execute("""INSERT INTO attendance
                (session_id,student_id,student_name,roll_no,detected_count,total_checks,percentage,status,session_date)
                VALUES (%s,%s,%s,%s,1,%s,%s,'PRESENT',%s)""",
                (session_id, student_id, info["name"], info["roll_no"],
                 total_checks, round(1/total_checks*100,1), date.today()))
        conn.commit(); cur.close(); conn.close()
        print(f"  PRESENT: {info['name']}")
    except Exception as e:
        print(f"  DB error: {e}")

def mark_all_absent(session_id, students, marked_ids, total_checks):
    try:
        conn = get_db(); cur = conn.cursor()
        for sid, info in students.items():
            cur.execute("SELECT id FROM attendance WHERE session_id=%s AND student_id=%s", (session_id, sid))
            if not cur.fetchone():
                cur.execute("""INSERT INTO attendance
                    (session_id,student_id,student_name,roll_no,detected_count,total_checks,percentage,status,session_date)
                    VALUES (%s,%s,%s,%s,0,%s,0.0,'ABSENT',%s)""",
                    (session_id, sid, info["name"], info["roll_no"], total_checks, date.today()))
        conn.commit(); cur.close(); conn.close()
        print(f"Done! Present: {len(marked_ids)} | Absent: {len(students)-len(marked_ids)}")
    except Exception as e:
        print(f"Error: {e}")

def train_recognizer(students):
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    recognizer    = cv2.face.LBPHFaceRecognizer_create()
    faces         = []
    labels        = []
    label_map     = {}
    label_counter = 0

    for folder in sorted(os.listdir(FACES_DIR)):
        folder_path = os.path.join(FACES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        student_id = None
        parts = folder.split("_", 1)
        if parts[0].isdigit():
            sid = int(parts[0])
            if sid in students:
                student_id = sid
        if student_id is None:
            fname = folder.replace("_", " ").lower()
            for sid, info in students.items():
                if info["name"].lower() in fname:
                    student_id = sid; break
        if student_id is None:
            continue

        label_map[label_counter] = student_id
        count = 0
        for img_file in os.listdir(folder_path):
            if not img_file.lower().endswith(('.jpg','.jpeg','.png')):
                continue
            img = cv2.imread(os.path.join(folder_path, img_file), cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            detected = face_cascade.detectMultiScale(img, 1.1, 5, minSize=(50,50))
            if len(detected) > 0:
                x,y,w,h = detected[0]
                face_roi = cv2.resize(img[y:y+h, x:x+w], (200,200))
            else:
                face_roi = cv2.resize(img, (200,200))
            faces.append(face_roi)
            labels.append(label_counter)
            count += 1
        print(f"  {students[student_id]['name']}: {count} photos")
        label_counter += 1

    if not faces:
        print("ERROR: No face images found!")
        sys.exit(1)

    recognizer.train(faces, np.array(labels))
    print(f"Trained on {len(faces)} images for {label_counter} students")
    return recognizer, label_map, face_cascade

def run_session(session_id, interval):
    print("\n" + "="*55)
    print(f"  AttendIQ LBPH — Session {session_id}")
    print(f"  Scan every: {interval}s  |  Press Q to stop")
    print("="*55)

    students     = load_students()
    total_checks = get_total_checks(session_id)

    print("Training face recognizer...")
    recognizer, label_map, face_cascade = train_recognizer(students)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera!")
        sys.exit(1)

    print(f"\nCamera opened! Press Q to stop.\n")

    marked_ids = {}
    last_scan  = 0
    last_label = "Ready..."
    last_color = (0, 165, 255)

    while True:
        ret, frame = cap.read()
        if not ret: break

        display = frame.copy()
        now  = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_detected = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80,80))

        if now - last_scan >= interval and len(faces_detected) > 0:
            last_scan = now
            print(f"Scanning at {datetime.now().strftime('%H:%M:%S')}...")
            x,y,w,h = faces_detected[0]
            face_roi = cv2.resize(gray[y:y+h, x:x+w], (200,200))
            label_int, confidence = recognizer.predict(face_roi)
            print(f"  Confidence: {confidence:.1f} (threshold: {CONFIDENCE_THRESHOLD})")

            if confidence <= CONFIDENCE_THRESHOLD:
                student_id = label_map.get(label_int)
                if student_id and student_id in students:
                    mark_present(session_id, student_id, students[student_id], total_checks)
                    marked_ids[student_id] = marked_ids.get(student_id, 0) + 1
                    last_label = f"PRESENT: {students[student_id]['name']}"
                    last_color = (0, 200, 0)
            else:
                last_label = "Unknown — move closer"
                last_color = (0, 0, 220)
                print("  Unknown face")

        for (x,y,w,h) in faces_detected:
            cv2.rectangle(display, (x,y), (x+w,y+h), last_color, 2)
            cv2.putText(display, last_label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, last_color, 2)

        status = (f"Session {session_id}  |  Marked: {len(marked_ids)}/{len(students)}  |  "
                  f"Next scan: {max(0, int(interval-(now-last_scan)))}s  |  "
                  f"{datetime.now().strftime('%H:%M:%S')}")
        cv2.rectangle(display, (0,0), (720,38), (20,20,20), -1)
        cv2.putText(display, status, (8,26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255,255,255), 1)
        cv2.rectangle(display, (0, display.shape[0]-30), (720, display.shape[0]), (20,20,20), -1)
        cv2.putText(display, "Press Q to end session", (8, display.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)

        cv2.imshow("AttendIQ — Attendance Camera", display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nSession ended.")
            break

    cap.release()
    cv2.destroyAllWindows()
    mark_all_absent(session_id, students, marked_ids, total_checks)
    print("="*55 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_id", type=int, required=True)
    parser.add_argument("--interval",   type=int, default=10)
    args = parser.parse_args()
    run_session(args.session_id, args.interval)
