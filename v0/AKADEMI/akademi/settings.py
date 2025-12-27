"""
Akademi Django Projesi - Settings
=================================

Bu dosya mayscon.v1 projesinin config/settings modülünden
tüm ayarları kalıtım olarak alır ve akademi'ye özel
override'ları uygular.

Kalıtım Yapısı:
--------------
mayscon.v1/config/settings/
├── env.py              → Environment değişkenleri
├── base.py             → Temel ayarlar
├── security.py         → Güvenlik
├── apps.py             → INSTALLED_APPS
├── middleware.py       → MIDDLEWARE
├── templates.py        → TEMPLATES
├── static.py           → Static/Media
├── data/               → Database (modüler)
│   ├── base.py         → Ortak DB ayarları
│   ├── mayscon.py      → MAYSCON DB
│   └── akademi.py      → AKADEMI DB
├── cache.py            → Cache
├── auth.py             → Authentication
├── i18n.py             → Internationalization
├── logging/            → Logging (modüler)
│   ├── base.py         → Ortak log ayarları
│   ├── mayscon.py      → MAYSCON logging
│   └── akademi.py      → AKADEMI logging
├── dev.py              → Development override
└── prod.py             → Production override

Kullanım:
--------
DJANGO_SETTINGS_MODULE=akademi.settings
"""

import sys
from pathlib import Path

# =============================================================================
# AKADEMI BASE DIRECTORY
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# MAYSCON.V1 PATH CONFIGURATION
# =============================================================================
# mayscon.v1 projesinin yolunu Python path'ine ekle
MAYSCON_V1_PATH = BASE_DIR.parent / 'MAYSCON' / 'mayscon.v1'

if str(MAYSCON_V1_PATH) not in sys.path:
    sys.path.insert(0, str(MAYSCON_V1_PATH))

# =============================================================================
# MAYSCON.V1 SETTINGS'DEN KALITIM
# =============================================================================
# Tüm ayarları mayscon.v1'den al (database ve logging hariç - modüler yapı)
from config.settings import *  # pyright: ignore[reportMissingImports]

# =============================================================================
# AKADEMI-SPECIFIC OVERRIDES
# =============================================================================
# Akademi projesine özel ayarlar burada tanımlanır

# Base directory'yi akademi için güncelle
BASE_DIR = Path(__file__).resolve().parent.parent

# URL yapılandırması
ROOT_URLCONF = 'akademi.urls'

# WSGI/ASGI uygulamaları
WSGI_APPLICATION = 'akademi.wsgi.application'
ASGI_APPLICATION = 'akademi.asgi.application'

# =============================================================================
# ADMIN PANEL BAŞLIKLARI
# =============================================================================
ADMIN_SITE_HEADER = "Akademi Yönetim Paneli"
ADMIN_SITE_TITLE = "Akademi Admin"
ADMIN_INDEX_TITLE = "Akademi Yönetim"

# =============================================================================
# CUSTOM USER MODEL
# =============================================================================
# Akademi özel User modeli
AUTH_USER_MODEL = 'users.User'

# =============================================================================
# AKADEMI UYGULAMALARI
# =============================================================================
# Akademi'ye özel backend uygulamaları
INSTALLED_APPS += [
    'backend.users',
    'backend.tenants',
    'backend.courses',
    'backend.instructor',
    'backend.admin_api',
    'backend.student',
    # Course Player modülleri (Phase 1)
    'backend.player',
    'backend.progress',
    'backend.telemetry',
    'backend.sequencing',
    'backend.quizzes',
    # Course Player modülleri (Phase 2)
    'backend.timeline',
    'backend.notes',
    'backend.ai',
    # Course Player modülleri (Phase 3)
    'backend.recommendations',
    'backend.integrity',
    # Storage modülü
    'backend.storage',
    # Sertifika modülü
    'backend.certificates',
    # Gerçek zamanlı iletişim modülü
    'backend.realtime',
    # Canlı ders modülü
    'backend.live',
]

# =============================================================================
# DJANGO CHANNELS (WebSocket)
# =============================================================================
# Channels layer için Redis kullan
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST if 'REDIS_HOST' in dir() else 'localhost', 6379)],
        },
    },
}

# ASGI application
ASGI_APPLICATION = 'akademi.asgi.application'

# =============================================================================
# JWT CUSTOM SERIALIZER
# =============================================================================
# Token'a kullanıcı bilgileri ekleyen custom serializer
SIMPLE_JWT['TOKEN_OBTAIN_SERIALIZER'] = 'backend.users.serializers.CustomTokenObtainPairSerializer'  # pyright: ignore

