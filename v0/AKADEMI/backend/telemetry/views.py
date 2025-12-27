"""
Telemetry Views
===============

Event tracking API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession

from .serializers import (
    EventBatchSerializer,
    EventBatchResponseSerializer,
)
from .services import IngestService

logger = logging.getLogger(__name__)


class EventBatchView(APIView):
    """
    Event Batch API.
    
    Endpoint:
        POST /events/  → Batch event ingestion
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
    
    def post(self, request, course_id, content_id):
        """
        Event batch gönder.
        
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
        
        Response 202:
        {
            "accepted": 5,
            "deduped": 1,
            "rejected": 0,
            "errors": []
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Request doğrulama
        serializer = EventBatchSerializer(data=request.data)
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
        
        # Session aktif olmasa bile event kabul et (buffer'da kalmış olabilir)
        # Ama uyarı logla
        if not session.is_active:
            logger.warning(f"Events received for inactive session: {session.id}")
        
        # Event batch'i işle
        accepted, deduped, rejected, errors = IngestService.ingest_batch(
            session=session,
            events=data['events'],
        )
        
        # Response
        response_data = {
            'accepted': accepted,
            'deduped': deduped,
            'rejected': rejected,
            'errors': errors if errors else [],
        }
        
        return Response(response_data, status=status.HTTP_202_ACCEPTED)

