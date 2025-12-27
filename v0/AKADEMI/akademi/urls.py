"""
Akademi Django Projesi - URL Configuration
==========================================

Bu dosya mayscon.v1 projesinin config/urls modülünden
URL yapılandırmasını kalıtım olarak alır ve akademi'ye
özel URL'leri ekler.

Kalıtım Yapısı:
--------------
mayscon.v1/config/urls/
├── base.py         → Temel URL utilities
├── health.py       → Health check endpoints
├── i18n.py         → Dil değiştirme
├── admin.py        → Admin panel
├── auth.py         → Authentication
├── api/            → REST API endpoints
├── webapp.py       → Frontend URL'leri
├── static.py       → Static/Media (dev only)
└── debug.py        → Debug toolbar (dev only)

Kullanım:
--------
ROOT_URLCONF = 'akademi.urls'
"""

import sys
from pathlib import Path
from django.contrib import admin
from django.urls import path, include

# =============================================================================
# MAYSCON.V1 PATH CONFIGURATION
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MAYSCON_V1_PATH = BASE_DIR.parent / 'MAYSCON' / 'mayscon.v1'

if str(MAYSCON_V1_PATH) not in sys.path:
    sys.path.insert(0, str(MAYSCON_V1_PATH))

# =============================================================================
# AKADEMI API URL PATTERNS (ÖNCELİKLİ)
# =============================================================================
# Akademi backend API endpoint'leri - MAYSCON'dan önce tanımlanmalı
# böylece akademi'nin custom view'ları kullanılır

from backend.tenants.views import MyTenantView

from backend.courses.views import EnrollmentViewSet
from rest_framework.routers import DefaultRouter

# Enrollment router - for /api/v1/enrollments/
enrollment_router = DefaultRouter()
enrollment_router.register('', EnrollmentViewSet, basename='enrollment')

# Phase 2 URL imports
from backend.notes.urls import content_urlpatterns as notes_content_urls
from backend.ai.urls import content_urlpatterns as ai_content_urls

# Akademi URL'leri - ÖNCE tanımlanır (override için)
urlpatterns = [
    # Auth API - JWT Authentication (Frontend expects /api/v1/auth/...)
    # Custom view'lar kullanılır (login audit log için)
    path('api/v1/auth/', include('backend.users.auth_urls', namespace='auth')),
    
    # Users API - User CRUD
    path('api/v1/users/', include('backend.users.urls', namespace='users')),
    
    # Tenants API - Akademi/Kurum Yönetimi
    path('api/v1/tenants/', include('backend.tenants.urls', namespace='tenants')),
    
    # My Tenant - Kullanıcının mevcut akademisi
    path('api/v1/my-tenant/', MyTenantView.as_view({'get': 'list'}), name='my-tenant'),
    
    # Courses API - Kurs Yönetimi
    path('api/v1/courses/', include('backend.courses.urls', namespace='courses')),
    
    # Enrollments API - Direct access (Frontend expects /api/v1/enrollments/)
    path('api/v1/enrollments/', include(enrollment_router.urls)),
    
    # Instructor API - Eğitmen Dashboard, Sınıflar, Öğrenciler, Değerlendirmeler
    path('api/v1/instructor/', include('backend.instructor.urls', namespace='instructor')),
    
    # Admin API - Loglar, Finans, Canlı Yayınlar (Global)
    path('api/v1/admin/', include('backend.admin_api.urls', namespace='admin_api')),
    
    # Student API - Öğrenci Modülü (Sınıflar, Ödevler, Canlı Dersler, Bildirimler)
    path('api/v1/student/', include('backend.student.urls', namespace='student')),
    
    # =========================================================================
    # COURSE PLAYER API (Phase 1)
    # =========================================================================
    # Player API - Playback Session Yönetimi
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/sessions/',
         include('backend.player.urls', namespace='player')),
    
    # Progress API - Video İlerleme Takibi
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/progress/',
         include('backend.progress.urls', namespace='progress')),
    
    # Telemetry API - Event Tracking
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/events/',
         include('backend.telemetry.urls', namespace='telemetry')),
    
    # Sequencing API - İçerik Kilitleme
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/lock/',
         include('backend.sequencing.urls', namespace='sequencing')),
    
    # Quizzes API - Quiz Sistemi
    path('api/v1/quizzes/', include('backend.quizzes.urls', namespace='quizzes')),
    
    # =========================================================================
    # COURSE PLAYER API (Phase 2)
    # =========================================================================
    # Timeline API - Overlay Nodes
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/timeline/',
         include('backend.timeline.urls', namespace='timeline')),
    
    # Notes API - Zamanlı Notlar (Content scoped)
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/',
         include((notes_content_urls, 'notes_content'))),
    
    # Notes API - Global (Export, Shared)
    path('api/v1/notes/', include('backend.notes.urls', namespace='notes')),
    
    # AI API - Transcript, Chat, Summary (Content scoped)
    path('api/v1/courses/<int:course_id>/content/<int:content_id>/',
         include((ai_content_urls, 'ai_content'))),
    
    # AI API - Global (Conversations, Quota)
    path('api/v1/ai/', include('backend.ai.urls', namespace='ai')),
    
    # =========================================================================
    # COURSE PLAYER API (Phase 3)
    # =========================================================================
    # Recommendations API - Kişiselleştirilmiş Öneriler
    path('api/v1/recommendations/', include('backend.recommendations.urls', namespace='recommendations')),
    
    # Integrity API - Bütünlük Kontrolü
    path('api/v1/integrity/', include('backend.integrity.urls', namespace='integrity')),
    
    # =========================================================================
    # STORAGE API (Dosya Yükleme)
    # =========================================================================
    # Storage API - Dosya yükleme, profil resimleri, ödev dosyaları, materyaller
    path('api/v1/storage/', include('backend.storage.urls', namespace='storage')),
    
    # =========================================================================
    # CERTIFICATES API (Sertifikalar)
    # =========================================================================
    # Certificates API - Sertifika oluşturma, doğrulama, PDF indirme
    path('api/v1/certificates/', include('backend.certificates.urls', namespace='certificates')),
    
    # =========================================================================
    # REALTIME API (Mesajlaşma & Bildirimler)
    # =========================================================================
    # Mesajlaşma API - Konuşmalar, mesajlar
    path('api/v1/messages/', include('backend.realtime.urls', namespace='realtime')),
    
    # =========================================================================
    # LIVE SESSION API (Canlı Dersler)
    # =========================================================================
    # Canlı ders yönetimi - oturumlar, kayıtlar, yoklama
    path('api/v1/live-sessions/', include('backend.live.urls', namespace='live')),
    
]

