"""
Recommendations Views
=====================

Recommendations API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent

from .models import Recommendation, TrendingContent
from .serializers import (
    RecommendationsResponseSerializer,
    RecommendedContentSerializer,
    NextContentSerializer,
    SimilarContentSerializer,
    TrendingContentSerializer,
    FeedbackRequestSerializer,
    FeedbackResponseSerializer,
    UserInterestSerializer,
    RecommendationClickSerializer,
)
from .services import RecommendationService

logger = logging.getLogger(__name__)


class PersonalizedRecommendationsView(APIView):
    """
    Kişiselleştirilmiş Öneriler API.
    
    Endpoint:
        GET /recommendations/  → Kişisel öneriler
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Kişiselleştirilmiş öneriler getir."""
        limit = int(request.query_params.get('limit', 10))
        exclude_completed = request.query_params.get('exclude_completed', 'true').lower() == 'true'
        
        recommendations = RecommendationService.get_personalized_recommendations(
            user=request.user,
            limit=limit,
            exclude_completed=exclude_completed,
        )
        
        return Response({
            'total': len(recommendations),
            'recommendations': recommendations,
        })


class NextContentView(APIView):
    """
    Sonraki İçerik Önerisi API.
    
    Endpoint:
        GET /recommendations/next/?content_id=123
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Sonraki içerik önerisini getir."""
        content_id = request.query_params.get('content_id')
        
        if not content_id:
            return Response(
                {'detail': 'content_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = get_object_or_404(
            CourseContent.objects.select_related('module__course'),
            id=content_id,
            module__course__tenant=request.user.tenant,
        )
        
        next_content = RecommendationService.get_next_content(
            user=request.user,
            current_content=content,
        )
        
        if not next_content:
            return Response(
                {'detail': 'Önerilecek içerik bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(next_content)


class SimilarContentView(APIView):
    """
    Benzer İçerikler API.
    
    Endpoint:
        GET /recommendations/similar/?content_id=123
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Benzer içerikleri getir."""
        content_id = request.query_params.get('content_id')
        limit = int(request.query_params.get('limit', 5))
        
        if not content_id:
            return Response(
                {'detail': 'content_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = get_object_or_404(
            CourseContent.objects.select_related('module__course'),
            id=content_id,
            module__course__tenant=request.user.tenant,
        )
        
        similar = RecommendationService.get_similar_content(
            user=request.user,
            content=content,
            limit=limit,
        )
        
        return Response({
            'content_id': content.id,
            'total': len(similar),
            'similar': similar,
        })


class TrendingContentView(APIView):
    """
    Trend İçerikler API.
    
    Endpoint:
        GET /recommendations/trending/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Trend içerikleri getir."""
        period = request.query_params.get('period', TrendingContent.TrendPeriod.WEEKLY)
        limit = int(request.query_params.get('limit', 10))
        
        trending = RecommendationService.get_trending_content(
            user=request.user,
            period=period,
            limit=limit,
        )
        
        serializer = TrendingContentSerializer(trending, many=True)
        
        return Response({
            'period': period,
            'total': len(trending),
            'trending': serializer.data,
        })


class ContinueWatchingView(APIView):
    """
    Devam Et Önerileri API.
    
    Endpoint:
        GET /recommendations/continue/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Yarıda kalan içerikleri getir."""
        limit = int(request.query_params.get('limit', 5))
        
        continue_watching = RecommendationService.get_continue_watching(
            user=request.user,
            limit=limit,
        )
        
        return Response({
            'total': len(continue_watching),
            'items': continue_watching,
        })


class RecommendationFeedbackView(APIView):
    """
    Öneri Geri Bildirimi API.
    
    Endpoint:
        POST /recommendations/feedback/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Geri bildirim kaydet."""
        serializer = FeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            feedback = RecommendationService.record_feedback(
                user=request.user,
                recommendation_id=str(data['recommendation_id']),
                feedback_type=data['feedback_type'],
                comment=data.get('comment', ''),
            )
            
            response_serializer = FeedbackResponseSerializer(feedback)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except Recommendation.DoesNotExist:
            return Response(
                {'detail': 'Öneri bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )


class RecommendationClickView(APIView):
    """
    Öneri Tıklama Kaydı API.
    
    Endpoint:
        POST /recommendations/click/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Tıklama kaydı."""
        serializer = RecommendationClickSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            recommendation = RecommendationService.record_click(
                user=request.user,
                recommendation_id=str(serializer.validated_data['recommendation_id']),
            )
            
            return Response({
                'status': 'recorded',
                'recommendation_id': str(recommendation.id),
            })
        
        except Recommendation.DoesNotExist:
            return Response(
                {'detail': 'Öneri bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserInterestView(APIView):
    """
    Kullanıcı İlgi Profili API.
    
    Endpoint:
        GET /recommendations/profile/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """İlgi profilini getir."""
        interest = RecommendationService.get_or_create_interest_profile(request.user)
        serializer = UserInterestSerializer(interest)
        return Response(serializer.data)

