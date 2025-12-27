"""
Certificate URLs
================

Sertifika API endpoint'leri.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateViewSet,
    CertificateVerifyView,
    MyCertificatesView,
    CertificateTemplateViewSet,
    CheckEligibilityView,
)

app_name = 'certificates'

router = DefaultRouter()
router.register(r'', CertificateViewSet, basename='certificate')
router.register(r'templates', CertificateTemplateViewSet, basename='template')

urlpatterns = [
    # Doğrulama (public)
    path('verify/<str:verification_code>/', CertificateVerifyView.as_view(), name='verify'),
    
    # Kullanıcının sertifikaları
    path('my/', MyCertificatesView.as_view(), name='my-certificates'),
    
    # Uygunluk kontrolü
    path('check/<int:enrollment_id>/', CheckEligibilityView.as_view(), name='check-eligibility'),
    
    # Router endpoints
    path('', include(router.urls)),
]

