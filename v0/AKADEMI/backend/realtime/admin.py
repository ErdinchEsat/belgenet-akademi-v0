"""
Realtime Admin
==============

Django admin panel yapılandırması.
"""

from django.contrib import admin

from .models import (
    Conversation,
    ConversationParticipant,
    ChatMessage,
    NotificationPreference,
)


class ConversationParticipantInline(admin.TabularInline):
    """Konuşma katılımcıları inline."""
    
    model = ConversationParticipant
    extra = 0
    raw_id_fields = ['user']
    readonly_fields = ['joined_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Conversation admin."""
    
    list_display = [
        'id', 'name', 'type', 'tenant',
        'message_count', 'last_message_at', 'created_at',
    ]
    list_filter = ['type', 'tenant', 'is_archived', 'created_at']
    search_fields = ['name', 'id']
    readonly_fields = ['id', 'message_count', 'last_message_at', 'created_at']
    raw_id_fields = ['tenant']
    inlines = [ConversationParticipantInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """ChatMessage admin."""
    
    list_display = [
        'id', 'conversation', 'sender', 'type',
        'content_preview', 'is_deleted', 'created_at',
    ]
    list_filter = ['type', 'is_deleted', 'is_edited', 'created_at']
    search_fields = ['content', 'sender__email']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['conversation', 'sender', 'attachment', 'reply_to']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'İçerik'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """NotificationPreference admin."""
    
    list_display = [
        'user', 'email_enabled', 'push_enabled',
        'quiet_hours_enabled', 'updated_at',
    ]
    list_filter = ['email_enabled', 'push_enabled', 'quiet_hours_enabled']
    search_fields = ['user__email']
    raw_id_fields = ['user']

