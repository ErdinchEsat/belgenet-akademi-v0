"""
Player Serializers
==================

Playback session API serializer'ları.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import PlaybackSession


class PlaybackSessionCreateSerializer(serializers.Serializer):
    """
    Session oluşturma request serializer.
    
    POST /api/v1/courses/{courseId}/content/{contentId}/sessions/
    """
    
    device_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Client tarafından üretilen benzersiz cihaz ID',
    )
    
    user_agent = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ResumeInfoSerializer(serializers.Serializer):
    """Resume bilgisi serializer."""
    
    last_position_seconds = serializers.IntegerField()
    watched_seconds = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    completion_ratio = serializers.FloatField()


class PlaybackSessionResponseSerializer(serializers.Serializer):
    """
    Session oluşturma response serializer.
    
    Response 201:
    {
        "session_id": "uuid",
        "server_time": "2025-12-26T10:00:00Z",
        "resume": {
            "last_position_seconds": 420,
            "watched_seconds": 1200,
            "is_completed": false,
            "completion_ratio": 0.62
        }
    }
    """
    
    session_id = serializers.UUIDField(source='id')
    server_time = serializers.DateTimeField(default=timezone.now)
    resume = ResumeInfoSerializer()


class PlaybackSessionSerializer(serializers.ModelSerializer):
    """PlaybackSession model serializer."""
    
    session_id = serializers.UUIDField(source='id', read_only=True)
    duration_seconds = serializers.IntegerField(read_only=True)
    is_stale = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PlaybackSession
        fields = [
            'session_id',
            'course',
            'content',
            'device_id',
            'started_at',
            'ended_at',
            'ended_reason',
            'last_heartbeat_at',
            'last_position_seconds',
            'is_active',
            'duration_seconds',
            'is_stale',
        ]
        read_only_fields = [
            'session_id',
            'started_at',
            'ended_at',
            'ended_reason',
            'last_heartbeat_at',
            'is_active',
            'duration_seconds',
            'is_stale',
        ]


class HeartbeatSerializer(serializers.Serializer):
    """
    Heartbeat request serializer.
    
    PUT /api/v1/courses/{courseId}/content/{contentId}/sessions/{sessionId}/heartbeat/
    """
    
    position_seconds = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text='Mevcut video pozisyonu (saniye)',
    )
    
    playback_rate = serializers.FloatField(
        min_value=0.25,
        max_value=4.0,
        required=False,
        default=1.0,
        help_text='Oynatma hızı',
    )


class EndSessionSerializer(serializers.Serializer):
    """
    Session sonlandırma request serializer.
    
    PUT /api/v1/courses/{courseId}/content/{contentId}/sessions/{sessionId}/end/
    """
    
    reason = serializers.ChoiceField(
        choices=PlaybackSession.EndReason.choices,
        required=False,
        default=PlaybackSession.EndReason.ENDED,
    )
    
    final_position_seconds = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text='Son video pozisyonu',
    )

