"""
Player Admin
=============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import PlaybackSession


@admin.register(PlaybackSession)
class PlaybackSessionAdmin(admin.ModelAdmin):
    """PlaybackSession admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'status_badge',
        'duration_display',
        'started_at',
        'device_id',
    ]
    
    list_filter = [
        'is_active',
        'ended_reason',
        'tenant',
        'started_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'content__title',
        'device_id',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'user',
        'course',
        'content',
        'started_at',
        'ended_at',
        'last_heartbeat_at',
        'ip_hash',
        'duration_seconds',
        'created_at',
        'updated_at',
    ]
    
    date_hierarchy = 'started_at'
    
    ordering = ['-started_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Aktif</span>'
            )
        return format_html(
            '<span style="color: gray;">○ {}</span>',
            obj.get_ended_reason_display() or 'Sonlandı'
        )
    status_badge.short_description = 'Durum'
    
    def duration_display(self, obj):
        seconds = obj.duration_seconds
        minutes = seconds // 60
        secs = seconds % 60
        return f'{minutes}:{secs:02d}'
    duration_display.short_description = 'Süre'

