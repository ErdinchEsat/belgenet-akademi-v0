"""
Recommendations URL Configuration
=================================

Recommendations API endpoint'leri.

URL Pattern:
    /api/v1/recommendations/
"""

from django.urls import path

from .views import (
    PersonalizedRecommendationsView,
    NextContentView,
    SimilarContentView,
    TrendingContentView,
    ContinueWatchingView,
    RecommendationFeedbackView,
    RecommendationClickView,
    UserInterestView,
)

app_name = 'recommendations'

urlpatterns = [
    path('', PersonalizedRecommendationsView.as_view(), name='list'),
    path('next/', NextContentView.as_view(), name='next'),
    path('similar/', SimilarContentView.as_view(), name='similar'),
    path('trending/', TrendingContentView.as_view(), name='trending'),
    path('continue/', ContinueWatchingView.as_view(), name='continue'),
    path('feedback/', RecommendationFeedbackView.as_view(), name='feedback'),
    path('click/', RecommendationClickView.as_view(), name='click'),
    path('profile/', UserInterestView.as_view(), name='profile'),
]

