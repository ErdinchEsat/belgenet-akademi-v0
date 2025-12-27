"""
Integrity Admin
===============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    DeviceFingerprint,
    IntegrityCheck,
    PlaybackAnomaly,
    UserIntegrityScore,
    IntegrityConfig,
)


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(admin.ModelAdmin):
    """DeviceFingerprint admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'device_type',
        'os',
        'browser',
        'trust_score',
        'is_trusted',
        'is_blocked',
        'session_count',
        'last_seen_at',
    ]
    
    list_filter = [
        'device_type',
        'is_trusted',
        'is_blocked',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
        'fingerprint_hash',
        'user_agent',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'fingerprint_hash',
        'first_seen_at',
        'last_seen_at',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'


@admin.register(IntegrityCheck)
class IntegrityCheckAdmin(admin.ModelAdmin):
    """IntegrityCheck admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'status_badge',
        'overall_score',
        'visibility_score',
        'playback_score',
        'timing_score',
        'video_position',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'tenant',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'session__id',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'session',
        'user',
        'device',
        'checks_performed',
        'client_data',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def status_badge(self, obj):
        colors = {
            'passed': 'green',
            'warning': 'orange',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'


@admin.register(PlaybackAnomaly)
class PlaybackAnomalyAdmin(admin.ModelAdmin):
    """PlaybackAnomaly admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'type_badge',
        'severity_badge',
        'is_reviewed',
        'action_taken',
        'created_at',
    ]
    
    list_filter = [
        'anomaly_type',
        'severity',
        'is_reviewed',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'session',
        'user',
        'content',
        'details',
        'created_at',
        'updated_at',
    ]
    
    actions = ['mark_reviewed']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title[:30]
    content_title.short_description = 'İçerik'
    
    def type_badge(self, obj):
        return format_html(
            '<span style="background-color: purple; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            obj.get_anomaly_type_display()
        )
    type_badge.short_description = 'Tür'
    
    def severity_badge(self, obj):
        colors = {
            'low': 'gray',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred',
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Şiddet'
    
    @admin.action(description='İncelendi olarak işaretle')
    def mark_reviewed(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            is_reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )


@admin.register(UserIntegrityScore)
class UserIntegrityScoreAdmin(admin.ModelAdmin):
    """UserIntegrityScore admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'score',
        'risk_badge',
        'total_checks',
        'pass_rate_display',
        'anomaly_count',
        'is_restricted',
        'last_check_at',
    ]
    
    list_filter = [
        'risk_level',
        'is_restricted',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'total_checks',
        'passed_checks',
        'failed_checks',
        'anomaly_count',
        'restricted_at',
        'last_check_at',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def risk_badge(self, obj):
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
        }
        color = colors.get(obj.risk_level, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.risk_level.upper()
        )
    risk_badge.short_description = 'Risk'
    
    def pass_rate_display(self, obj):
        return f"{obj.pass_rate:.0%}"
    pass_rate_display.short_description = 'Geçme Oranı'


@admin.register(IntegrityConfig)
class IntegrityConfigAdmin(admin.ModelAdmin):
    """IntegrityConfig admin konfigürasyonu."""
    
    list_display = [
        'id',
        'tenant_name',
        'min_overall_score',
        'auto_restrict_threshold',
        'check_interval',
        'is_enabled',
    ]
    
    list_filter = [
        'is_enabled',
    ]
    
    def tenant_name(self, obj):
        return obj.tenant.name
    tenant_name.short_description = 'Tenant'

