"""
Live Session Serializers
========================

Canlı ders API serializer'ları.
"""

from rest_framework import serializers
from django.utils import timezone
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


class LiveProviderConfigSerializer(serializers.ModelSerializer):
    """Sağlayıcı konfigürasyonu serializer."""
    
    # Secrets masked
    jitsi_jwt_secret = serializers.SerializerMethodField()
    bbb_shared_secret = serializers.SerializerMethodField()
    zoom_client_secret = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveProviderConfig
        fields = [
            'id', 'provider', 'is_active', 'is_default',
            'jitsi_domain', 'jitsi_app_id', 'jitsi_jwt_secret',
            'bbb_server_url', 'bbb_shared_secret',
            'zoom_account_id', 'zoom_client_id', 'zoom_client_secret',
            'max_concurrent_rooms', 'default_room_duration_minutes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_jitsi_jwt_secret(self, obj):
        """JWT secret masked."""
        if obj.jitsi_jwt_secret:
            return '********'
        return ''
    
    def get_bbb_shared_secret(self, obj):
        """BBB secret masked."""
        if obj.bbb_shared_secret:
            return '********'
        return ''
    
    def get_zoom_client_secret(self, obj):
        """Zoom secret masked."""
        if obj.zoom_client_secret:
            return '********'
        return ''


class LiveProviderConfigWriteSerializer(serializers.ModelSerializer):
    """Sağlayıcı konfigürasyonu write serializer (secrets dahil)."""
    
    class Meta:
        model = LiveProviderConfig
        fields = [
            'provider', 'is_active', 'is_default',
            'jitsi_domain', 'jitsi_app_id', 'jitsi_jwt_secret',
            'bbb_server_url', 'bbb_shared_secret',
            'zoom_account_id', 'zoom_client_id', 'zoom_client_secret',
            'max_concurrent_rooms', 'default_room_duration_minutes',
        ]


class LiveSessionPolicySerializer(serializers.ModelSerializer):
    """Canlı ders politikası serializer."""
    
    class Meta:
        model = LiveSessionPolicy
        fields = [
            'id',
            'recording_required', 'auto_recording', 'recording_retention_days',
            'attendance_threshold_percent', 'minimum_duration_minutes',
            'late_join_tolerance_minutes', 'early_leave_tolerance_minutes',
            'lobby_enabled', 'require_authentication', 'allow_guests',
            'students_can_share_screen', 'students_can_use_whiteboard',
            'students_can_unmute_self', 'students_start_muted', 'students_video_off',
        ]
        read_only_fields = ['id']


class LiveSessionListSerializer(serializers.ModelSerializer):
    """Canlı ders listesi serializer."""
    
    course_title = serializers.CharField(source='course.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    can_join = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'type', 'status',
            'course', 'course_title',
            'scheduled_start', 'scheduled_end',
            'actual_start', 'actual_end',
            'provider', 'room_id',
            'max_participants', 'participant_count', 'peak_participants',
            'recording_enabled', 'waiting_room_enabled',
            'created_by', 'created_by_name',
            'duration_minutes', 'total_duration_minutes',
            'is_live', 'is_upcoming', 'can_join',
            'created_at', 'updated_at',
        ]


class LiveSessionDetailSerializer(serializers.ModelSerializer):
    """Canlı ders detay serializer."""
    
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_slug = serializers.CharField(source='course.slug', read_only=True)
    content_title = serializers.CharField(source='content.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    created_by_avatar = serializers.SerializerMethodField()
    
    duration_minutes = serializers.IntegerField(read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    can_join = serializers.BooleanField(read_only=True)
    
    recordings_count = serializers.SerializerMethodField()
    active_participants_count = serializers.SerializerMethodField()
    policy = LiveSessionPolicySerializer(read_only=True)
    
    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'type', 'status',
            'course', 'course_title', 'course_slug',
            'content', 'content_title',
            'scheduled_start', 'scheduled_end',
            'actual_start', 'actual_end',
            'provider', 'room_id', 'room_url',
            'max_participants', 'participant_count', 'peak_participants',
            'recording_enabled', 'auto_recording', 'waiting_room_enabled',
            'students_can_share_screen', 'students_start_muted', 'students_video_off',
            'created_by', 'created_by_name', 'created_by_avatar',
            'duration_minutes', 'total_duration_minutes',
            'is_live', 'is_upcoming', 'can_join',
            'recordings_count', 'active_participants_count',
            'policy',
            'created_at', 'updated_at',
        ]
    
    def get_created_by_avatar(self, obj):
        if obj.created_by:
            return obj.created_by.get_avatar_url()
        return None
    
    def get_recordings_count(self, obj):
        return obj.recordings.filter(status='published').count()
    
    def get_active_participants_count(self, obj):
        return obj.participants.filter(is_active=True).count()


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    """Canlı ders oluşturma serializer."""
    
    class Meta:
        model = LiveSession
        fields = [
            'title', 'description', 'type',
            'course', 'content',
            'scheduled_start', 'scheduled_end',
            'max_participants',
            'recording_enabled', 'auto_recording', 'waiting_room_enabled',
            'students_can_share_screen', 'students_start_muted', 'students_video_off',
        ]
    
    def validate(self, attrs):
        """Zamanlama validasyonu."""
        scheduled_start = attrs.get('scheduled_start')
        scheduled_end = attrs.get('scheduled_end')
        
        if scheduled_start and scheduled_end:
            if scheduled_end <= scheduled_start:
                raise serializers.ValidationError({
                    'scheduled_end': _('Bitiş zamanı başlangıçtan sonra olmalı.')
                })
            
            # Minimum 5 dakika
            duration = (scheduled_end - scheduled_start).total_seconds() / 60
            if duration < 5:
                raise serializers.ValidationError({
                    'scheduled_end': _('Ders süresi en az 5 dakika olmalı.')
                })
        
        # Type=ADHOC için scheduled_start şimdi olabilir
        session_type = attrs.get('type', LiveSession.Type.SCHEDULED)
        if session_type == LiveSession.Type.ADHOC:
            if not scheduled_start:
                attrs['scheduled_start'] = timezone.now()
            if not scheduled_end:
                attrs['scheduled_end'] = timezone.now() + timezone.timedelta(hours=2)
        
        return attrs


class LiveSessionUpdateSerializer(serializers.ModelSerializer):
    """Canlı ders güncelleme serializer."""
    
    class Meta:
        model = LiveSession
        fields = [
            'title', 'description',
            'scheduled_start', 'scheduled_end',
            'max_participants',
            'recording_enabled', 'auto_recording', 'waiting_room_enabled',
            'students_can_share_screen', 'students_start_muted', 'students_video_off',
        ]
    
    def validate(self, attrs):
        """Güncelleme validasyonu."""
        instance = self.instance
        
        # Status kontrolü
        if instance and instance.status in [LiveSession.Status.ENDED, LiveSession.Status.CANCELLED]:
            raise serializers.ValidationError(_('Bitmiş veya iptal edilmiş ders güncellenemez.'))
        
        # Zamanlama validasyonu
        scheduled_start = attrs.get('scheduled_start', instance.scheduled_start if instance else None)
        scheduled_end = attrs.get('scheduled_end', instance.scheduled_end if instance else None)
        
        if scheduled_start and scheduled_end and scheduled_end <= scheduled_start:
            raise serializers.ValidationError({
                'scheduled_end': _('Bitiş zamanı başlangıçtan sonra olmalı.')
            })
        
        return attrs


class JoinResponseSerializer(serializers.Serializer):
    """Katılım yanıtı serializer."""
    
    join_url = serializers.URLField()
    token = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    role = serializers.CharField()
    session_id = serializers.UUIDField()
    room_id = serializers.CharField()
    provider = serializers.CharField()


class HeartbeatSerializer(serializers.Serializer):
    """Heartbeat request serializer."""
    
    is_active = serializers.BooleanField(default=True)
    is_background = serializers.BooleanField(default=False)
    video_enabled = serializers.BooleanField(default=False)
    audio_enabled = serializers.BooleanField(default=False)


class LiveSessionParticipantSerializer(serializers.ModelSerializer):
    """Oturum katılımcısı serializer."""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveSessionParticipant
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_avatar',
            'role', 'joined_at', 'left_at', 'duration_seconds', 'duration_minutes',
            'device_type', 'is_active', 'kicked', 'last_heartbeat',
        ]
    
    def get_user_avatar(self, obj):
        return obj.user.get_avatar_url()
    
    def get_duration_minutes(self, obj):
        return obj.duration_seconds // 60


class LiveSessionAttendanceSummarySerializer(serializers.ModelSerializer):
    """Katılım özeti serializer."""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    total_duration_minutes = serializers.IntegerField(read_only=True)
    effective_duration_seconds = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = LiveSessionAttendanceSummary
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_avatar',
            'total_duration_seconds', 'total_duration_minutes',
            'effective_duration_seconds', 'join_count',
            'first_join', 'last_leave',
            'attended', 'attendance_percent',
            'late_join', 'early_leave',
            'background_duration_seconds',
        ]
    
    def get_user_avatar(self, obj):
        return obj.user.get_avatar_url()


