"""
AI Admin
========

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Transcript, TranscriptSegment,
    AIConversation, AIMessage,
    VideoSummary, AIQuota
)


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    """Transcript admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_title',
        'language',
        'source',
        'status_badge',
        'word_count',
        'segment_count',
        'created_at',
    ]
    
    list_filter = [
        'language',
        'source',
        'status',
        'tenant',
    ]
    
    search_fields = [
        'content__title',
        'full_text',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'word_count',
        'segment_count',
        'duration_seconds',
        'created_at',
        'updated_at',
    ]
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    """TranscriptSegment admin konfigürasyonu."""
    
    list_display = [
        'id',
        'transcript_info',
        'sequence',
        'time_display',
        'text_preview',
    ]
    
    list_filter = [
        'transcript__language',
    ]
    
    search_fields = [
        'text',
    ]
    
    readonly_fields = [
        'id',
    ]
    
    def transcript_info(self, obj):
        return f"{obj.transcript.content.title} ({obj.transcript.language})"
    transcript_info.short_description = 'Transkript'
    
    def time_display(self, obj):
        start = f"{int(obj.start_ts // 60)}:{int(obj.start_ts % 60):02d}"
        end = f"{int(obj.end_ts // 60)}:{int(obj.end_ts % 60):02d}"
        return f"{start} → {end}"
    time_display.short_description = 'Zaman'
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Metin'


class AIMessageInline(admin.TabularInline):
    """AI Message inline for conversation."""
    
    model = AIMessage
    extra = 0
    readonly_fields = ['id', 'role', 'content', 'video_ts', 'tokens_used', 'created_at']
    can_delete = False


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    """AIConversation admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'title',
        'content_title',
        'message_count',
        'last_activity_at',
    ]
    
    list_filter = [
        'tenant',
        'last_activity_at',
    ]
    
    search_fields = [
        'user__email',
        'title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'message_count',
        'last_activity_at',
        'created_at',
        'updated_at',
    ]
    
    inlines = [AIMessageInline]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title if obj.content else '-'
    content_title.short_description = 'İçerik'


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    """AIMessage admin konfigürasyonu."""
    
    list_display = [
        'id',
        'conversation_info',
        'role',
        'content_preview',
        'tokens_used',
        'created_at',
    ]
    
    list_filter = [
        'role',
        'model_used',
    ]
    
    search_fields = [
        'content',
    ]
    
    readonly_fields = [
        'id',
        'conversation',
        'role',
        'content',
        'video_ts',
        'sources',
        'tokens_used',
        'model_used',
        'created_at',
    ]
    
    def conversation_info(self, obj):
        return f"{obj.conversation.user.email} - {obj.conversation.title[:30]}..."
    conversation_info.short_description = 'Konuşma'
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'İçerik'


@admin.register(VideoSummary)
class VideoSummaryAdmin(admin.ModelAdmin):
    """VideoSummary admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_title',
        'summary_type',
        'language',
        'tokens_used',
        'created_at',
    ]
    
    list_filter = [
        'summary_type',
        'language',
        'tenant',
    ]
    
    search_fields = [
        'content__title',
        'summary_text',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'tokens_used',
        'model_used',
        'created_at',
        'updated_at',
    ]
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'


@admin.register(AIQuota)
class AIQuotaAdmin(admin.ModelAdmin):
    """AIQuota admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'daily_usage',
        'monthly_usage',
        'daily_reset_at',
    ]
    
    list_filter = [
        'tenant',
    ]
    
    search_fields = [
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def daily_usage(self, obj):
        return f"{obj.daily_questions_used}/{obj.daily_questions_limit}"
    daily_usage.short_description = 'Günlük Kullanım'
    
    def monthly_usage(self, obj):
        return f"{obj.monthly_tokens_used:,}/{obj.monthly_tokens_limit:,}"
    monthly_usage.short_description = 'Aylık Token'

