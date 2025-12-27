"""
AI Serializers
==============

AI API serializer'ları.
"""

from rest_framework import serializers

from .models import (
    Transcript, TranscriptSegment, 
    AIConversation, AIMessage, 
    VideoSummary, AIQuota
)


# ============ Transcript Serializers ============

class TranscriptSegmentSerializer(serializers.ModelSerializer):
    """Transkript segmenti serializer."""
    
    class Meta:
        model = TranscriptSegment
        fields = [
            'id',
            'start_ts',
            'end_ts',
            'text',
            'sequence',
            'speaker',
        ]


class TranscriptResponseSerializer(serializers.ModelSerializer):
    """Transkript response serializer."""
    
    segments = TranscriptSegmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Transcript
        fields = [
            'id',
            'language',
            'source',
            'status',
            'word_count',
            'segment_count',
            'duration_seconds',
            'segments',
        ]


class TranscriptListSerializer(serializers.ModelSerializer):
    """Transkript liste serializer."""
    
    class Meta:
        model = Transcript
        fields = [
            'id',
            'language',
            'source',
            'status',
            'word_count',
        ]


class TranscriptSearchResultSerializer(serializers.Serializer):
    """Transkript arama sonucu serializer."""
    
    segment_id = serializers.UUIDField()
    start_ts = serializers.FloatField()
    end_ts = serializers.FloatField()
    text = serializers.CharField()
    highlight = serializers.CharField()
    relevance = serializers.FloatField()


class TranscriptSearchResponseSerializer(serializers.Serializer):
    """Transkript arama response serializer."""
    
    query = serializers.CharField()
    total = serializers.IntegerField()
    results = TranscriptSearchResultSerializer(many=True)


# ============ AI Chat Serializers ============

class AskQuestionSerializer(serializers.Serializer):
    """Soru sorma request serializer."""
    
    question = serializers.CharField(max_length=2000)
    
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text='Mevcut konuşmaya devam etmek için',
    )
    
    video_ts = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Sorunun ilişkili olduğu video zamanı',
    )
    
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    
    include_transcript = serializers.BooleanField(
        default=True,
        help_text='Transkripti context olarak ekle',
    )
    
    include_notes = serializers.BooleanField(
        default=False,
        help_text='Kullanıcı notlarını context olarak ekle',
    )


class AIMessageSerializer(serializers.ModelSerializer):
    """AI mesaj serializer."""
    
    class Meta:
        model = AIMessage
        fields = [
            'id',
            'role',
            'content',
            'video_ts',
            'sources',
            'created_at',
        ]


class AskQuestionResponseSerializer(serializers.Serializer):
    """Soru cevap response serializer."""
    
    conversation_id = serializers.UUIDField()
    message = AIMessageSerializer()
    sources = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    quota = serializers.DictField(required=False)


class ConversationSerializer(serializers.ModelSerializer):
    """Konuşma serializer."""
    
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = AIConversation
        fields = [
            'id',
            'title',
            'message_count',
            'last_activity_at',
            'last_message',
            'created_at',
        ]
    
    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'role': last.role,
                'content': last.content[:100] + '...' if len(last.content) > 100 else last.content,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Konuşma detay serializer."""
    
    messages = AIMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = AIConversation
        fields = [
            'id',
            'title',
            'context',
            'message_count',
            'last_activity_at',
            'messages',
            'created_at',
        ]


# ============ Summary Serializers ============

class SummaryRequestSerializer(serializers.Serializer):
    """Özet oluşturma request serializer."""
    
    summary_type = serializers.ChoiceField(
        choices=VideoSummary.SummaryType.choices,
        default=VideoSummary.SummaryType.BRIEF,
    )
    
    language = serializers.CharField(
        max_length=10,
        default='tr',
    )
    
    start_ts = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Bölüm özeti için başlangıç',
    )
    
    end_ts = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='Bölüm özeti için bitiş',
    )


class SummaryResponseSerializer(serializers.ModelSerializer):
    """Özet response serializer."""
    
    class Meta:
        model = VideoSummary
        fields = [
            'id',
            'summary_type',
            'language',
            'summary_text',
            'start_ts',
            'end_ts',
            'created_at',
        ]


# ============ Quota Serializers ============

class QuotaSerializer(serializers.ModelSerializer):
    """Kota serializer."""
    
    can_ask_question = serializers.BooleanField(read_only=True)
    remaining_questions = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = AIQuota
        fields = [
            'daily_questions_limit',
            'daily_questions_used',
            'monthly_tokens_limit',
            'monthly_tokens_used',
            'can_ask_question',
            'remaining_questions',
            'daily_reset_at',
        ]

