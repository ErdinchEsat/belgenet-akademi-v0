"""
Telemetry Serializers
=====================

Event tracking API serializer'ları.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import TelemetryEvent


class SingleEventSerializer(serializers.Serializer):
    """
    Tek event serializer.
    
    Batch içindeki her event için kullanılır.
    """
    
    client_event_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text='Client tarafından üretilen benzersiz event ID',
    )
    
    event_type = serializers.ChoiceField(
        choices=TelemetryEvent.EventType.choices,
        required=True,
    )
    
    video_ts = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text='Video pozisyonu (saniye)',
    )
    
    client_ts = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Client zaman damgası',
    )
    
    payload = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text='Event\'e özgü ek veriler',
    )
    
    def validate_client_event_id(self, value):
        """Client event ID boş olamaz."""
        if not value or not value.strip():
            raise serializers.ValidationError("client_event_id boş olamaz")
        return value.strip()


class EventBatchSerializer(serializers.Serializer):
    """
    Event batch request serializer.
    
    POST /api/v1/courses/{courseId}/content/{contentId}/events/
    
    Request:
    {
        "session_id": "uuid",
        "events": [
            {
                "client_event_id": "evt-001",
                "event_type": "play",
                "video_ts": 440,
                "client_ts": "2025-12-26T10:05:20Z",
                "payload": {"autoplay": false}
            }
        ]
    }
    """
    
    session_id = serializers.UUIDField(
        required=True,
        help_text='Aktif playback session ID',
    )
    
    events = SingleEventSerializer(
        many=True,
        required=True,
        help_text='Event listesi',
    )
    
    def validate_events(self, value):
        """Event listesi boş olamaz ve max 100 event."""
        if not value:
            raise serializers.ValidationError("En az 1 event gerekli")
        if len(value) > 100:
            raise serializers.ValidationError("Maksimum 100 event gönderilebilir")
        return value


class EventBatchResponseSerializer(serializers.Serializer):
    """
    Event batch response serializer.
    
    Response 202:
    {
        "accepted": 5,
        "deduped": 1,
        "rejected": 0,
        "errors": []
    }
    """
    
    accepted = serializers.IntegerField(help_text='Kabul edilen event sayısı')
    deduped = serializers.IntegerField(help_text='Dedupe nedeniyle atlanan sayısı')
    rejected = serializers.IntegerField(help_text='Reddedilen event sayısı')
    errors = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='Hata detayları',
    )


class TelemetryEventSerializer(serializers.ModelSerializer):
    """TelemetryEvent model serializer."""
    
    class Meta:
        model = TelemetryEvent
        fields = [
            'id',
            'client_event_id',
            'event_type',
            'video_ts',
            'server_ts',
            'client_ts',
            'payload',
        ]
        read_only_fields = fields

