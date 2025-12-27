"""
Student URLs
============

Öğrenci modülü URL'leri.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    StudentAssignmentViewSet,
    StudentClassViewSet,
    StudentLiveSessionViewSet,
    StudentMessageViewSet,
    StudentNotificationViewSet,
    StudentSupportViewSet,
)

app_name = 'student'

router = DefaultRouter()
router.register('classes', StudentClassViewSet, basename='class')
router.register('assignments', StudentAssignmentViewSet, basename='assignment')
router.register('live-sessions', StudentLiveSessionViewSet, basename='live-session')
router.register('notifications', StudentNotificationViewSet, basename='notification')
router.register('messages', StudentMessageViewSet, basename='message')
router.register('support', StudentSupportViewSet, basename='support')

urlpatterns = [
    path('', include(router.urls)),
]

