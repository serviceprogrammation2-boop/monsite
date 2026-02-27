# settings.py (version Render optimisée)
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# -----------------------------
# Charger .env local (uniquement en local)
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env.local"))

# -----------------------------
# SECURITY
# -----------------------------
DEBUG = os.environ.get("DEBUG", "True") == "True"

if DEBUG:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-1234567890")
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
else:
    SECRET_KEY = os.environ["SECRET_KEY"]
    ALLOWED_HOSTS = ["monsite-vh4i.onrender.com"]

# Pour que la redirection login fonctionne
LOGIN_URL = "/admin/login/"

# -----------------------------
# INSTALLED APPS
# -----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tes apps
    'blog',
    'rangefilter',
    'background_task',
]

# -----------------------------
# DATABASES
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL or "postgres://user:password@127.0.0.1:5432/nomdb_local",
        conn_max_age=600,
        ssl_require=not DEBUG
    )
}

# SSL options pour prod
if not DEBUG:
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}
else:
    DATABASES["default"]["OPTIONS"] = {"sslmode": "disable"}

# -----------------------------
# MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "monsite.urls"

# -----------------------------
# TEMPLATES
# -----------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # ⚡ indispensable pour admin
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "monsite.wsgi.application"

# -----------------------------
# STATIC & MEDIA
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# settings.py
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'