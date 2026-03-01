@echo off
cd /d "C:\Users\sasit\Desktop\AttendIQ"
call venv\Scripts\activate.bat
python camera_session.py --session_id %1 --interval %2
pause
