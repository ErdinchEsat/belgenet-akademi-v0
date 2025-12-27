"""
Live Session Admin
==================

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionAttendanceSummary,
    LiveSessionRecording,
    LiveSessionArtifact,
    LiveSessionPolicy,
    LiveProviderConfig,
)


@admin.register(LiveProviderConfig)
class LiveProviderConfigAdmin(admin.ModelAdmin):
    """Sağlayıcı konfigürasyonu admin."""
    
    list_display = ['tenant', 'provider', 'is_active', 'is_default', 'created_at']
    list_filter = ['provider', 'is_active', 'is_default']
    search_fields = ['tenant__name', 'jitsi_domain', 'bbb_server_url']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('tenant', 'provider', 'is_active', 'is_default')
        }),
        (_('Jitsi Ayarları'), {
            'fields': ('jitsi_domain', 'jitsi_app_id', 'jitsi_jwt_secret'),
            'classes': ('collapse',),
        }),
        (_('BBB Ayarları'), {
            'fields': ('bbb_server_url', 'bbb_shared_secret'),
            'classes': ('collapse',),
        }),
        (_('Zoom Ayarları'), {
            'fields': ('zoom_account_id', 'zoom_client_id', 'zoom_client_secret'),
            'classes': ('collapse',),
        }),
        (_('Genel'), {
            'fields': ('max_concurrent_rooms', 'default_room_duration_minutes'),
        }),
        (_('Meta'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


class LiveSessionParticipantInline(admin.TabularInline):
    """Katılımcı inline."""
    
    model = LiveSessionParticipant
    extra = 0
    readonly_fields = ['user', 'role', 'joined_at', 'left_at', 'duration_seconds', 'is_active']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class LiveSessionRecordingInline(admin.TabularInline):
    """Kayıt inline."""
    
    model = LiveSessionRecording
    extra = 0
    readonly_fields = ['provider_recording_id', 'status', 'duration_seconds', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    """Canlı ders admin."""
    
    list_display = [
        'title', 'course', 'type', 'status_badge', 'provider',
        'scheduled_start', 'participant_count', 'created_by'
    ]
    list_filter = ['status', 'type', 'provider', 'tenant', 'created_at']
    search_fields = ['title', 'room_id', 'course__title', 'created_by__email']
    readonly_fields = [
        'id', 'room_id', 'room_url', 'participant_count', 'peak_participants',
        'total_duration_minutes', 'actual_start', 'actual_end',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['course', 'content', 'created_by']
    date_hierarchy = 'scheduled_start'
    
    inlines = [LiveSessionParticipantInline, LiveSessionRecordingInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'type', 'status')
        }),
        (_('İlişkiler'), {
            'fields': ('tenant', 'course', 'content', 'created_by'),
        }),
        (_('Zamanlama'), {
            'fields': (
                ('scheduled_start', 'scheduled_end'),
                ('actual_start', 'actual_end'),
                'total_duration_minutes',
            ),
        }),
        (_('Provider'), {
            'fields': ('provider', 'room_id', 'room_url', 'room_password'),
        }),
        (_('Ayarlar'), {
            'fields': (
                'max_participants',
                ('recording_enabled', 'auto_recording'),
                'waiting_room_enabled',
                ('students_can_share_screen', 'students_start_muted', 'students_video_off'),
            ),
        }),
        (_('İstatistikler'), {
            'fields': ('participant_count', 'peak_participants'),
            'classes': ('collapse',),
        }),
        (_('Meta'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def status_badge(self, obj):
        """Durum badge'i."""
        colors = {
            'draft': '#6b7280',
            'scheduled': '#3b82f6',
            'live': '#22c55e',
            'ended': '#6b7280',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Durum')
    
    actions = ['start_sessions', 'end_sessions', 'cancel_sessions']
    
    @admin.action(description=_('Seçili oturumları başlat'))
    def start_sessions(self, request, queryset):
        from .services.session_service import LiveSessionService
        
        count = 0
        for session in queryset.filter(status__in=['draft', 'scheduled']):
            try:
                LiveSessionService.start_session(session)
                count += 1
            except Exception as e:
                self.message_user(request, f"Hata: {session.title} - {e}", level='error')
        
        self.message_user(request, f"{count} oturum başlatıldı.")
    
    @admin.action(description=_('Seçili oturumları sonlandır'))
    def end_sessions(self, request, queryset):
        from .services.session_service import LiveSessionService
        
        count = 0
        for session in queryset.filter(status='live'):
            try:
                LiveSessionService.end_session(session)
                count += 1
            except Exception as e:
                self.message_user(request, f"Hata: {session.title} - {e}", level='error')
        
        self.message_user(request, f"{count} oturum sonlandırıldı.")
    
    @admin.action(description=_('Seçili oturumları iptal et'))
    def cancel_sessions(self, request, queryset):
        count = queryset.exclude(status='ended').update(status='cancelled')
        self.message_user(request, f"{count} oturum iptal edildi.")


@admin.register(LiveSessionParticipant)
class LiveSessionParticipantAdmin(admin.ModelAdmin):
    """Katılımcı admin."""
    
    list_display = ['user', 'session', 'role', 'joined_at', 'left_at', 'duration_seconds', 'is_active']
    list_filter = ['role', 'is_active', 'kicked', 'session__tenant']
    search_fields = ['user__email', 'user__first_name', 'session__title']
    readonly_fields = ['id', 'session', 'user', 'joined_at', 'left_at', 'duration_seconds']
    raw_id_fields = ['session', 'user']
    date_hierarchy = 'joined_at'


@admin.register(LiveSessionAttendanceSummary)
class LiveSessionAttendanceSummaryAdmin(admin.ModelAdmin):
    """Katılım özeti admin."""
    
    list_display = [
        'user', 'session', 'attended', 'attendance_percent',
        'total_duration_minutes', 'late_join', 'early_leave'
    ]
    list_filter = ['attended', 'late_join', 'early_leave', 'session__tenant']
    search_fields = ['user__email', 'session__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['session', 'user']
    
    def total_duration_minutes(self, obj):
        return obj.total_duration_minutes
    total_duration_minutes.short_description = _('Süre (dk)')


@admin.register(LiveSessionRecording)
class LiveSessionRecordingAdmin(admin.ModelAdmin):
    """Kayıt admin."""
    
    list_display = [
        'title', 'session', 'status_badge', 'duration_minutes',
        'file_size_mb', 'view_count', 'created_at'
    ]
    list_filter = ['status', 'transcript_status', 'is_public', 'session__tenant']
    search_fields = ['title', 'session__title', 'provider_recording_id']
    readonly_fields = [
        'id', 'provider_recording_id', 'provider_url',
        'file_size_bytes', 'view_count', 'download_count',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['session', 'file']
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        colors = {
            'processing': '#f59e0b',
            'ready': '#3b82f6',
            'published': '#22c55e',
            'failed': '#ef4444',
            'deleted': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Durum')
    
    def duration_minutes(self, obj):
        return obj.duration_minutes
    duration_minutes.short_description = _('Süre (dk)')
    
    def file_size_mb(self, obj):
        return obj.file_size_mb
    file_size_mb.short_description = _('Boyut (MB)')
    
    actions = ['publish_recordings', 'unpublish_recordings']
    
    @admin.action(description=_('Seçili kayıtları yayınla'))
    def publish_recordings(self, request, queryset):
        from .services.recording_service import RecordingService
        
        count = 0
        for recording in queryset.filter(status='ready'):
            try:
                RecordingService.publish_recording(recording)
                count += 1
            except Exception as e:
                self.message_user(request, f"Hata: {recording.title} - {e}", level='error')
        
        self.message_user(request, f"{count} kayıt yayınlandı.")
    
    @admin.action(description=_('Seçili kayıtları yayından kaldır'))
    def unpublish_recordings(self, request, queryset):
        from .services.recording_service import RecordingService
        
        count = 0
        for recording in queryset.filter(status='published'):
            try:
                RecordingService.unpublish_recording(recording)
                count += 1
            except Exception as e:
                self.message_user(request, f"Hata: {recording.title} - {e}", level='error')
        
        self.message_user(request, f"{count} kayıt yayından kaldırıldı.")


@admin.register(LiveSessionArtifact)
class LiveSessionArtifactAdmin(admin.ModelAdmin):
    """Çıktı admin."""
    
    list_display = ['title', 'session', 'type', 'created_at']
    list_filter = ['type', 'session__tenant']
    search_fields = ['title', 'session__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['session', 'file']


@admin.register(LiveSessionPolicy)
class LiveSessionPolicyAdmin(admin.ModelAdmin):
    """Politika admin."""
    
    list_display = ['__str__', 'attendance_threshold_percent', 'lobby_enabled', 'recording_required']
    list_filter = ['lobby_enabled', 'recording_required', 'students_can_share_screen']
    search_fields = ['tenant__name', 'course__title', 'session__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant', 'course', 'session']
    
    fieldsets = (
        (None, {
            'fields': ('tenant', 'course', 'session')
        }),
        (_('Kayıt Politikası'), {
            'fields': ('recording_required', 'auto_recording', 'recording_retention_days'),
        }),
        (_('Katılım Politikası'), {
            'fields': (
                'attendance_threshold_percent',
                'minimum_duration_minutes',
                ('late_join_tolerance_minutes', 'early_leave_tolerance_minutes'),
            ),
        }),
        (_('Güvenlik'), {
            'fields': ('lobby_enabled', 'require_authentication', 'allow_guests'),
        }),
        (_('Öğrenci İzinleri'), {
            'fields': (
                ('students_can_share_screen', 'students_can_use_whiteboard'),
                ('students_can_unmute_self', 'students_start_muted'),
                'students_video_off',
            ),
        }),
        (_('Meta'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

