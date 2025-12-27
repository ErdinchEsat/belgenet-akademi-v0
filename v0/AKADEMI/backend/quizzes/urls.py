"""
Quizzes URL Configuration
=========================

Quiz API endpoint'leri.

URL Pattern:
    /api/v1/quizzes/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import QuizViewSet

app_name = 'quizzes'

router = DefaultRouter()
router.register('', QuizViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
]

