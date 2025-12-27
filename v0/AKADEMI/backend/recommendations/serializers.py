"""
Recommendations Serializers
===========================

Recommendations API serializer'ları.
"""

from rest_framework import serializers

from .models import (
    UserContentInterest,
    Recommendation,
    RecommendationFeedback,
    TrendingContent,
)


class RecommendedContentSerializer(serializers.Serializer):
    """Önerilen içerik serializer."""
    
    recommendation_id = serializers.UUIDField()
    content_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    thumbnail_url = serializers.URLField(allow_null=True)
    duration_minutes = serializers.IntegerField()
    instructor_name = serializers.CharField()
    recommendation_type = serializers.CharField()
    score = serializers.FloatField()
    rank = serializers.IntegerField()
    reason = serializers.CharField(allow_blank=True)


class RecommendationsResponseSerializer(serializers.Serializer):
    """Öneriler response serializer."""
    
    total = serializers.IntegerField()
    recommendations = RecommendedContentSerializer(many=True)


class NextContentSerializer(serializers.Serializer):
    """Sonraki içerik önerisi serializer."""
    
    content_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    duration_minutes = serializers.IntegerField()
    reason = serializers.CharField()
    auto_play = serializers.BooleanField(default=False)


class SimilarContentSerializer(serializers.Serializer):
    """Benzer içerik serializer."""
    
    content_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    title = serializers.CharField()
    thumbnail_url = serializers.URLField(allow_null=True)
    duration_minutes = serializers.IntegerField()
    similarity_score = serializers.FloatField()


class TrendingContentSerializer(serializers.ModelSerializer):
    """Trend içerik serializer."""
    
    content_id = serializers.IntegerField(source='content.id')
    title = serializers.CharField(source='content.title')
    course_id = serializers.IntegerField(source='content.module.course.id')
    course_title = serializers.CharField(source='content.module.course.title')
    
    class Meta:
        model = TrendingContent
        fields = [
            'content_id',
            'title',
            'course_id',
            'course_title',
            'rank',
            'score',
            'view_count',
            'completion_count',
        ]


class FeedbackRequestSerializer(serializers.Serializer):
    """Geri bildirim request serializer."""
    
    recommendation_id = serializers.UUIDField()
    feedback_type = serializers.ChoiceField(
        choices=RecommendationFeedback.FeedbackType.choices,
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )


class FeedbackResponseSerializer(serializers.ModelSerializer):
    """Geri bildirim response serializer."""
    
    class Meta:
        model = RecommendationFeedback
        fields = [
            'id',
            'feedback_type',
            'comment',
            'created_at',
        ]


class UserInterestSerializer(serializers.ModelSerializer):
    """Kullanıcı ilgi profili serializer."""
    
    class Meta:
        model = UserContentInterest
        fields = [
            'category_scores',
            'tag_scores',
            'preferred_duration',
            'preferred_difficulty',
            'total_watch_time',
            'total_completions',
            'avg_completion_rate',
            'last_activity_at',
        ]


class RecommendationClickSerializer(serializers.Serializer):
    """Öneri tıklama kaydı serializer."""
    
    recommendation_id = serializers.UUIDField()

