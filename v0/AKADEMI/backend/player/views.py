"""
Player Views
=============

Playback session API endpoint'leri.
"""

import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from backend.courses.models import Course, CourseContent, Enrollment
from backend.libs.tenant_aware.mixins import TenantFilterMixin
from backend.libs.idempotency.decorators import idempotent

from .models import PlaybackSession
from .serializers import (
    PlaybackSessionCreateSerializer,
    PlaybackSessionResponseSerializer,
    PlaybackSessionSerializer,
    HeartbeatSerializer,
    EndSessionSerializer,
)
from .services import SessionService

logger = logging.getLogger(__name__)


class PlaybackSessionViewSet(TenantFilterMixin, viewsets.GenericViewSet):
    """
    Playback Session API.
    
    Endpoints:
        POST   /sessions/                    → Session başlat
        GET    /sessions/{id}/               → Session detayı
        PUT    /sessions/{id}/heartbeat/     → Heartbeat gönder
        PUT    /sessions/{id}/end/           → Session sonlandır
    """
    
    queryset = PlaybackSession.objects.all()
    serializer_class = PlaybackSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_course_and_content(self):
        """URL'den course ve content objelerini al."""
        course_id = self.kwargs.get('course_id')
        content_id = self.kwargs.get('content_id')
        
        course = get_object_or_404(
            Course.objects.filter(tenant=self.request.user.tenant),
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
    
    @idempotent(timeout=60)
    def create(self, request, *args, **kwargs):
        """
        Yeni playback session başlat.
        
        POST /api/v1/courses/{courseId}/content/{contentId}/sessions/
        
        Request:
            {
                "device_id": "chrome-win-01",
                "user_agent": "Mozilla/5.0 ..."
            }
        
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
        serializer = PlaybackSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        course, content = self.get_course_and_content()
        
        # Enrollment kontrolü
        if not self.check_enrollment(request.user, course):
            return Response(
                {'detail': 'Bu kursa kayıtlı değilsiniz.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Session oluştur
        session, resume = SessionService.create_session(
            user=request.user,
            course=course,
            content=content,
            device_id=serializer.validated_data.get('device_id'),
            user_agent=serializer.validated_data.get('user_agent') or request.META.get('HTTP_USER_AGENT'),
            ip_address=SessionService.get_client_ip(request),
        )
        
        # Response oluştur
        response_data = {
            'id': session.id,
            'server_time': timezone.now(),
            'resume': resume,
        }
        
        response_serializer = PlaybackSessionResponseSerializer(response_data)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Session detayını getir.
        
        GET /api/v1/courses/{courseId}/content/{contentId}/sessions/{id}/
        """
        session = self.get_object()
        
        # Sadece kendi session'ına erişebilir
        if session.user != request.user:
            return Response(
                {'detail': 'Bu oturuma erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['put'])
    def heartbeat(self, request, *args, **kwargs):
        """
        Heartbeat gönder.
        
        PUT /api/v1/courses/{courseId}/content/{contentId}/sessions/{id}/heartbeat/
        
        Request:
            {
                "position_seconds": 455,
                "playback_rate": 1.25
            }
        
        Response 200:
            {
                "status": "ok",
                "server_time": "2025-12-26T10:05:10Z"
            }
        """
        session = self.get_object()
        
        # Sadece kendi session'ına heartbeat gönderebilir
        if session.user != request.user:
            return Response(
                {'detail': 'Bu oturuma erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Aktif olmayan session'a heartbeat gönderilemez
        if not session.is_active:
            return Response(
                {'detail': 'Bu oturum sonlandırılmış.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        SessionService.process_heartbeat(
            session=session,
            position_seconds=serializer.validated_data.get('position_seconds'),
            playback_rate=serializer.validated_data.get('playback_rate', 1.0),
        )
        
        return Response({
            'status': 'ok',
            'server_time': timezone.now(),
        })
    
    @action(detail=True, methods=['put'])
    def end(self, request, *args, **kwargs):
        """
        Session'ı sonlandır.
        
        PUT /api/v1/courses/{courseId}/content/{contentId}/sessions/{id}/end/
        
        Request:
            {
                "reason": "ended",
                "final_position_seconds": 1800
            }
        
        Response 200:
            {
                "status": "ended",
                "session_id": "uuid",
                "duration_seconds": 1200
            }
        """
        session = self.get_object()
        
        # Sadece kendi session'ını sonlandırabilir
        if session.user != request.user:
            return Response(
                {'detail': 'Bu oturuma erişim yetkiniz yok.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Zaten sonlandırılmış
        if not session.is_active:
            return Response({
                'status': 'already_ended',
                'session_id': session.id,
                'ended_at': session.ended_at,
            })
        
        serializer = EndSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        SessionService.end_session(
            session=session,
            reason=serializer.validated_data.get('reason'),
            final_position=serializer.validated_data.get('final_position_seconds'),
        )
        
        return Response({
            'status': 'ended',
            'session_id': session.id,
            'duration_seconds': session.duration_seconds,
        })