class AttendanceReportSerializer(serializers.Serializer):
    """Yoklama raporu serializer."""
    
    session = LiveSessionListSerializer()
    total_enrolled = serializers.IntegerField()
    total_attended = serializers.IntegerField()
    attendance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    summaries = LiveSessionAttendanceSummarySerializer(many=True)


class LiveSessionRecordingSerializer(serializers.ModelSerializer):
    """Ders kaydı serializer."""
    
    session_title = serializers.CharField(source='session.title', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    file_size_mb = serializers.FloatField(read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveSessionRecording
        fields = [
            'id', 'session', 'session_title',
            'title', 'duration_seconds', 'duration_minutes',
            'file_size_bytes', 'file_size_mb', 'format', 'resolution',
            'thumbnail_url', 'storage_url', 'download_url',
            'transcript_status', 'transcript_url',
            'status', 'is_public', 'published_at',
            'view_count', 'download_count',
            'expires_at', 'created_at',
        ]
    
    def get_download_url(self, obj):
        """Signed download URL oluştur."""
        if obj.file:
            from backend.storage.services.storage_service import StorageService
            return StorageService.get_download_url(obj.file)
        return obj.storage_url


class LiveSessionRecordingPublishSerializer(serializers.Serializer):
    """Kayıt yayınlama serializer."""
    
    is_public = serializers.BooleanField(default=False)
    title = serializers.CharField(max_length=200, required=False)


class LiveSessionArtifactSerializer(serializers.ModelSerializer):
    """Oturum çıktısı serializer."""
    
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveSessionArtifact
        fields = [
            'id', 'session', 'type', 'title',
            'content', 'metadata', 'download_url',
            'created_at',
        ]
    
    def get_download_url(self, obj):
        if obj.file:
            from backend.storage.services.storage_service import StorageService
            return StorageService.get_download_url(obj.file)
        return None


class CalendarEventSerializer(serializers.Serializer):
    """Takvim etkinliği serializer (ICS için)."""
    
    session_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    location = serializers.URLField()  # Join URL
    organizer_name = serializers.CharField()
    organizer_email = serializers.EmailField()

