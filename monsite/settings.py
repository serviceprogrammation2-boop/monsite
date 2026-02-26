# settings.py
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# -----------------------------
# 🔹 Charger .env local (uniquement en local)
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env.local"))

# -----------------------------
# 🔐 SECURITY
# -----------------------------
DEBUG = os.environ.get("DEBUG", "True") == "True"

if DEBUG:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-1234567890")
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
else:
    SECRET_KEY = os.environ["SECRET_KEY"]  # obligatoire en prod
    ALLOWED_HOSTS = ["monsite-vh4i.onrender.com"]

# -----------------------------
# 📦 INSTALLED APPS
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
# 🗄 DATABASES
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL or "postgres://user:password@127.0.0.1:5432/nomdb_local",
        conn_max_age=600,
        ssl_require=not DEBUG  # SSL uniquement si prod
    )
}

# ⚡ Options supplémentaires pour PostgreSQL
if not DEBUG:
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}
else:
    DATABASES["default"]["OPTIONS"] = {"sslmode": "disable"}

# -----------------------------
# 🌐 ALLOWED HOSTS / OTHER SETTINGS
# -----------------------------
# Par défaut, déjà géré ci-dessus

# -----------------------------
# ⚡ Autres settings classiques
# -----------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "monsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "monsite.wsgi.application"

# -----------------------------
# 🔹 Static & Media
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Compression et cache pour WhiteNoise
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# -----------------------------
# 🗄 TA BASE ORACLE (SI UTILISÉE)
# -----------------------------
ORACLE_GMAO = {
    'dsn': '10.2.2.2:1521/ORCL',
    'user': 'gmao',
    'password': 'gm',
}
