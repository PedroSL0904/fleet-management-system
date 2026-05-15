from pathlib import Path
from typing import Any

# ==========================================
# CORE DIRECTORIES
# ==========================================
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# SECURITY & ENVIRONMENT
# ==========================================
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-w9k4-573lm0#^u1h^owy13t9m@xt-4#620-(y_!bxrr5&d@(ft'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Explicitly typed for Pylance compliance
ALLOWED_HOSTS: list[str] = []


# ==========================================
# APPLICATION DEFINITION
# ==========================================
INSTALLED_APPS: list[str] = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Internal Project Apps
    'control_vehicular',
]

MIDDLEWARE: list[str] = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema_flotilla.urls'

# Explicitly typed to resolve Pylance reportUnknownVariableType warnings
TEMPLATES: list[dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # Custom Global Context Processors for FleetPro
                'control_vehicular.context_processors.alertas_globales',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_flotilla.wsgi.application'


# ==========================================
# DATABASE CONFIGURATION
# ==========================================
# Explicitly typed to resolve Pylance reportUnknownVariableType warnings
DATABASES: dict[str, dict[str, Any]] = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ==========================================
# PASSWORD VALIDATION
# ==========================================
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==========================================
# INTERNATIONALIZATION & LOCALIZATION
# ==========================================
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True


# ==========================================
# STATIC & MEDIA FILES HANDLING
# ==========================================
STATIC_URL = 'static/'

# Media files configuration for user-uploaded content (e.g., photos, PDFs)
MEDIA_URL = '/media/'
# Modern Pathlib implementation, replacing the legacy os.path.join
MEDIA_ROOT = BASE_DIR / 'media'


# ==========================================
# AUTHENTICATION ROUTING
# ==========================================
LOGIN_REDIRECT_URL = '/'

# ==========================================
# EMAIL CONFIGURATION
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'pedrolucio.0904@gmail.com'      
EMAIL_HOST_PASSWORD = 'yxwd uhoa ekqk tlnj'       
DEFAULT_FROM_EMAIL = 'FleetPro <pedrolucio.0904@gmail.com>'