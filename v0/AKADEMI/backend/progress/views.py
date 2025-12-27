"""
Progress Views
==============

Video ilerleme API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent, Enrollment
from backend.player.models import PlaybackSession
from backend.libs.idempotency.decorators import idempotent

from .models import VideoProgress
from .serializers import (
    ProgressResponseSerializer,
    ProgressUpdateSerializer,
    ProgressUpdateResponseSerializer,
)
from .services import ProgressService

logger = logging.getLogger(__name__)


class ProgressView(APIView):
    """
    Video Progress API.
    
    Endpoints:
        GET  /progress/  → İlerleme durumu getir
        PUT  /progress/  → İlerleme güncelle
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_course_and_content(self, request, course_id, content_id):
        """URL'den course ve content objelerini al."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        return course, content
    
    def check_enrollment(self, user, course):
        """Kullanıcının kursa kayıtlı olduğunu kontrol et."""
        return Enrollment.objects.filter(
            user=user,
            course=course,
            status=Enrollment.Status.ACTIVE,
        ).exists()
    
    def get(self, request, course_id, content_id):
        """
        İlerleme durumunu getir.
        
        GET /api/v1/courses/{courseId}/content/{contentId}/progress/
        
        Response 200:
        {
            "watched_seconds": 1210,
            "last_position_seconds": 455,
            "completion_ratio": 0.62,
            "is_completed": false,
            "preferred_speed": 1.25,
            "preferred_caption_lang": "tr"
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Enrollment kontrolü
        if not self.check_enrollment(request.user, course):
            return Response(
                {'detail': 'Bu kursa kayıtlı değilsiniz.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Progress'i getir
        progress = ProgressService.get_progress(request.user, content)
        
        if not progress:
            # Progress yoksa varsayılan değerler döndür
            return Response({
                'watched_seconds': 0,
                'last_position_seconds': 0,
                'completion_ratio': 0.0,
                'is_completed': False,
                'preferred_speed': 1.0,
                'preferred_caption_lang': None,
                'updated_at': None,
            })
        
        serializer = ProgressResponseSerializer(progress)
        return Response(serializer.data)
    
    @idempotent(timeout=30)
    def put(self, request, course_id, content_id):
        """
        İlerlemeyi güncelle.
        
        PUT /api/v1/courses/{courseId}/content/{contentId}/progress/
        
        Request:
        {
            "session_id": "uuid",
            "last_position_seconds": 455,
            "client_watched_delta_seconds": 10,
            "playback_rate": 1.25,
            "caption_lang": "tr"
        }
        
        Response 200:
        {
            "content_id": 123,
            "watched_seconds": 1210,
            "last_position_seconds": 455,
            "completion_ratio": 0.62,
            "is_completed": false,
            "updated_at": "2025-12-26T10:05:11Z"
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Enrollment kontrolü
        if not self.check_enrollment(request.user, course):
            return Response(
                {'detail': 'Bu kursa kayıtlı değilsiniz.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Request doğrulama
        serializer = ProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session kontrolü
        try:
            session = PlaybackSession.objects.get(
                id=data['session_id'],
                user=request.user,
                content=content,
            )
        except PlaybackSession.DoesNotExist:
            return Response(
                {'detail': 'Geçersiz veya bulunamayan session.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not session.is_active:
            return Response(
                {'detail': 'Session aktif değil.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Progress güncelle
            progress = ProgressService.update_progress(
                user=request.user,
                course=course,
                content=content,
                session=session,
                last_position_seconds=data['last_position_seconds'],
                client_watched_delta_seconds=data.get('client_watched_delta_seconds', 0),
                playback_rate=data.get('playback_rate', 1.0),
                caption_lang=data.get('caption_lang'),
            )
            
            # Enrollment ile senkronize et
            ProgressService.sync_to_enrollment(progress)
            
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Response
        response_data = {
            'content_id': content.id,
            'watched_seconds': progress.watched_seconds,
            'last_position_seconds': progress.last_position_seconds,
            'completion_ratio': float(progress.completion_ratio),
            'is_completed': progress.is_completed,
            'updated_at': progress.updated_at,
        }
        
        return Response(response_data)

