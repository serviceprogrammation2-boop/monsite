"""
Django settings for monsite project.
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------
# 🔐 SECURITY
# -----------------------------
SECRET_KEY = 'django-insecure-nq*4!rks9o563=9w^h1obi38rzml$adrnavm+x%0q4u4!q&+mz'
DEBUG = True     # Mets False ensuite pour la production Render

# Render accepte tous les domaines du service
ALLOWED_HOSTS = ['*']


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
    'core',
    'rangefilter',
    'background_task',
]


# -----------------------------
# ⚙️ MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ OBLIGATOIRE POUR LES STATIC FILES SUR RENDER
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]



ROOT_URLCONF = 'monsite.urls'


# -----------------------------
# 🎨 TEMPLATES
# -----------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],            # tu peux mettre tes templates ici
        'APP_DIRS': True,      # DOIT être True
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'monsite.wsgi.application'


# -----------------------------
# 🗄 DATABASE (Render PostgreSQL)
# -----------------------------
import dj_database_url
import os

DEBUG = True  # TEMPORAIRE pour voir les erreurs

ALLOWED_HOSTS = [
    "monsite-vh4i.onrender.com",
    "localhost",
    "127.0.0.1",
]


# Database PostgreSQL via DATABASE_URL fourni par Render
DATABASES = {
    'default': dj_database_url.config(default=os.environ.get('DATABASE_URL'))
}

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise (OBLIGATOIRE sur Render)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"



# -----------------------------
# 🔐 PASSWORD VALIDATION
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -----------------------------
# 🌍 INTERNATIONALIZATION
# -----------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# -----------------------------
# 🖼 STATIC FILES (IMPORTANT POUR RENDER)
# -----------------------------
STATIC_URL = '/static/'

# Dossier où Render rassemble les fichiers (collectstatic)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# -----------------------------
# 🔑 DEFAULT PRIMARY KEY
# -----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -----------------------------
# 🗄 TA BASE ORACLE (SI UTILISÉE)
# -----------------------------
ORACLE_GMAO = {
    'dsn': '10.2.2.2:1521/ORCL',
    'user': 'gmao',
    'password': 'gm',
}
