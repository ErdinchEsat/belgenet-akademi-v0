"""
Integrity Serializers
=====================

Integrity API serializer'ları.
"""

from rest_framework import serializers

from .models import (
    DeviceFingerprint,
    IntegrityCheck,
    PlaybackAnomaly,
    UserIntegrityScore,
)


class DeviceFingerprintSerializer(serializers.Serializer):
    """Cihaz parmak izi request serializer."""
    
    fingerprint_hash = serializers.CharField(max_length=255)
    device_type = serializers.CharField(max_length=50, required=False)
    os = serializers.CharField(max_length=100, required=False)
    browser = serializers.CharField(max_length=100, required=False)
    user_agent = serializers.CharField(required=False)
    screen_resolution = serializers.CharField(max_length=50, required=False)
    timezone = serializers.CharField(max_length=100, required=False)
    language = serializers.CharField(max_length=20, required=False)


class IntegrityVerifyRequestSerializer(serializers.Serializer):
    """Bütünlük doğrulama request serializer."""
    
    session_id = serializers.UUIDField()
    video_position = serializers.IntegerField(min_value=0)
    
    # Client tarafından hesaplanan metrikler
    tab_visibility_ratio = serializers.FloatField(
        min_value=0, max_value=1,
        help_text='0-1 arası, tab aktif olma oranı',
    )
    
    playback_speed = serializers.FloatField(
        min_value=0.25, max_value=16,
        default=1.0,
    )
    
    seek_count = serializers.IntegerField(
        min_value=0,
        default=0,
    )
    
    pause_count = serializers.IntegerField(
        min_value=0,
        default=0,
    )
    
    total_pause_duration = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text='Toplam duraklatma süresi (saniye)',
    )
    
    # Zaman bilgileri
    client_timestamp = serializers.DateTimeField()
    elapsed_seconds = serializers.IntegerField(
        min_value=0,
        help_text='Son kontrolden bu yana geçen gerçek süre',
    )
    
    # Cihaz bilgisi
    device_fingerprint = DeviceFingerprintSerializer(required=False)


class IntegrityCheckResponseSerializer(serializers.ModelSerializer):
    """Bütünlük kontrol response serializer."""
    
    class Meta:
        model = IntegrityCheck
        fields = [
            'id',
            'status',
            'visibility_score',
            'playback_score',
            'timing_score',
            'overall_score',
            'checks_performed',
            'created_at',
        ]


class IntegrityStatusResponseSerializer(serializers.Serializer):
    """Bütünlük durumu response serializer."""
    
    user_score = serializers.IntegerField()
    risk_level = serializers.CharField()
    is_restricted = serializers.BooleanField()
    total_checks = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    recent_anomalies = serializers.IntegerField()
    last_check_at = serializers.DateTimeField(allow_null=True)


class AnomalyReportSerializer(serializers.Serializer):
    """Anomali raporu request serializer."""
    
    session_id = serializers.UUIDField()
    anomaly_type = serializers.ChoiceField(
        choices=PlaybackAnomaly.AnomalyType.choices,
    )
    description = serializers.CharField(max_length=500)
    details = serializers.JSONField(required=False, default=dict)
    video_ts = serializers.IntegerField(min_value=0, required=False)


class AnomalyResponseSerializer(serializers.ModelSerializer):
    """Anomali response serializer."""
    
    class Meta:
        model = PlaybackAnomaly
        fields = [
            'id',
            'anomaly_type',
            'severity',
            'description',
            'video_ts',
            'created_at',
        ]


class UserIntegrityScoreSerializer(serializers.ModelSerializer):
    """Kullanıcı bütünlük skoru serializer."""
    
    pass_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = UserIntegrityScore
        fields = [
            'score',
            'total_checks',
            'passed_checks',
            'failed_checks',
            'anomaly_count',
            'risk_level',
            'is_restricted',
            'pass_rate',
            'last_check_at',
        ]

