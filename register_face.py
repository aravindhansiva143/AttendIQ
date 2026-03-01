"""
register_face.py - Register student faces into database
Run: python register_face.py
"""
import cv2
import os
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Aravind123',
    'database': 'attendance_db'
}

FACES_DIR = "database/faces"

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def add_student(name, roll_no):
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO students (name, roll_no) VALUES (%s, %s)", (name, roll_no))
    conn.commit()
    student_id = cur.lastrowid
    cur.close(); conn.close()
    return student_id

def register_student():
    print("="*40)
    print("  STUDENT FACE REGISTRATION")
    print("="*40)

    name    = input("\nEnter student name: ").strip()
    roll_no = input("Enter roll number: ").strip()

    if not name or not roll_no:
        print("Name and roll number cannot be empty!")
        return

    os.makedirs(FACES_DIR, exist_ok=True)
    student_id     = add_student(name, roll_no)
    student_folder = os.path.join(FACES_DIR, f"{student_id}_{name}")
    os.makedirs(student_folder, exist_ok=True)

    cap          = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    count = 0
    print(f"\nCamera open for: {name}")
    print("Press SPACE to capture photo (need 5 photos)")
    print("Press Q to quit\n")

    while count < 5:
        ret, frame = cap.read()
        if not ret: break

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        for (x,y,w,h) in faces:
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

        cv2.putText(frame, f"{name} | Photos: {count}/5",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        cv2.putText(frame, "SPACE=capture  Q=quit",
                    (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        if len(faces) == 0:
            cv2.putText(frame, "No face detected!", (10,100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        cv2.imshow("Register Face", frame)
        key = cv2.waitKey(1)

        if key == 32:  # SPACE
            if len(faces) > 0:
                x,y,w,h  = faces[0]
                face_img = frame[y:y+h, x:x+w]
                img_path = os.path.join(student_folder, f"{count+1}.jpg")
                cv2.imwrite(img_path, face_img)
                count += 1
                print(f"  Photo {count}/5 saved!")
            else:
                print("  No face detected — move closer!")
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if count == 5:
        print(f"\nSUCCESS! {name} registered with 5 photos! (ID: {student_id})")
    else:
        print(f"\nOnly {count} photos captured.")

if __name__ == "__main__":
    while True:
        register_student()
        again = input("\nRegister another? (yes/no): ").strip().lower()
        if again != 'yes':
            break
    print("\nDone! Run python app.py to start the system.")
