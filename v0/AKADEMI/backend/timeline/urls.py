"""
Timeline URL Configuration
==========================

Timeline API endpoint'leri.

URL Pattern:
    /api/v1/courses/{courseId}/content/{contentId}/timeline/
"""

from django.urls import path

from .views import (
    TimelineView,
    TimelineInteractionView,
    CheckpointConfirmView,
    PollAnswerView,
)

app_name = 'timeline'

urlpatterns = [
    path('', TimelineView.as_view(), name='list'),
    path('<uuid:node_id>/interact/', TimelineInteractionView.as_view(), name='interact'),
    path('<uuid:node_id>/confirm/', CheckpointConfirmView.as_view(), name='confirm'),
    path('<uuid:node_id>/answer/', PollAnswerView.as_view(), name='answer'),
    path('<uuid:node_id>/results/', PollAnswerView.as_view(), name='results'),
]

