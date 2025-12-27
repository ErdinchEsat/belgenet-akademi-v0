"""
Sequencing URL Configuration
============================

İçerik kilitleme API endpoint'leri.

URL Pattern:
    /api/v1/courses/{courseId}/content/{contentId}/lock/
    /api/v1/courses/{courseId}/content/{contentId}/lock/evaluate/
"""

from django.urls import path

from .views import LockStatusView, LockEvaluateView

app_name = 'sequencing'

urlpatterns = [
    path('', LockStatusView.as_view(), name='status'),
    path('evaluate/', LockEvaluateView.as_view(), name='evaluate'),
]

