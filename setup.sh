#!/usr/bin/env bash
# ============================================================
#  IMS — Internal Management System
#  One-command setup: installs, migrates, seeds, and runs
# ============================================================
set -e

PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"
MANAGE="$VENV_DIR/bin/python manage.py"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   IMS — Internal Management System Setup       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# ── 1. Virtual environment ──────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "📦  Creating virtual environment…"
  $PYTHON -m venv "$VENV_DIR"
fi

echo "📦  Installing dependencies…"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

# ── 2. Environment file ─────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "⚙️   Creating .env file…"
  cat > .env << 'ENVEOF'
SECRET_KEY=change-this-in-production-use-a-long-random-string
DEBUG=True
USE_POSTGRES=False
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_HOST_USER=you@gmail.com
# EMAIL_HOST_PASSWORD=app-specific-password
ENVEOF
fi

# ── 3. Migrations ───────────────────────────────────────────
echo "🗄️   Running database migrations…"
$MANAGE makemigrations users core projects tasks amc expenses reports notifications dashboard --no-input 2>/dev/null || true
$MANAGE migrate --no-input

# ── 4. Static files ─────────────────────────────────────────
echo "🎨  Collecting static files…"
$MANAGE collectstatic --no-input --clear 2>/dev/null || true

# ── 5. Admin account (fresh installs only) ─────────────────
echo "👤  Checking admin account…"
$MANAGE ensure_admin
$MANAGE load_holidays

# ── Detect LAN IP ──────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="127.0.0.1"
export CSRF_TRUSTED_ORIGINS="http://127.0.0.1:8000,http://localhost:8000,http://${LOCAL_IP}:8000"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   Setup complete!                              ║"
echo "║                                                ║"
echo "║   Fresh install? Login with:                   ║"
echo "║   ▸ admin@ims.local / admin123                 ║"
echo "║   (change the password after first login)      ║"
echo "║                                                ║"
echo "║   Local  : http://127.0.0.1:8000               ║"
echo "║   Network: http://${LOCAL_IP}:8000             ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

$MANAGE runserver 0.0.0.0:8000
