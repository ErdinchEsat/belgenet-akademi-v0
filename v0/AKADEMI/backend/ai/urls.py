"""
AI URL Configuration
====================

AI API endpoint'leri.

URL Patterns:
    /api/v1/courses/{courseId}/content/{contentId}/transcript/
    /api/v1/courses/{courseId}/content/{contentId}/ai/
    /api/v1/courses/{courseId}/content/{contentId}/summary/
    /api/v1/ai/conversations/
    /api/v1/ai/quota/
"""

from django.urls import path

from .views import (
    TranscriptView,
    TranscriptLanguagesView,
    TranscriptSearchView,
    AIAskView,
    AIConversationsView,
    AIConversationDetailView,
    AIQuotaView,
    SummaryView,
    SummaryListView,
)

app_name = 'ai'

# Content scoped URLs (courses/{courseId}/content/{contentId}/ prefix ile)
content_urlpatterns = [
    # Transcript
    path('transcript/', TranscriptView.as_view(), name='transcript'),
    path('transcript/languages/', TranscriptLanguagesView.as_view(), name='transcript-languages'),
    path('transcript/search/', TranscriptSearchView.as_view(), name='transcript-search'),
    
    # AI Chat
    path('ai/ask/', AIAskView.as_view(), name='ai-ask'),
    path('ai/conversations/', AIConversationsView.as_view(), name='ai-conversations'),
    
    # Summary
    path('summary/', SummaryView.as_view(), name='summary'),
    path('summaries/', SummaryListView.as_view(), name='summaries'),
]

# Global URLs (/api/v1/ai/ prefix ile)
urlpatterns = [
    path('conversations/', AIConversationsView.as_view(), name='conversations-list'),
    path('conversations/<uuid:conversation_id>/', AIConversationDetailView.as_view(), name='conversation-detail'),
    path('quota/', AIQuotaView.as_view(), name='quota'),
]