# =============================================================================
# MAYSCON.V1 URL PATTERNS'DEN KALITIM
# =============================================================================
# Temel URL pattern'ları mayscon.v1'den al (akademi URL'lerinden SONRA)
try:
    from config.urls import urlpatterns as base_urlpatterns
    urlpatterns += list(base_urlpatterns)
except ImportError:
    # Fallback: Temel admin URL'i
    urlpatterns += [
        path('admin/', admin.site.urls),
    ]

# =============================================================================
# AKADEMI NAMESPACE'LERİ
# =============================================================================
"""
Akademi URL Yapısı
==================

Kalıtım ile gelen (mayscon.v1):
-----------------------------
/admin/                     → Django Admin
/health/                    → Health check
/api/v1/                    → REST API
/accounts/                  → Authentication
/logs/                      → Log viewer

Akademi API Endpoint'leri:
-------------------------
/api/v1/auth/token/        → JWT Login
/api/v1/auth/refresh/      → Token Refresh
/api/v1/auth/register/     → Kayıt
/api/v1/auth/me/           → Mevcut Kullanıcı
/api/v1/users/             → Kullanıcı CRUD
/api/v1/tenants/           → Akademi CRUD
/api/v1/my-tenant/         → Kullanıcının Akademisi
/api/v1/courses/           → Kurs CRUD
/api/v1/enrollments/       → Kayıt CRUD
/api/v1/docs/              → Swagger UI
/api/v1/redoc/             → ReDoc

Instructor API (Eğitmen):
-------------------------
/api/v1/instructor/dashboard/              → Eğitmen Dashboard
/api/v1/instructor/classes/                → Eğitmenin Sınıfları
/api/v1/instructor/students/               → Eğitmenin Öğrencileri
/api/v1/instructor/assessments/            → Değerlendirmeler
/api/v1/instructor/behavior/students/      → Öğrenci Davranış Analizi
/api/v1/instructor/behavior/classes/       → Sınıf Performansı
/api/v1/instructor/calendar/               → Takvim

Admin API (Yönetici):
---------------------
/api/v1/admin/logs/tech/                   → Teknik Loglar
/api/v1/admin/logs/activity/               → Aktivite Logları
/api/v1/admin/finance/academies/           → Akademi Finansları
/api/v1/admin/finance/categories/          → Kategori Gelirleri
/api/v1/admin/finance/instructors/         → Eğitmen Kazançları
/api/v1/admin/live-sessions/               → Global Canlı Yayınlar
"""
