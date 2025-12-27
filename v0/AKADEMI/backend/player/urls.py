"""
Player URL Configuration
========================

Playback session API endpoint'leri.

URL Pattern:
    /api/v1/courses/{courseId}/content/{contentId}/sessions/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PlaybackSessionViewSet

app_name = 'player'

# Router oluştur
router = DefaultRouter()
router.register('', PlaybackSessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]

