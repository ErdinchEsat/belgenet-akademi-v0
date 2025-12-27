"""
Realtime Serializers
====================

Mesajlaşma ve bildirim API serializer'ları.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Conversation,
    ConversationParticipant,
    ChatMessage,
    NotificationPreference,
)

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal kullanıcı bilgisi."""
    
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar_url']
    
    def get_avatar_url(self, obj):
        return obj.get_avatar_url()


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Konuşma katılımcısı serializer."""
    
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'user', 'role', 'is_muted', 'unread_count',
            'is_pinned', 'joined_at', 'last_read_at',
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    """Sohbet mesajı serializer."""
    
    sender = UserMinimalSerializer(read_only=True)
    content_preview = serializers.ReadOnlyField()
    attachment_info = serializers.SerializerMethodField()
    reply_to_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'conversation', 'sender', 'type', 'content',
            'content_preview', 'attachment_info', 'reply_to', 'reply_to_info',
            'is_edited', 'edited_at', 'is_deleted', 'created_at',
        ]
        read_only_fields = ['id', 'sender', 'is_edited', 'edited_at', 'is_deleted', 'created_at']
    
    def get_attachment_info(self, obj):
        if not obj.attachment:
            return None
        return {
            'id': str(obj.attachment.id),
            'filename': obj.attachment.original_filename,
            'file_size': obj.attachment.file_size_display,
            'mime_type': obj.attachment.mime_type,
            'url': obj.attachment.file_url,
        }
    
    def get_reply_to_info(self, obj):
        if not obj.reply_to:
            return None
        return {
            'id': str(obj.reply_to.id),
            'sender_name': obj.reply_to.sender.full_name if obj.reply_to.sender else 'Silinmiş',
            'content_preview': obj.reply_to.content_preview,
        }


class ConversationSerializer(serializers.ModelSerializer):
    """Konuşma serializer."""
    
    participants_info = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    my_participation = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'type', 'avatar', 'description',
            'display_name', 'participants_info', 'my_participation',
            'last_message_at', 'last_message_preview', 'message_count',
            'is_muted', 'is_archived', 'created_at',
        ]
        read_only_fields = ['id', 'last_message_at', 'last_message_preview', 'message_count', 'created_at']
    
    def get_participants_info(self, obj):
        participants = obj.conversation_participants.select_related('user')[:5]
        return ConversationParticipantSerializer(participants, many=True).data
    
    def get_display_name(self, obj):
        request = self.context.get('request')
        if request:
            return obj.get_display_name(request.user)
        return obj.name or str(obj.id)
    
    def get_my_participation(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        
        try:
            participation = obj.conversation_participants.get(user=request.user)
            return {
                'role': participation.role,
                'is_muted': participation.is_muted,
                'is_pinned': participation.is_pinned,
                'unread_count': participation.unread_count,
            }
        except ConversationParticipant.DoesNotExist:
            return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Konuşma listesi için basit serializer."""
    
    display_name = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'type', 'avatar', 'display_name',
            'last_message_at', 'last_message_preview',
            'unread_count', 'other_participant',
        ]
    
    def get_display_name(self, obj):
        request = self.context.get('request')
        if request:
            return obj.get_display_name(request.user)
        return obj.name
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        
        try:
            return obj.conversation_participants.get(user=request.user).unread_count
        except ConversationParticipant.DoesNotExist:
            return 0
    
    def get_other_participant(self, obj):
        """Özel konuşmalarda karşı tarafın bilgisi."""
        request = self.context.get('request')
        if not request or obj.type != Conversation.Type.PRIVATE:
            return None
        
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return UserMinimalSerializer(other).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    """Yeni konuşma oluşturma."""
    
    type = serializers.ChoiceField(
        choices=Conversation.Type.choices,
        default=Conversation.Type.PRIVATE,
    )
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    initial_message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_participant_ids(self, value):
        # Kendini ekleme
        request = self.context.get('request')
        if request and request.user.id in value:
            value.remove(request.user.id)
        
        # Kullanıcıların varlığını kontrol et
        existing = User.objects.filter(id__in=value).count()
        if existing != len(value):
            raise serializers.ValidationError("Bazı kullanıcılar bulunamadı")
        
        return value
    
    def create(self, validated_data):
        from django.db import transaction
        
        request = self.context.get('request')
        participant_ids = validated_data.pop('participant_ids')
        initial_message = validated_data.pop('initial_message', None)
        conv_type = validated_data.get('type', Conversation.Type.PRIVATE)
        
        with transaction.atomic():
            # Özel konuşma için mevcut konuşmayı kontrol et
            if conv_type == Conversation.Type.PRIVATE and len(participant_ids) == 1:
                existing = self._find_existing_private_conversation(
                    request.user.id,
                    participant_ids[0]
                )
                if existing:
                    return existing
            
            # Yeni konuşma oluştur
            conversation = Conversation.objects.create(
                tenant=request.user.tenant,
                **validated_data
            )
            
            # Kendini ekle
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=request.user,
                role=ConversationParticipant.Role.OWNER if conv_type != Conversation.Type.PRIVATE else ConversationParticipant.Role.MEMBER,
            )
            
            # Diğer katılımcıları ekle
            for user_id in participant_ids:
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user_id=user_id,
                    role=ConversationParticipant.Role.MEMBER,
                )
            
            # İlk mesajı gönder
            if initial_message:
                ChatMessage.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    type=ChatMessage.Type.TEXT,
                    content=initial_message,
                )
                conversation.last_message_preview = initial_message[:100]
                conversation.message_count = 1
                conversation.save()
        
        return conversation
    
    def _find_existing_private_conversation(self, user1_id, user2_id):
        """Mevcut özel konuşmayı bul."""
        from django.db.models import Count
        
        conversations = Conversation.objects.filter(
            type=Conversation.Type.PRIVATE,
            participants__id=user1_id,
        ).filter(
            participants__id=user2_id,
        ).annotate(
            participant_count=Count('participants')
        ).filter(participant_count=2)
        
        return conversations.first()


class SendMessageSerializer(serializers.Serializer):
    """Mesaj gönderme (REST API)."""
    
    content = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(
        choices=ChatMessage.Type.choices,
        default=ChatMessage.Type.TEXT,
    )
    reply_to = serializers.UUIDField(required=False, allow_null=True)
    attachment_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate(self, attrs):
        if not attrs.get('content') and not attrs.get('attachment_id'):
            raise serializers.ValidationError("Mesaj içeriği veya dosya gerekli")
        return attrs
    
    def create(self, validated_data):
        conversation = self.context['conversation']
        request = self.context['request']
        
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            type=validated_data.get('type', ChatMessage.Type.TEXT),
            content=validated_data.get('content', ''),
            reply_to_id=validated_data.get('reply_to'),
            attachment_id=validated_data.get('attachment_id'),
        )
        
        # Konuşma bilgilerini güncelle
        conversation.last_message_at = message.created_at
        conversation.last_message_preview = message.content_preview
        conversation.message_count += 1
        conversation.save(update_fields=['last_message_at', 'last_message_preview', 'message_count'])
        
        return message


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Bildirim tercihleri serializer."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'sms_enabled',
            'notify_assignments', 'notify_grades', 'notify_messages',
            'notify_live_sessions', 'notify_announcements', 'notify_system',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
        ]
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

