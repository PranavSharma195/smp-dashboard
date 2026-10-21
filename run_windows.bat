@echo off
cd /d "%~dp0"
if not exist venv (echo Run setup_windows.bat first. & exit /b 1)
call venv\Scripts\activate.bat
echo SMP Dashboard: http://127.0.0.1:8000/  (Ctrl+C to stop)
python manage.py runserver 127.0.0.1:8000
