"""
Telemetry Admin
===============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin

from .models import TelemetryEvent, TelemetryAggregate


@admin.register(TelemetryEvent)
class TelemetryEventAdmin(admin.ModelAdmin):
    """TelemetryEvent admin konfigürasyonu."""
    
    list_display = [
        'id',
        'event_type',
        'video_ts_display',
        'user_email',
        'content_title',
        'server_ts',
    ]
    
    list_filter = [
        'event_type',
        'tenant',
        'server_ts',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
        'client_event_id',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'session',
        'user',
        'course',
        'content',
        'client_event_id',
        'event_type',
        'video_ts',
        'server_ts',
        'client_ts',
        'payload',
    ]
    
    date_hierarchy = 'server_ts'
    ordering = ['-server_ts']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def video_ts_display(self, obj):
        if obj.video_ts is None:
            return '-'
        m, s = divmod(obj.video_ts, 60)
        return f'{m}:{s:02d}'
    video_ts_display.short_description = 'Video Zamanı'


@admin.register(TelemetryAggregate)
class TelemetryAggregateAdmin(admin.ModelAdmin):
    """TelemetryAggregate admin konfigürasyonu."""
    
    list_display = [
        'id',
        'aggregate_type',
        'content_title',
        'period_start',
        'period_end',
        'sample_count',
    ]
    
    list_filter = [
        'aggregate_type',
        'tenant',
        'period_start',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'content',
        'aggregate_type',
        'period_start',
        'period_end',
        'data',
        'sample_count',
        'created_at',
        'updated_at',
    ]
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'

