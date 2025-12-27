"""
Integrity URL Configuration
===========================

Integrity API endpoint'leri.

URL Pattern:
    /api/v1/integrity/
"""

from django.urls import path

from .views import (
    IntegrityVerifyView,
    IntegrityStatusView,
    AnomalyReportView,
    UserIntegrityScoreView,
    SessionIntegrityHistoryView,
    UserAnomaliesView,
)

app_name = 'integrity'

urlpatterns = [
    path('verify/', IntegrityVerifyView.as_view(), name='verify'),
    path('status/', IntegrityStatusView.as_view(), name='status'),
    path('report/', AnomalyReportView.as_view(), name='report'),
    path('score/', UserIntegrityScoreView.as_view(), name='score'),
    path('history/', SessionIntegrityHistoryView.as_view(), name='history'),
    path('anomalies/', UserAnomaliesView.as_view(), name='anomalies'),
]

