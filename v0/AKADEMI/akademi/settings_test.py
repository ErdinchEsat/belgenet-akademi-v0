"""
Akademi Test Settings
=====================

Test ortamı için özelleştirilmiş Django ayarları.
Docker'da PostgreSQL, local'de SQLite kullanır.

Kullanım:
    DJANGO_SETTINGS_MODULE=akademi.settings_test pytest tests/akademi/ -v
"""

import os
import sys
from pathlib import Path

# =============================================================================
# PATH CONFIGURATION
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MAYSCON_V1_PATH = BASE_DIR.parent / 'MAYSCON' / 'mayscon.v1'

if str(MAYSCON_V1_PATH) not in sys.path:
    sys.path.insert(0, str(MAYSCON_V1_PATH))

# =============================================================================
# IMPORT BASE SETTINGS (simplified for tests)
# =============================================================================
# Sadece gerekli temel ayarları al, karmaşık startup'ı atla
from config.settings.env import config

# Secret key
SECRET_KEY = 'test-secret-key-not-for-production-use-only'

# Debug kapalı
DEBUG = False

# Allowed hosts
ALLOWED_HOSTS = ['*']

# =============================================================================
# INSTALLED APPS (Test için minimal)
# =============================================================================
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    
    # Akademi apps
    'backend.users',
    'backend.tenants',
    'backend.courses',
    'backend.instructor',
    'backend.admin_api',
    'backend.student',
    # Course Player modülleri
    'backend.player',
    'backend.progress',
    'backend.telemetry',
    'backend.sequencing',
    'backend.quizzes',
    # Phase 2
    'backend.timeline',
    'backend.notes',
    'backend.ai',
    # Phase 3
    'backend.recommendations',
    'backend.integrity',
    # Storage & Certificates
    'backend.storage',
    'backend.certificates',
    # Realtime & Live
    'backend.realtime',
    'backend.live',
    
    # Logs
    'logs.audit',
    'logs.analytics',
]

# =============================================================================
# MIDDLEWARE (Test için minimal)
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# =============================================================================
# DATABASE
# =============================================================================
# Docker modunda PostgreSQL, local'de SQLite
DOCKER_MODE = config('DOCKER_MODE', default=False, cast=bool)

if DOCKER_MODE:
    # Docker: PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('AKADEMI_DB_PRIMARY_NAME', default='akademi_test'),
            'USER': config('AKADEMI_DB_USER', default='akademi'),
            'PASSWORD': config('AKADEMI_DB_PASSWORD', default='akademi_secret_2024'),
            'HOST': config('AKADEMI_DB_PRIMARY_HOST', default='test-db'),
            'PORT': config('AKADEMI_DB_PRIMARY_PORT', default='5432'),
            'CONN_MAX_AGE': 0,
            'TEST': {
                'NAME': 'test_akademi',
            },
        }
    }
else:
    # Local: SQLite in-memory
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }

# =============================================================================
# AUTH
# =============================================================================
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = []  # Test için validasyon yok

# Hızlı password hasher
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# =============================================================================
# JWT
# =============================================================================
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# =============================================================================
# URLS
# =============================================================================
ROOT_URLCONF = 'akademi.urls'

# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
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
            ],
        },
    },
]

# =============================================================================
# STATIC & MEDIA
# =============================================================================
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# =============================================================================
# CACHE
# =============================================================================
if DOCKER_MODE:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://test-redis:6379/0'),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# =============================================================================
# CELERY
# =============================================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# EMAIL
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# =============================================================================
# LOGGING (Minimal)
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# =============================================================================
# DEFAULT AUTO FIELD
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
