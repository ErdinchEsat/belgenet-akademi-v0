"""
Sequencing Serializers
======================

İçerik kilitleme API serializer'ları.
"""

from rest_framework import serializers

from .models import ContentLockPolicy, ContentUnlockState


class PolicyRequirementSerializer(serializers.Serializer):
    """Policy gereksinimi serializer."""
    
    type = serializers.CharField()
    passed = serializers.BooleanField()
    details = serializers.DictField(required=False)


class LockStatusSerializer(serializers.Serializer):
    """
    Kilit durumu response serializer.
    
    GET /api/v1/courses/{courseId}/content/{contentId}/lock/
    
    Response:
    {
        "content_id": 123,
        "is_unlocked": false,
        "requirements": [
            {"type": "min_watch_ratio", "passed": false, "details": {"current": 0.62, "required": 0.80}},
            {"type": "requires_quiz_pass", "passed": false, "details": {"quiz_id": "uuid", "passed": false}}
        ]
    }
    """
    
    content_id = serializers.IntegerField()
    is_unlocked = serializers.BooleanField()
    unlocked_at = serializers.DateTimeField(allow_null=True)
    requirements = PolicyRequirementSerializer(many=True)


class EvaluateResponseSerializer(serializers.Serializer):
    """
    Kilit değerlendirme response serializer.
    
    POST /api/v1/courses/{courseId}/content/{contentId}/lock/evaluate/
    
    Response:
    {
        "content_id": 123,
        "is_unlocked": true,
        "unlocked_at": "2025-12-26T10:20:00Z",
        "changed": true
    }
    """
    
    content_id = serializers.IntegerField()
    is_unlocked = serializers.BooleanField()
    unlocked_at = serializers.DateTimeField(allow_null=True)
    changed = serializers.BooleanField(help_text='Durum değişti mi?')


class ContentLockPolicySerializer(serializers.ModelSerializer):
    """ContentLockPolicy model serializer."""
    
    class Meta:
        model = ContentLockPolicy
        fields = [
            'id',
            'content',
            'policy_type',
            'policy_config',
            'is_active',
            'priority',
        ]


class ContentUnlockStateSerializer(serializers.ModelSerializer):
    """ContentUnlockState model serializer."""
    
    class Meta:
        model = ContentUnlockState
        fields = [
            'id',
            'content',
            'is_unlocked',
            'unlocked_at',
            'unlock_reason',
            'evaluation_state',
            'last_evaluated_at',
        ]
        read_only_fields = fields

