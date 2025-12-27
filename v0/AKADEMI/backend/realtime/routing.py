"""
WebSocket URL Routing
=====================

WebSocket endpoint'leri için URL tanımları.
"""

from django.urls import re_path

from .consumers import NotificationConsumer, MessagingConsumer

websocket_urlpatterns = [
    # Bildirimler
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    
    # Mesajlaşma - Genel
    re_path(r'ws/messages/$', MessagingConsumer.as_asgi()),
    
    # Mesajlaşma - Belirli konuşma
    re_path(
        r'ws/messages/(?P<conversation_id>[0-9a-f-]+)/$',
        MessagingConsumer.as_asgi()
    ),
]

