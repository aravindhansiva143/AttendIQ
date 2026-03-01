import cv2, os

# Read face folder path from file (avoids path escaping issues)
with open(r"C:\Users\sasit\Desktop\AttendIQ\_face_path.txt", encoding='utf-8') as f:
    face_folder = f.read().strip()

name = "arav"
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
print(f"  Face Registration: {name}")
print(f"  SPACE = capture photo")
print(f"  Q = quit")
print(f"  Need {needed} photos")
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
    cv2.putText(frame, f"{name}  |  Photos: {count}/{needed}", (10,22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,180), 2)
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
            img_path = os.path.join(face_folder, f"{count+1}.jpg")
            cv2.imwrite(img_path, frame[y:y+h, x:x+w])
            count += 1
            print(f"  Photo {count}/{needed} saved!")
        else:
            print("  No face detected! Move closer.")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\nDone! {count} photos saved for {name}")
input("\nPress Enter to close this window...")
