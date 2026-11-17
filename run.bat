@echo off
setlocal enabledelayedexpansion

:: ── Always run from the folder this script lives in ──────────────────────────
cd /d "%~dp0"

:: ── Check if running as Administrator ────────────────────────────────────────
net session >nul 2>&1
set "IS_ADMIN=0"
if not errorlevel 1 set "IS_ADMIN=1"

:: ── Load .env file into environment ─────────────────────────────────────────
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%B"=="" (
            set "%%A=%%B"
        )
    )
)

:: ── LAN IP — auto-detected from ipconfig ─────────────────────────────────────
set "LOCAL_IP=127.0.0.1"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R "IPv4 Address"') do (
    set "CANDIDATE=%%A"
    set "CANDIDATE=!CANDIDATE: =!"
    if not "!CANDIDATE!"=="127.0.0.1" (
        set "LOCAL_IP=!CANDIDATE!"
        goto :ip_done
    )
)
:ip_done

:: ── Set CSRF trusted origins so LAN devices can POST forms ───────────────────
set "CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://%LOCAL_IP%:8000"

:: ── Open Windows Firewall for port 8000 (no admin needed for port 8000) ──────
netsh advfirewall firewall show rule name="IMS Django Port 8000" >nul 2>&1
if errorlevel 1 (
    if "%IS_ADMIN%"=="1" (
        echo  [Firewall] Adding inbound rule for port 8000...
        netsh advfirewall firewall add rule name="IMS Django Port 8000" ^
            protocol=TCP dir=in localport=8000 action=allow profile=any >nul 2>&1
        echo  [Firewall] Done. Other devices on this network can now connect.
    ) else (
        echo.
        echo  NOTE: For first-time setup, right-click run.bat and choose
        echo  "Run as administrator" once to add the firewall rule.
        echo  After that, normal double-click works fine.
        echo.
    )
) else (
    echo  [Firewall] Port 8000 rule OK.
)

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   IMS — Internal Management System                       ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║   This machine  : http://127.0.0.1:8000                  ║
echo  ║   Other devices : http://%LOCAL_IP%:8000
echo  ║                                                          ║
echo  ║   On each office PC open the "Other devices" URL.        ║
echo  ║   Press Ctrl+C here to stop the server.                  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

.venv\Scripts\python manage.py runserver 0.0.0.0:8000
pause
