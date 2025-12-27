"""
Timeline Admin
==============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import TimelineNode, TimelineNodeInteraction


@admin.register(TimelineNode)
class TimelineNodeAdmin(admin.ModelAdmin):
    """TimelineNode admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_title',
        'node_type_badge',
        'time_display',
        'title',
        'is_blocking',
        'is_required',
        'is_active',
    ]
    
    list_filter = [
        'node_type',
        'is_blocking',
        'is_required',
        'is_active',
        'tenant',
    ]
    
    search_fields = [
        'title',
        'content__title',
        'course__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['content', 'start_ts', 'order']
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def node_type_badge(self, obj):
        colors = {
            'quiz': 'purple',
            'poll': 'blue',
            'checkpoint': 'orange',
            'hotspot': 'green',
            'info': 'gray',
            'cta': 'red',
            'chapter': 'teal',
        }
        color = colors.get(obj.node_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_node_type_display()
        )
    node_type_badge.short_description = 'Tür'
    
    def time_display(self, obj):
        start = f"{obj.start_ts // 60}:{obj.start_ts % 60:02d}"
        if obj.end_ts:
            end = f"{obj.end_ts // 60}:{obj.end_ts % 60:02d}"
            return f"{start} → {end}"
        return start
    time_display.short_description = 'Zaman'


@admin.register(TimelineNodeInteraction)
class TimelineNodeInteractionAdmin(admin.ModelAdmin):
    """TimelineNodeInteraction admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'node_info',
        'interaction_type',
        'video_ts_display',
        'created_at',
    ]
    
    list_filter = [
        'interaction_type',
        'tenant',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'node__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'node',
        'user',
        'session',
        'interaction_type',
        'data',
        'video_ts',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def node_info(self, obj):
        return f"{obj.node.get_node_type_display()} @ {obj.node.start_ts}s"
    node_info.short_description = 'Node'
    
    def video_ts_display(self, obj):
        if obj.video_ts is None:
            return '-'
        return f"{obj.video_ts // 60}:{obj.video_ts % 60:02d}"
    video_ts_display.short_description = 'Video Zamanı'

