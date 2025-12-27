"""
Progress Admin
==============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import VideoProgress, ProgressWatchWindow


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    """VideoProgress admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'watched_display',
        'completion_badge',
        'preferred_speed',
        'updated_at',
    ]
    
    list_filter = [
        'is_completed',
        'tenant',
        'updated_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'content__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'user',
        'course',
        'content',
        'watched_seconds',
        'completion_ratio',
        'is_completed',
        'completed_at',
        'last_session',
        'created_at',
        'updated_at',
    ]
    
    date_hierarchy = 'updated_at'
    ordering = ['-updated_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def watched_display(self, obj):
        minutes = obj.watched_seconds // 60
        seconds = obj.watched_seconds % 60
        return f'{minutes}:{seconds:02d}'
    watched_display.short_description = 'İzlenen'
    
    def completion_badge(self, obj):
        percent = float(obj.completion_ratio) * 100
        if obj.is_completed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ {:.0f}%</span>',
                percent
            )
        color = 'orange' if percent >= 50 else 'gray'
        return format_html(
            '<span style="color: {};">{:.0f}%</span>',
            color, percent
        )
    completion_badge.short_description = 'Tamamlanma'


@admin.register(ProgressWatchWindow)
class ProgressWatchWindowAdmin(admin.ModelAdmin):
    """ProgressWatchWindow admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'time_range',
        'duration_seconds',
        'playback_rate',
        'is_verified',
        'created_at',
    ]
    
    list_filter = [
        'is_verified',
        'tenant',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'session',
        'progress',
        'user',
        'content',
        'start_video_ts',
        'end_video_ts',
        'duration_seconds',
        'playback_rate',
        'is_verified',
        'created_at',
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def time_range(self, obj):
        def format_time(seconds):
            m, s = divmod(seconds, 60)
            return f'{m}:{s:02d}'
        return f'{format_time(obj.start_video_ts)} → {format_time(obj.end_video_ts)}'
    time_range.short_description = 'Aralık'

