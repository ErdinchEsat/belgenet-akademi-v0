"""
Timeline Serializers
====================

Timeline API serializer'ları.
"""

from rest_framework import serializers

from .models import TimelineNode, TimelineNodeInteraction


class TimelineNodeSerializer(serializers.ModelSerializer):
    """
    Timeline node serializer.
    
    GET /api/v1/courses/{courseId}/content/{contentId}/timeline/
    """
    
    duration = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TimelineNode
        fields = [
            'id',
            'node_type',
            'start_ts',
            'end_ts',
            'title',
            'config',
            'is_blocking',
            'is_required',
            'order',
            'duration',
        ]


class TimelineResponseSerializer(serializers.Serializer):
    """
    Timeline response serializer.
    
    Response:
    {
        "content_id": 123,
        "nodes": [...],
        "chapters": [...]
    }
    """
    
    content_id = serializers.IntegerField()
    total_nodes = serializers.IntegerField()
    nodes = TimelineNodeSerializer(many=True)
    chapters = serializers.ListField(
        child=serializers.DictField(),
        help_text='Sadece chapter node\'ları (timeline navigasyonu için)',
    )


class InteractionCreateSerializer(serializers.Serializer):
    """
    Etkileşim oluşturma request serializer.
    
    POST /api/v1/courses/{courseId}/content/{contentId}/timeline/{nodeId}/interact/
    """
    
    interaction_type = serializers.ChoiceField(
        choices=TimelineNodeInteraction.InteractionType.choices,
    )
    
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    
    video_ts = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    
    data = serializers.JSONField(
        required=False,
        default=dict,
    )


class InteractionResponseSerializer(serializers.ModelSerializer):
    """Etkileşim response serializer."""
    
    class Meta:
        model = TimelineNodeInteraction
        fields = [
            'id',
            'node',
            'interaction_type',
            'data',
            'video_ts',
            'created_at',
        ]


class PollAnswerSerializer(serializers.Serializer):
    """Poll cevabı serializer."""
    
    node_id = serializers.UUIDField()
    answer = serializers.CharField()
    session_id = serializers.UUIDField(required=False)
    video_ts = serializers.IntegerField(required=False)


class CheckpointConfirmSerializer(serializers.Serializer):
    """Checkpoint onay serializer."""
    
    node_id = serializers.UUIDField()
    session_id = serializers.UUIDField(required=False)
    video_ts = serializers.IntegerField(required=False)

