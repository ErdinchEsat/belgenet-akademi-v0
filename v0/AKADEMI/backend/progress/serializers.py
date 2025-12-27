"""
Progress Serializers
====================

Video ilerleme API serializer'ları.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import VideoProgress, ProgressWatchWindow


class ProgressResponseSerializer(serializers.ModelSerializer):
    """
    Progress GET response serializer.
    
    GET /api/v1/courses/{courseId}/content/{contentId}/progress/
    
    Response:
    {
        "watched_seconds": 1210,
        "last_position_seconds": 455,
        "completion_ratio": 0.62,
        "is_completed": false,
        "preferred_speed": 1.25,
        "preferred_caption_lang": "tr"
    }
    """
    
    class Meta:
        model = VideoProgress
        fields = [
            'watched_seconds',
            'last_position_seconds',
            'completion_ratio',
            'is_completed',
            'completed_at',
            'preferred_speed',
            'preferred_caption_lang',
            'updated_at',
        ]
        read_only_fields = fields


class ProgressUpdateSerializer(serializers.Serializer):
    """
    Progress update request serializer.
    
    PUT /api/v1/courses/{courseId}/content/{contentId}/progress/
    
    Request:
    {
        "session_id": "uuid",
        "last_position_seconds": 455,
        "client_watched_delta_seconds": 10,
        "playback_rate": 1.25,
        "caption_lang": "tr",
        "client_ts": "2025-12-26T10:05:10Z"
    }
    """
    
    session_id = serializers.UUIDField(
        required=True,
        help_text='Aktif playback session ID',
    )
    
    last_position_seconds = serializers.IntegerField(
        min_value=0,
        required=True,
        help_text='Mevcut video pozisyonu',
    )
    
    client_watched_delta_seconds = serializers.IntegerField(
        min_value=0,
        max_value=60,  # Maksimum 60 saniye (abuse prevention)
        required=False,
        default=0,
        help_text='Son güncellemeden bu yana izlenen süre',
    )
    
    playback_rate = serializers.FloatField(
        min_value=0.25,
        max_value=4.0,
        required=False,
        default=1.0,
        help_text='Oynatma hızı',
    )
    
    caption_lang = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Altyazı dili',
    )
    
    client_ts = serializers.DateTimeField(
        required=False,
        default=timezone.now,
        help_text='Client timestamp',
    )
    
    def validate_client_watched_delta_seconds(self, value):
        """Delta süre doğrulaması."""
        # Gerçek zamanda izlenenden fazla olamaz
        # Örn: 10 saniyelik update aralığında 60 saniye izlenemez
        # (playback_rate ile çarpılabilir: 2x hızda 20 saniye)
        playback_rate = self.initial_data.get('playback_rate', 1.0)
        max_possible = 15 * float(playback_rate)  # 15 saniye margin
        
        if value > max_possible:
            # Fazla süreyi kes, hata verme
            return int(max_possible)
        
        return value


class ProgressUpdateResponseSerializer(serializers.Serializer):
    """
    Progress update response serializer.
    
    Response 200:
    {
        "content_id": "uuid",
        "watched_seconds": 1210,
        "last_position_seconds": 455,
        "completion_ratio": 0.62,
        "is_completed": false,
        "updated_at": "2025-12-26T10:05:11Z"
    }
    """
    
    content_id = serializers.IntegerField()
    watched_seconds = serializers.IntegerField()
    last_position_seconds = serializers.IntegerField()
    completion_ratio = serializers.FloatField()
    is_completed = serializers.BooleanField()
    updated_at = serializers.DateTimeField()


class WatchWindowSerializer(serializers.ModelSerializer):
    """İzleme penceresi serializer."""
    
    class Meta:
        model = ProgressWatchWindow
        fields = [
            'id',
            'start_video_ts',
            'end_video_ts',
            'duration_seconds',
            'playback_rate',
            'is_verified',
            'created_at',
        ]
        read_only_fields = fields

