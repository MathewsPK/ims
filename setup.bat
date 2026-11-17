@echo off
setlocal enabledelayedexpansion

:: ── Always run from the folder this script lives in ──────────────────────────
cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════╗
echo ║   IMS — Internal Management System Setup       ║
echo ║   Windows Setup Script                         ║
echo ╚════════════════════════════════════════════════╝
echo.

:: ── Check Python ────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo [OK] Python found:
python --version

:: ── Create virtual environment ───────────────────────────────────────────────
if not exist ".venv" (
    echo.
    echo [1/6] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: ── Install dependencies ─────────────────────────────────────────────────────
echo.
echo [2/6] Installing dependencies (this may take a minute)...
.venv\Scripts\pip install --quiet --upgrade pip
.venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: ── Create .env if missing ───────────────────────────────────────────────────
if not exist ".env" (
    echo.
    echo [3/6] Creating .env file...
    (
        echo SECRET_KEY=change-this-in-production-use-a-long-random-string
        echo DEBUG=True
        echo USE_POSTGRES=False
    ) > .env
    echo [OK] .env file created.
) else (
    echo [OK] .env file already exists.
)

:: ── Run migrations ───────────────────────────────────────────────────────────
echo.
echo [4/6] Running database migrations...
.venv\Scripts\python manage.py makemigrations users core projects tasks amc expenses reports notifications --no-input 2>nul
.venv\Scripts\python manage.py migrate --no-input
if errorlevel 1 (
    echo [ERROR] Migration failed.
    pause
    exit /b 1
)
echo [OK] Database ready.

:: ── Ensure admin account (fresh installs only — never touches existing data) ─
echo.
echo [5/6] Checking admin account...
.venv\Scripts\python manage.py ensure_admin
.venv\Scripts\python manage.py load_holidays
echo [OK] Admin account ready.

:: ── Detect LAN IP ────────────────────────────────────────────────────────────
set "LOCAL_IP=127.0.0.1"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
    set "LOCAL_IP=%%A"
    set "LOCAL_IP=!LOCAL_IP: =!"
    goto :ip_found
)
:ip_found
set "CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://%LOCAL_IP%:8000"

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo ╔════════════════════════════════════════════════╗
echo ║   Setup complete!                              ║
echo ║                                                ║
echo ║   Fresh install? Login with:                   ║
echo ║   admin@ims.local / admin123                   ║
echo ║   (change the password after first login)      ║
echo ║                                                ║
echo ║   [6/6] Starting server...                     ║
echo ║   Local  : http://127.0.0.1:8000               ║
echo ║   Network: http://%LOCAL_IP%:8000
echo ╚════════════════════════════════════════════════╝
echo.

.venv\Scripts\python manage.py runserver 0.0.0.0:8000

pause
