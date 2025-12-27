"""
Base WebSocket Consumer
=======================

Tüm WebSocket consumer'ları için temel sınıf.
"""

import json
import logging
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class BaseConsumer(AsyncJsonWebsocketConsumer):
    """
    Base WebSocket Consumer.
    
    Ortak işlevler:
    - Authentication kontrolü
    - Group management
    - Error handling
    - Logging
    """
    
    # Alt sınıflar override edebilir
    requires_auth = True
    
    async def connect(self):
        """WebSocket bağlantısı kurulduğunda."""
        self.user = self.scope.get('user', AnonymousUser())
        self.tenant = self.scope.get('tenant')
        
        # Authentication kontrolü
        if self.requires_auth and not await self.is_authenticated():
            logger.warning(f"Unauthorized WebSocket connection attempt")
            await self.close(code=4001)
            return
        
        # Bağlantıyı kabul et
        await self.accept()
        
        # Kullanıcı gruplarına katıl
        await self.join_user_groups()
        
        logger.info(f"WebSocket connected: {self.user} - {self.channel_name}")
    
    async def disconnect(self, close_code):
        """WebSocket bağlantısı kesildiğinde."""
        # Gruplardan ayrıl
        await self.leave_user_groups()
        
        logger.info(f"WebSocket disconnected: {self.user} - code: {close_code}")
    
    async def receive_json(self, content):
        """
        JSON mesaj alındığında.
        
        Alt sınıflar bu metodu override etmeli.
        """
        message_type = content.get('type', 'unknown')
        
        # Handler metodunu çağır
        handler = getattr(self, f'handle_{message_type}', None)
        if handler:
            try:
                await handler(content)
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                await self.send_error(str(e))
        else:
            await self.send_error(f"Unknown message type: {message_type}")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def is_authenticated(self) -> bool:
        """Kullanıcı doğrulanmış mı?"""
        return self.user and not isinstance(self.user, AnonymousUser)
    
    async def join_user_groups(self):
        """Kullanıcıya özel gruplara katıl."""
        if await self.is_authenticated():
            # Kullanıcı grubu
            user_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(user_group, self.channel_name)
            
            # Tenant grubu
            if self.tenant:
                tenant_group = f"tenant_{self.tenant.id}"
                await self.channel_layer.group_add(tenant_group, self.channel_name)
    
    async def leave_user_groups(self):
        """Kullanıcı gruplarından ayrıl."""
        if await self.is_authenticated():
            user_group = f"user_{self.user.id}"
            await self.channel_layer.group_discard(user_group, self.channel_name)
            
            if self.tenant:
                tenant_group = f"tenant_{self.tenant.id}"
                await self.channel_layer.group_discard(tenant_group, self.channel_name)
    
    async def send_success(self, data: dict = None, message: str = "Success"):
        """Başarı mesajı gönder."""
        await self.send_json({
            'status': 'success',
            'message': message,
            'data': data or {},
        })
    
    async def send_error(self, message: str, code: str = "error"):
        """Hata mesajı gönder."""
        await self.send_json({
            'status': 'error',
            'code': code,
            'message': message,
        })
    
    @staticmethod
    def get_user_group(user_id) -> str:
        """Kullanıcı grup adını döndürür."""
        return f"user_{user_id}"
    
    @staticmethod
    def get_tenant_group(tenant_id) -> str:
        """Tenant grup adını döndürür."""
        return f"tenant_{tenant_id}"

