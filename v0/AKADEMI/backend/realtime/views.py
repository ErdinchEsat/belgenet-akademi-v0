"""
Realtime Views
==============

Mesajlaşma ve bildirim REST API view'ları.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Conversation,
    ConversationParticipant,
    ChatMessage,
    NotificationPreference,
)
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ConversationCreateSerializer,
    ChatMessageSerializer,
    SendMessageSerializer,
    NotificationPreferenceSerializer,
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    Konuşma API.
    
    Endpoints:
    - GET /api/v1/messages/conversations/ - Konuşma listesi
    - POST /api/v1/messages/conversations/ - Yeni konuşma
    - GET /api/v1/messages/conversations/{id}/ - Konuşma detayı
    - DELETE /api/v1/messages/conversations/{id}/ - Konuşmadan ayrıl
    - GET /api/v1/messages/conversations/{id}/messages/ - Mesajlar
    - POST /api/v1/messages/conversations/{id}/messages/ - Mesaj gönder
    - POST /api/v1/messages/conversations/{id}/mark_read/ - Okundu işaretle
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Kullanıcının konuşmalarını döndür."""
        return Conversation.objects.filter(
            conversation_participants__user=self.request.user,
            conversation_participants__left_at__isnull=True,
            is_archived=False,
        ).order_by('-last_message_at', '-created_at').distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def perform_destroy(self, instance):
        """Konuşmadan ayrıl (silme değil)."""
        ConversationParticipant.objects.filter(
            conversation=instance,
            user=self.request.user,
        ).update(left_at=timezone.now())
    
    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """Konuşma mesajları."""
        conversation = self.get_object()
        
        if request.method == 'GET':
            # Mesajları listele
            messages = ChatMessage.objects.filter(
                conversation=conversation,
                is_deleted=False,
            ).select_related('sender', 'attachment', 'reply_to').order_by('-created_at')
            
            # Pagination
            page = self.paginate_queryset(messages)
            if page is not None:
                serializer = ChatMessageSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)
        
        else:
            # Mesaj gönder
            serializer = SendMessageSerializer(
                data=request.data,
                context={'request': request, 'conversation': conversation}
            )
            serializer.is_valid(raise_exception=True)
            message = serializer.save()
            
            # WebSocket ile bildir
            self._notify_new_message(conversation, message)
            
            return Response(
                ChatMessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Konuşmayı okundu olarak işaretle."""
        conversation = self.get_object()
        
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(
            last_read_at=timezone.now(),
            unread_count=0,
        )
        
        return Response({'status': 'ok'})
    
    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """Konuşmayı sessize al."""
        conversation = self.get_object()
        muted_until = request.data.get('until')  # ISO datetime
        
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(
            is_muted=True,
            muted_until=muted_until,
        )
        
        return Response({'status': 'muted'})
    
    @action(detail=True, methods=['post'])
    def unmute(self, request, pk=None):
        """Sessizden çıkar."""
        conversation = self.get_object()
        
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(
            is_muted=False,
            muted_until=None,
        )
        
        return Response({'status': 'unmuted'})
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Konuşmayı sabitle."""
        conversation = self.get_object()
        
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(is_pinned=True)
        
        return Response({'status': 'pinned'})
    
    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        """Sabitlemeyi kaldır."""
        conversation = self.get_object()
        
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(is_pinned=False)
        
        return Response({'status': 'unpinned'})
    
    @action(detail=True, methods=['post'])
    def add_participants(self, request, pk=None):
        """Konuşmaya katılımcı ekle (grup için)."""
        conversation = self.get_object()
        
        if conversation.type == Conversation.Type.PRIVATE:
            return Response(
                {'error': 'Özel konuşmaya katılımcı eklenemez'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Yetki kontrolü
        my_role = ConversationParticipant.objects.get(
            conversation=conversation,
            user=request.user,
        ).role
        
        if my_role not in [ConversationParticipant.Role.ADMIN, ConversationParticipant.Role.OWNER]:
            return Response(
                {'error': 'Bu işlem için yetkiniz yok'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_ids = request.data.get('user_ids', [])
        added = []
        
        for user_id in user_ids:
            participant, created = ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user_id=user_id,
                defaults={'role': ConversationParticipant.Role.MEMBER},
            )
            if created:
                added.append(user_id)
            elif participant.left_at:
                participant.left_at = None
                participant.save()
                added.append(user_id)
        
        return Response({'added': added})
    
    def _notify_new_message(self, conversation, message):
        """WebSocket üzerinden yeni mesaj bildirimi."""
        from .consumers.notification_consumer import send_notification_to_user_sync
        
        # Tüm katılımcılara bildir (gönderen hariç)
        for participant in conversation.conversation_participants.exclude(user=message.sender):
            if not participant.is_muted:
                send_notification_to_user_sync(
                    participant.user_id,
                    {
                        'id': 0,
                        'title': f'Yeni mesaj: {conversation.get_display_name(participant.user)}',
                        'message': message.content_preview,
                        'type': 'MESSAGE',
                        'action_url': f'/messages/{conversation.id}',
                    }
                )


class ArchivedConversationsView(generics.ListAPIView):
    """
    Arşivlenmiş konuşmalar.
    
    GET /api/v1/messages/archived/
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer
    
    def get_queryset(self):
        return Conversation.objects.filter(
            conversation_participants__user=self.request.user,
            conversation_participants__left_at__isnull=True,
            is_archived=True,
        ).order_by('-last_message_at')


class MessageSearchView(generics.ListAPIView):
    """
    Mesaj arama.
    
    GET /api/v1/messages/search/?q=aranacak
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ChatMessageSerializer
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        
        if len(query) < 2:
            return ChatMessage.objects.none()
        
        # Kullanıcının konuşmalarındaki mesajlarda ara
        user_conversations = Conversation.objects.filter(
            conversation_participants__user=self.request.user,
            conversation_participants__left_at__isnull=True,
        )
        
        return ChatMessage.objects.filter(
            conversation__in=user_conversations,
            content__icontains=query,
            is_deleted=False,
        ).select_related('sender', 'conversation').order_by('-created_at')[:50]


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    Bildirim tercihleri.
    
    GET /api/v1/notifications/preferences/
    PUT /api/v1/notifications/preferences/
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    
    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj


class UnreadCountView(generics.GenericAPIView):
    """
    Okunmamış sayıları döndürür.
    
    GET /api/v1/notifications/unread-count/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from backend.student.models import Notification
        
        # Okunmamış bildirimler
        notification_count = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
        
        # Okunmamış mesajlar
        message_count = ConversationParticipant.objects.filter(
            user=request.user,
            left_at__isnull=True,
            unread_count__gt=0,
        ).count()
        
        return Response({
            'notifications': notification_count,
            'messages': message_count,
            'total': notification_count + message_count,
        })