# =============================================================================
# AUDIT MIDDLEWARE (Kullanıcı Aktivite Takibi)
# =============================================================================
# Audit Middleware'i aktif et
MIDDLEWARE += [
    'logs.audit.middleware.AuditMiddleware',
]

# Audit ayarları
AUDIT_MIDDLEWARE_ENABLED = True
AUDIT_PATHS = ['/api/', '/admin/']  # Bu path'lerdeki istekleri logla
AUDIT_EXCLUDE_PATHS = [
    '/api/v1/auth/token/refresh/',  # Token refresh'i hariç tut (çok sık)
    '/static/',
    '/media/',
    '/favicon.ico',
    '/health/',
    '/ready/',
    '/live/',
]
AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Bu HTTP metodlarını logla

# =============================================================================
# STATIC & MEDIA (MAYSCON Webapp'tan kalıtım)
# =============================================================================
# MAYSCON webapp dizinlerini kullan - merkezi yönetim
MAYSCON_WEBAPP_DIR = MAYSCON_V1_PATH / 'webapp'

STATICFILES_DIRS = [
    MAYSCON_WEBAPP_DIR / 'static',
]
STATIC_ROOT = MAYSCON_V1_PATH / 'staticfiles'
MEDIA_ROOT = MAYSCON_WEBAPP_DIR / 'media'

# =============================================================================
# TEMPLATES (MAYSCON Webapp'tan kalıtım)
# =============================================================================
# MAYSCON webapp template dizinlerini kullan
TEMPLATES[0]['DIRS'] = [  # pyright: ignore[reportUndefinedVariable]
    MAYSCON_WEBAPP_DIR / 'templates',
]

# =============================================================================
# DATABASE CONFIGURATION - AKADEMI MULTI-DATABASE (Modüler)
# =============================================================================
# Veritabanı ayarları config/settings/data/akademi.py modülünden gelir
#
# Veritabanları:
# - default (akademi_primary) : Ana veritabanı (users, tenants, courses)
# - analytics                 : Analitik veritabanı (reports, metrics)
# - logs                      : Log veritabanı (audit, activity logs)
# - media                     : Media veritabanı (dosya metadata, video bilgileri)
#
# Docker ile çalıştırma:
#   cd v0/MAYSCON/mayscon.v1/infra/docker
#   docker-compose --profile akademi up -d

from config.settings.data.akademi import DATABASES, DATABASE_ROUTERS  # pyright: ignore

# =============================================================================
# LOGGING CONFIGURATION - AKADEMI (Modüler)
# =============================================================================
# Logging ayarları config/settings/logging/akademi.py modülünden gelir
#
# Log dosyaları: mayscon.v1/logs/data/akademi/ altında tutulur
# - global.log     : Ana log
# - levels/        : Seviye bazlı loglar (debug, info, warning, error)
# - database/      : SQL logları

from config.settings.logging.akademi import LOGGING, LOG_DIR, LOG_FILES  # pyright: ignore

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================
# Celery için Redis broker ve result backend
CELERY_BROKER_URL = f"redis://{REDIS_HOST if 'REDIS_HOST' in dir() else 'localhost'}:6379/1"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST if 'REDIS_HOST' in dir() else 'localhost'}:6379/2"

# Celery ayarları
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Istanbul'
CELERY_ENABLE_UTC = True

# =============================================================================
# LIVE SESSION CONFIGURATION
# =============================================================================
# Canlı ders modülü ayarları

# Varsayılan provider (jitsi, bbb, zoom)
LIVE_DEFAULT_PROVIDER = 'jitsi'

# Jitsi ayarları (environment'tan al)
import os
JITSI_DOMAIN = os.environ.get('JITSI_DOMAIN', 'meet.localhost')
JITSI_APP_ID = os.environ.get('JITSI_APP_ID', 'edutech')
JITSI_JWT_SECRET = os.environ.get('JITSI_JWT_SECRET', '')

# BBB ayarları
BBB_SERVER_URL = os.environ.get('BBB_SERVER_URL', '')
BBB_SHARED_SECRET = os.environ.get('BBB_SHARED_SECRET', '')

# Live session limitleri
LIVE_MAX_CONCURRENT_ROOMS = int(os.environ.get('LIVE_MAX_CONCURRENT_ROOMS', 10))
LIVE_DEFAULT_DURATION_MINUTES = int(os.environ.get('LIVE_DEFAULT_DURATION_MINUTES', 120))
LIVE_RECORDING_RETENTION_DAYS = int(os.environ.get('LIVE_RECORDING_RETENTION_DAYS', 90))
LIVE_ATTENDANCE_THRESHOLD_PERCENT = int(os.environ.get('LIVE_ATTENDANCE_THRESHOLD_PERCENT', 70))
