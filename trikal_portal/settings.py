"""
Django settings for trikal_portal project.
"""
import os
import sys
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-_(1@ran2op0v^mhq@2zun67n$3&*9+t8gfvv(ayi_5%(q4%*yi'

DEBUG = True
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',  # आपका मुख्य ऐप
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'trikal_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'trikal_portal.wsgi.application'

# ==========================================
# Database Configuration
# ==========================================

# Render Database URL
RENDER_DB_URL = "postgresql://trikal_user:pS1IvOdD0g1u225MPYBDXCtO3mblzAFk@dpg-d88sd20js32c73a08bb0-a.singapore-postgres.render.com/trikal"

# चेक करें कि क्या कोड मोबाइल (Pydroid) पर चल रहा है
IS_PYDROID = 'pydroid3' in sys.executable or 'ru.iiec.pydroid3' in sys.prefix

if IS_PYDROID:
    # 1. Pydroid के लिए लोकल SQLite डेटाबेस
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # 2. Render (Live Server) के लिए PostgreSQL डेटाबेस
    DATABASES = {
        'default': dj_database_url.config(
            default=RENDER_DB_URL,
            conn_max_age=0,
            conn_health_checks=True,
        )
    }

# ==========================================
# Password Validation
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==========================================
# Static files (CSS, JavaScript, Images)
# ==========================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# ==========================================
# Email Configuration for Live Alerts
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True  # Port 465 के लिए TLS की जगह SSL का इस्तेमाल सही रहता है
EMAIL_HOST_USER = 'nileshdave1511@gmail.com'
EMAIL_HOST_PASSWORD = 'wqqy hqwd vwnz thby'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
