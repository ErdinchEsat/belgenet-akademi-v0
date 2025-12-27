"""
Notification WebSocket Consumer
===============================

Gerçek zamanlı bildirim gönderimi.
"""

import logging
from channels.db import database_sync_to_async

from .base import BaseConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(BaseConsumer):
    """
    Bildirim WebSocket Consumer.
    
    Kullanıcıya gerçek zamanlı bildirim gönderir.
    
    Client → Server Messages:
    - {"type": "mark_read", "notification_id": 123}
    - {"type": "mark_all_read"}
    - {"type": "get_unread_count"}
    
    Server → Client Messages:
    - {"type": "notification", "data": {...}}
    - {"type": "unread_count", "count": 5}
    """
    
    async def connect(self):
        """Bağlantı kurulduğunda."""
        await super().connect()
        
        if await self.is_authenticated():
            # Okunmamış sayısını gönder
            await self.send_unread_count()
    
    # =========================================================================
    # CLIENT MESSAGE HANDLERS
    # =========================================================================
    
    async def handle_mark_read(self, content):
        """Bildirimi okundu olarak işaretle."""
        notification_id = content.get('notification_id')
        
        if not notification_id:
            await self.send_error("notification_id gerekli")
            return
        
        success = await self.mark_notification_read(notification_id)
        
        if success:
            await self.send_success(message="Bildirim okundu olarak işaretlendi")
            await self.send_unread_count()
        else:
            await self.send_error("Bildirim bulunamadı")
    
    async def handle_mark_all_read(self, content):
        """Tüm bildirimleri okundu olarak işaretle."""
        count = await self.mark_all_notifications_read()
        await self.send_success(
            data={'marked_count': count},
            message=f"{count} bildirim okundu olarak işaretlendi"
        )
        await self.send_unread_count()
    
    async def handle_get_unread_count(self, content):
        """Okunmamış bildirim sayısını gönder."""
        await self.send_unread_count()
    
    # =========================================================================
    # SERVER → CLIENT MESSAGES
    # =========================================================================
    
    async def notification_message(self, event):
        """
        Channel layer'dan gelen bildirim mesajı.
        
        Başka bir yerden (view, signal, task) gönderilen bildirim.
        """
        notification_data = event.get('data', {})
        
        await self.send_json({
            'type': 'notification',
            'data': notification_data,
        })
    
    async def send_unread_count(self):
        """Okunmamış bildirim sayısını gönder."""
        count = await self.get_unread_count()
        await self.send_json({
            'type': 'unread_count',
            'count': count,
        })
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    @database_sync_to_async
    def get_unread_count(self) -> int:
        """Okunmamış bildirim sayısı."""
        from backend.student.models import Notification
        return Notification.objects.filter(
            user=self.user,
            is_read=False,
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id) -> bool:
        """Bildirimi okundu olarak işaretle."""
        from backend.student.models import Notification
        from django.utils import timezone
        
        updated = Notification.objects.filter(
            id=notification_id,
            user=self.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        
        return updated > 0
    
    @database_sync_to_async
    def mark_all_notifications_read(self) -> int:
        """Tüm bildirimleri okundu olarak işaretle."""
        from backend.student.models import Notification
        from django.utils import timezone
        
        return Notification.objects.filter(
            user=self.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())


# =============================================================================
# UTILITY FUNCTIONS (View'lardan çağrılabilir)
# =============================================================================

async def send_notification_to_user(user_id: int, notification_data: dict):
    """
    Kullanıcıya gerçek zamanlı bildirim gönderir.
    
    Kullanım:
    --------
    from backend.realtime.consumers.notification_consumer import send_notification_to_user
    
    await send_notification_to_user(
        user_id=123,
        notification_data={
            'id': 1,
            'title': 'Yeni ödev',
            'message': 'Matematik ödevi eklendi',
            'type': 'ASSIGNMENT',
        }
    )
    """
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    
    await channel_layer.group_send(
        group_name,
        {
            'type': 'notification_message',
            'data': notification_data,
        }
    )


def send_notification_to_user_sync(user_id: int, notification_data: dict):
    """
    Senkron versiyon - View'lardan kullanım için.
    
    Kullanım:
    --------
    from backend.realtime.consumers.notification_consumer import send_notification_to_user_sync
    
    send_notification_to_user_sync(
        user_id=123,
        notification_data={'title': 'Test', ...}
    )
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            'data': notification_data,
        }
    )

