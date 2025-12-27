"""
Progress URL Configuration
==========================

Video ilerleme API endpoint'leri.

URL Pattern:
    /api/v1/courses/{courseId}/content/{contentId}/progress/
"""

from django.urls import path

from .views import ProgressView

app_name = 'progress'

urlpatterns = [
    path('', ProgressView.as_view(), name='progress'),
]

