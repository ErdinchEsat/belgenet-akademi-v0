"""
Realtime URLs
=============

Mesajlaşma ve bildirim API endpoint'leri.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    ArchivedConversationsView,
    MessageSearchView,
    NotificationPreferenceView,
    UnreadCountView,
)

app_name = 'realtime'

# Conversations router
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    # Conversations API
    path('', include(router.urls)),
    
    # Arşivlenmiş konuşmalar
    path('archived/', ArchivedConversationsView.as_view(), name='archived'),
    
    # Mesaj arama
    path('search/', MessageSearchView.as_view(), name='search'),
    
    # Bildirim tercihleri
    path('notifications/preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # Okunmamış sayılar
    path('notifications/unread-count/', UnreadCountView.as_view(), name='unread-count'),
]

