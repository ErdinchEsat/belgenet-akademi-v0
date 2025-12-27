"""
Messaging WebSocket Consumer
============================

Gerçek zamanlı mesajlaşma.
"""

import logging
from uuid import UUID

from channels.db import database_sync_to_async
from django.utils import timezone

from .base import BaseConsumer

logger = logging.getLogger(__name__)


class MessagingConsumer(BaseConsumer):
    """
    Mesajlaşma WebSocket Consumer.
    
    Gerçek zamanlı sohbet mesajlaşması.
    
    Client → Server Messages:
    - {"type": "send_message", "conversation_id": "...", "content": "..."}
    - {"type": "typing", "conversation_id": "..."}
    - {"type": "stop_typing", "conversation_id": "..."}
    - {"type": "mark_read", "conversation_id": "..."}
    - {"type": "delete_message", "message_id": "..."}
    - {"type": "edit_message", "message_id": "...", "content": "..."}
    
    Server → Client Messages:
    - {"type": "new_message", "data": {...}}
    - {"type": "user_typing", "user_id": ..., "conversation_id": "..."}
    - {"type": "message_read", "message_id": "...", "user_id": ...}
    - {"type": "message_deleted", "message_id": "..."}
    - {"type": "message_edited", "message_id": "...", "content": "..."}
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_groups = set()
    
    async def connect(self):
        """Bağlantı kurulduğunda."""
        await super().connect()
        
        if await self.is_authenticated():
            # URL'den conversation_id varsa o konuşmaya katıl
            conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
            if conversation_id:
                await self.join_conversation(conversation_id)
            else:
                # Tüm konuşmalara katıl
                await self.join_all_conversations()
    
    async def disconnect(self, close_code):
        """Bağlantı kesildiğinde."""
        # Tüm konuşma gruplarından ayrıl
        for group_name in self.conversation_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
        
        await super().disconnect(close_code)
    
    # =========================================================================
    # GROUP MANAGEMENT
    # =========================================================================
    
    async def join_conversation(self, conversation_id: str):
        """Belirli bir konuşmaya katıl."""
        # Yetki kontrolü
        if not await self.can_access_conversation(conversation_id):
            await self.send_error("Bu konuşmaya erişim yetkiniz yok")
            return False
        
        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.conversation_groups.add(group_name)
        
        logger.debug(f"User {self.user.id} joined conversation {conversation_id}")
        return True
    
    async def join_all_conversations(self):
        """Kullanıcının tüm konuşmalarına katıl."""
        conversation_ids = await self.get_user_conversations()
        
        for conv_id in conversation_ids:
            group_name = f"conversation_{conv_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.conversation_groups.add(group_name)
    
    # =========================================================================
    # CLIENT MESSAGE HANDLERS
    # =========================================================================
    
    async def handle_send_message(self, content):
        """Mesaj gönder."""
        conversation_id = content.get('conversation_id')
        message_content = content.get('content', '').strip()
        message_type = content.get('message_type', 'text')
        reply_to = content.get('reply_to')
        attachment_id = content.get('attachment_id')
        
        if not conversation_id:
            await self.send_error("conversation_id gerekli")
            return
        
        if not message_content and not attachment_id:
            await self.send_error("Mesaj içeriği veya dosya gerekli")
            return
        
        # Yetki kontrolü
        if not await self.can_access_conversation(conversation_id):
            await self.send_error("Bu konuşmaya erişim yetkiniz yok")
            return
        
        # Mesajı kaydet
        message = await self.create_message(
            conversation_id=conversation_id,
            content=message_content,
            message_type=message_type,
            reply_to=reply_to,
            attachment_id=attachment_id,
        )
        
        if not message:
            await self.send_error("Mesaj gönderilemedi")
            return
        
        # Tüm katılımcılara bildir
        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'new_message_event',
                'data': message,
            }
        )
    
    async def handle_typing(self, content):
        """Yazıyor... bildirimi."""
        conversation_id = content.get('conversation_id')
        
        if not conversation_id:
            return
        
        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'user_typing_event',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'conversation_id': conversation_id,
            }
        )
    
    async def handle_stop_typing(self, content):
        """Yazma bitti bildirimi."""
        conversation_id = content.get('conversation_id')
        
        if not conversation_id:
            return
        
        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'user_stop_typing_event',
                'user_id': self.user.id,
                'conversation_id': conversation_id,
            }
        )
    
    async def handle_mark_read(self, content):
        """Konuşmayı okundu olarak işaretle."""
        conversation_id = content.get('conversation_id')
        
        if not conversation_id:
            return
        
        await self.mark_conversation_read(conversation_id)
        
        # Diğer katılımcılara bildir
        group_name = f"conversation_{conversation_id}"
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'messages_read_event',
                'user_id': self.user.id,
                'conversation_id': conversation_id,
            }
        )
    
    async def handle_delete_message(self, content):
        """Mesajı sil."""
        message_id = content.get('message_id')
        
        if not message_id:
            await self.send_error("message_id gerekli")
            return
        
        result = await self.delete_message(message_id)
        
        if result:
            # Tüm katılımcılara bildir
            group_name = f"conversation_{result['conversation_id']}"
            await self.channel_layer.group_send(
                group_name,
                {
                    'type': 'message_deleted_event',
                    'message_id': message_id,
                }
            )
        else:
            await self.send_error("Mesaj silinemedi")
    
    async def handle_edit_message(self, content):
        """Mesajı düzenle."""
        message_id = content.get('message_id')
        new_content = content.get('content', '').strip()
        
        if not message_id or not new_content:
            await self.send_error("message_id ve content gerekli")
            return
        
        result = await self.edit_message(message_id, new_content)
        
        if result:
            group_name = f"conversation_{result['conversation_id']}"
            await self.channel_layer.group_send(
                group_name,
                {
                    'type': 'message_edited_event',
                    'message_id': message_id,
                    'content': new_content,
                    'edited_at': result['edited_at'],
                }
            )
        else:
            await self.send_error("Mesaj düzenlenemedi")
    
    # =========================================================================
    # SERVER → CLIENT EVENTS
    # =========================================================================
    
    async def new_message_event(self, event):
        """Yeni mesaj bildir."""
        await self.send_json({
            'type': 'new_message',
            'data': event['data'],
        })
    
    async def user_typing_event(self, event):
        """Yazıyor... bildir."""
        # Kendimize gönderme
        if event['user_id'] == self.user.id:
            return
        
        await self.send_json({
            'type': 'user_typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'conversation_id': event['conversation_id'],
        })
    
    async def user_stop_typing_event(self, event):
        """Yazma bitti bildir."""
        if event['user_id'] == self.user.id:
            return
        
        await self.send_json({
            'type': 'user_stop_typing',
            'user_id': event['user_id'],
            'conversation_id': event['conversation_id'],
        })
    
    async def messages_read_event(self, event):
        """Okundu bildir."""
        if event['user_id'] == self.user.id:
            return
        
        await self.send_json({
            'type': 'messages_read',
            'user_id': event['user_id'],
            'conversation_id': event['conversation_id'],
        })
    
    async def message_deleted_event(self, event):
        """Mesaj silindi bildir."""
        await self.send_json({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        })
    
    async def message_edited_event(self, event):
        """Mesaj düzenlendi bildir."""
        await self.send_json({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'edited_at': event['edited_at'],
        })
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    @database_sync_to_async
    def can_access_conversation(self, conversation_id: str) -> bool:
        """Konuşmaya erişim yetkisi var mı?"""
        from backend.realtime.models import ConversationParticipant
        
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            user=self.user,
            left_at__isnull=True,
        ).exists()
    
    @database_sync_to_async
    def get_user_conversations(self) -> list:
        """Kullanıcının konuşma ID'leri."""
        from backend.realtime.models import ConversationParticipant
        
        return list(
            ConversationParticipant.objects.filter(
                user=self.user,
                left_at__isnull=True,
            ).values_list('conversation_id', flat=True)
        )
    
    @database_sync_to_async
    def create_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str = 'text',
        reply_to: str = None,
        attachment_id: str = None,
    ) -> dict:
        """Mesaj oluştur."""
        from backend.realtime.models import ChatMessage, Conversation, ConversationParticipant
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Mesaj oluştur
            message = ChatMessage.objects.create(
                conversation=conversation,
                sender=self.user,
                type=message_type,
                content=content,
                reply_to_id=reply_to,
                attachment_id=attachment_id,
            )
            
            # Konuşma son mesaj bilgisini güncelle
            conversation.last_message_at = message.created_at
            conversation.last_message_preview = message.content_preview
            conversation.message_count += 1
            conversation.save(update_fields=['last_message_at', 'last_message_preview', 'message_count'])
            
            # Diğer katılımcıların okunmamış sayısını artır
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).exclude(user=self.user).update(
                unread_count=models.F('unread_count') + 1
            )
            
            return {
                'id': str(message.id),
                'conversation_id': str(conversation_id),
                'sender': {
                    'id': self.user.id,
                    'name': self.user.full_name,
                    'avatar': self.user.get_avatar_url(),
                },
                'type': message.type,
                'content': message.content,
                'content_preview': message.content_preview,
                'reply_to': str(message.reply_to_id) if message.reply_to_id else None,
                'attachment': {
                    'id': str(message.attachment.id),
                    'filename': message.attachment.original_filename,
                    'url': message.attachment.file_url,
                } if message.attachment else None,
                'created_at': message.created_at.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Message creation error: {e}")
            return None
    
    @database_sync_to_async
    def mark_conversation_read(self, conversation_id: str):
        """Konuşmayı okundu olarak işaretle."""
        from backend.realtime.models import ConversationParticipant
        
        ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            user=self.user,
        ).update(
            last_read_at=timezone.now(),
            unread_count=0,
        )
    
    @database_sync_to_async
    def delete_message(self, message_id: str) -> dict:
        """Mesajı sil (soft delete)."""
        from backend.realtime.models import ChatMessage
        
        try:
            message = ChatMessage.objects.get(
                id=message_id,
                sender=self.user,
                is_deleted=False,
            )
            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.save(update_fields=['is_deleted', 'deleted_at'])
            
            return {'conversation_id': str(message.conversation_id)}
            
        except ChatMessage.DoesNotExist:
            return None
    
    @database_sync_to_async
    def edit_message(self, message_id: str, new_content: str) -> dict:
        """Mesajı düzenle."""
        from backend.realtime.models import ChatMessage
        
        try:
            message = ChatMessage.objects.get(
                id=message_id,
                sender=self.user,
                is_deleted=False,
            )
            message.content = new_content
            message.is_edited = True
            message.edited_at = timezone.now()
            message.save(update_fields=['content', 'is_edited', 'edited_at'])
            
            return {
                'conversation_id': str(message.conversation_id),
                'edited_at': message.edited_at.isoformat(),
            }
            
        except ChatMessage.DoesNotExist:
            return None


# Import models for F expression
from django.db import models

