"""
Recommendations Admin
=====================

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    UserContentInterest,
    ContentSimilarity,
    Recommendation,
    RecommendationFeedback,
    TrendingContent,
)


@admin.register(UserContentInterest)
class UserContentInterestAdmin(admin.ModelAdmin):
    """UserContentInterest admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'total_watch_time',
        'total_completions',
        'avg_completion_rate',
        'last_activity_at',
    ]
    
    list_filter = [
        'tenant',
        'last_activity_at',
    ]
    
    search_fields = [
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'


@admin.register(ContentSimilarity)
class ContentSimilarityAdmin(admin.ModelAdmin):
    """ContentSimilarity admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_a_title',
        'content_b_title',
        'similarity_score',
        'similarity_type',
        'computed_at',
    ]
    
    list_filter = [
        'similarity_type',
        'computed_at',
    ]
    
    search_fields = [
        'content_a__title',
        'content_b__title',
    ]
    
    def content_a_title(self, obj):
        return obj.content_a.title[:50]
    content_a_title.short_description = 'İçerik A'
    
    def content_b_title(self, obj):
        return obj.content_b.title[:50]
    content_b_title.short_description = 'İçerik B'


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    """Recommendation admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'type_badge',
        'score',
        'rank',
        'status_badge',
        'shown_at',
    ]
    
    list_filter = [
        'recommendation_type',
        'status',
        'tenant',
        'shown_at',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'shown_at',
        'clicked_at',
        'completed_at',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title[:50]
    content_title.short_description = 'İçerik'
    
    def type_badge(self, obj):
        colors = {
            'personalized': 'purple',
            'similar': 'blue',
            'trending': 'orange',
            'next': 'green',
            'continue': 'teal',
            'new': 'pink',
        }
        color = colors.get(obj.recommendation_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_recommendation_type_display()
        )
    type_badge.short_description = 'Tür'
    
    def status_badge(self, obj):
        colors = {
            'shown': 'gray',
            'clicked': 'blue',
            'started': 'orange',
            'completed': 'green',
            'dismissed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    """RecommendationFeedback admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'feedback_type',
        'created_at',
    ]
    
    list_filter = [
        'feedback_type',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
        'comment',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'


@admin.register(TrendingContent)
class TrendingContentAdmin(admin.ModelAdmin):
    """TrendingContent admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_title',
        'period',
        'rank',
        'score',
        'view_count',
        'completion_count',
        'computed_at',
    ]
    
    list_filter = [
        'period',
        'tenant',
        'computed_at',
    ]
    
    search_fields = [
        'content__title',
    ]
    
    ordering = ['period', 'rank']
    
    def content_title(self, obj):
        return obj.content.title[:50]
    content_title.short_description = 'İçerik'

