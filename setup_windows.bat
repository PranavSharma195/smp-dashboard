@echo off
REM One-time setup for Windows. Usage: setup_windows.bat
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo Python 3.10-3.13 not found. Install from https://www.python.org/downloads/ & exit /b 1)
if not exist venv (%PY% -m venv venv || exit /b 1)
call venv\Scripts\activate.bat || exit /b 1
python -m pip install --quiet --upgrade pip || exit /b 1
python -m pip install --quiet -r requirements.txt || exit /b 1
if not exist static\vendor mkdir static\vendor
if not exist static\vendor\gsap.min.js curl -fsSL -o static\vendor\gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js
if not exist static\vendor\chart.umd.min.js curl -fsSL -o static\vendor\chart.umd.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js
python manage.py migrate --noinput || exit /b 1
python manage.py ensure_demo_user || exit /b 1
python manage.py seed_products || exit /b 1
python manage.py check || exit /b 1
python manage.py test --verbosity 1 || exit /b 1
echo.
echo Done. Start with run_windows.bat then open http://127.0.0.1:8000/  (login: manab / manab123, demo only)
