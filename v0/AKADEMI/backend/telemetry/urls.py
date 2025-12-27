"""
Telemetry URL Configuration
===========================

Event tracking API endpoint'leri.

URL Pattern:
    /api/v1/courses/{courseId}/content/{contentId}/events/
"""

from django.urls import path

from .views import EventBatchView

app_name = 'telemetry'

urlpatterns = [
    path('', EventBatchView.as_view(), name='events'),
]

