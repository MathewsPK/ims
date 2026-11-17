"""
Django settings for IMS (Internal Management System) project.
"""
from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local .env file into the process environment, if
# present. Needed because nothing else does this on Linux/systemd — run.bat
# does its own parsing on Windows, but a systemd service or a plain SSH shell
# never reads .env automatically. Real environment variables (e.g. ones set
# by systemd's EnvironmentFile=) always take priority over .env.
def _load_dotenv(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(BASE_DIR / '.env')

# SECURITY
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production-xyz123')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']  # Allows all hosts — fine for LAN/local deployment and simple online hosting

# CSRF: list every origin that can POST to this server.
# run.bat auto-populates this from the detected LAN IP.
# In production, set CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com (or your domain) in the host's env vars.
_csrf_default = 'http://localhost:8000,http://127.0.0.1:8000'
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', _csrf_default).split(',')
    if o.strip()
]

# Tender Radar: folder of the separate tender_radar project (has pyproject.toml).
# The "Search now & email" button runs <TENDER_RADAR_DIR>/.venv/.../tender-radar unless
# TENDER_RADAR_CMD gives the full path to that executable.
TENDER_RADAR_DIR = os.environ.get('TENDER_RADAR_DIR', '')
TENDER_RADAR_CMD = os.environ.get('TENDER_RADAR_CMD', '')

# Secret shared with an external cron pinger (Render Cron Job, GitHub Actions,
# cron-job.org) that hits /billing/cron/check-renewals/?token=... once a day.
CRON_SECRET = os.environ.get('CRON_SECRET', '')

# Behind a reverse proxy (Render, Railway, etc.) requests arrive over plain
# HTTP internally; this tells Django to trust the proxy's X-Forwarded-Proto
# header so HTTPS detection, secure cookies, and redirects work correctly.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'import_export',

    # Local apps
    'users',
    'core',
    'projects',
    'tasks',
    'amc',
    'expenses',
    'billing',
    'reports',
    'notifications',
    'dashboard',
    'tenders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database — SQLite by default; set USE_POSTGRES=True in .env to switch,
# or (on a host like Render/Railway) just set DATABASE_URL and it takes over.
USE_POSTGRES = os.environ.get('USE_POSTGRES', 'False') == 'True'
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG)
    }
elif USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'ims'),
            'USER': os.environ.get('DB_USER', 'ims'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Authentication backends - email login
AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/users/login/'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# I18n
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# CORS (for optional React frontend)
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Email (console backend for dev; swap to SMTP in prod)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@ims.local')

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Session
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True
