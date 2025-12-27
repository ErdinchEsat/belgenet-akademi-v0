"""
Timeline Views
==============

Timeline API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession

from .models import TimelineNode
from .serializers import (
    TimelineNodeSerializer,
    TimelineResponseSerializer,
    InteractionCreateSerializer,
    InteractionResponseSerializer,
)
from .services import TimelineService

logger = logging.getLogger(__name__)


class TimelineView(APIView):
    """
    Timeline API.
    
    Endpoint:
        GET /timeline/  → Timeline node'larını getir
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
    
    def get(self, request, course_id, content_id):
        """
        Timeline node'larını getir.
        
        GET /api/v1/courses/{courseId}/content/{contentId}/timeline/
        
        Query params:
            include_inactive: Pasif node'ları dahil et (admin için)
        
        Response 200:
        {
            "content_id": 123,
            "total_nodes": 5,
            "nodes": [
                {
                    "id": "uuid",
                    "node_type": "checkpoint",
                    "start_ts": 300,
                    "config": {...}
                }
            ],
            "chapters": [
                {"id": "uuid", "start_ts": 0, "title": "Giriş"},
                {"id": "uuid", "start_ts": 300, "title": "Örnekler"}
            ]
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Admin için pasif node'ları da göster
        include_inactive = (
            request.query_params.get('include_inactive', '').lower() == 'true'
            and request.user.is_staff
        )
        
        # Node'ları getir
        nodes = TimelineService.get_timeline_nodes(
            content=content,
            include_inactive=include_inactive,
        )
        
        # Chapter'ları getir
        chapters = TimelineService.get_chapters(content)
        
        # Kullanıcı etkileşimlerini ekle
        user_interactions = TimelineService.get_user_interactions(
            user=request.user,
            content=content,
        )
        
        # Node serialization
        nodes_data = TimelineNodeSerializer(nodes, many=True).data
        
        # Her node'a kullanıcı etkileşimini ekle
        for node_data in nodes_data:
            node_id = str(node_data['id'])
            if node_id in user_interactions:
                node_data['user_interaction'] = user_interactions[node_id]
        
        response_data = {
            'content_id': content.id,
            'total_nodes': len(nodes),
            'nodes': nodes_data,
            'chapters': chapters,
        }
        
        return Response(response_data)


class TimelineInteractionView(APIView):
    """
    Timeline Node Interaction API.
    
    Endpoint:
        POST /timeline/{nodeId}/interact/  → Etkileşim kaydet
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_node(self, request, course_id, content_id, node_id):
        """URL'den node objesini al."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        node = get_object_or_404(
            TimelineNode.objects.filter(content=content),
            id=node_id
        )
        
        return node
    
    def post(self, request, course_id, content_id, node_id):
        """
        Node etkileşimini kaydet.
        
        POST /api/v1/courses/{courseId}/content/{contentId}/timeline/{nodeId}/interact/
        
        Request:
        {
            "interaction_type": "completed",
            "session_id": "uuid",
            "video_ts": 305,
            "data": {"answer": "Evet"}
        }
        
        Response 201:
        {
            "id": "uuid",
            "node": "uuid",
            "interaction_type": "completed",
            "data": {...},
            "created_at": "..."
        }
        """
        node = self.get_node(request, course_id, content_id, node_id)
        
        serializer = InteractionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session al (opsiyonel)
        session = None
        if data.get('session_id'):
            try:
                session = PlaybackSession.objects.get(
                    id=data['session_id'],
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        # Etkileşimi kaydet
        interaction = TimelineService.record_interaction(
            user=request.user,
            node=node,
            interaction_type=data['interaction_type'],
            session=session,
            video_ts=data.get('video_ts'),
            data=data.get('data', {}),
        )
        
        response_serializer = InteractionResponseSerializer(interaction)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CheckpointConfirmView(APIView):
    """
    Checkpoint Confirm API.
    
    Endpoint:
        POST /timeline/{nodeId}/confirm/  → Checkpoint'i onayla
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id, content_id, node_id):
        """
        Checkpoint'i onayla.
        
        POST /api/v1/courses/{courseId}/content/{contentId}/timeline/{nodeId}/confirm/
        """
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        node = get_object_or_404(
            TimelineNode.objects.filter(
                content=content,
                node_type=TimelineNode.NodeType.CHECKPOINT,
            ),
            id=node_id
        )
        
        # Session al (opsiyonel)
        session = None
        session_id = request.data.get('session_id')
        if session_id:
            try:
                session = PlaybackSession.objects.get(
                    id=session_id,
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        interaction = TimelineService.confirm_checkpoint(
            user=request.user,
            node=node,
            session=session,
            video_ts=request.data.get('video_ts'),
        )
        
        return Response({
            'status': 'confirmed',
            'node_id': str(node.id),
            'interaction_id': str(interaction.id),
        })


class PollAnswerView(APIView):
    """
    Poll Answer API.
    
    Endpoint:
        POST /timeline/{nodeId}/answer/  → Poll'u cevapla
        GET  /timeline/{nodeId}/results/  → Poll sonuçları
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id, content_id, node_id):
        """Poll'u cevapla."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        node = get_object_or_404(
            TimelineNode.objects.filter(
                content=content,
                node_type=TimelineNode.NodeType.POLL,
            ),
            id=node_id
        )
        
        answer = request.data.get('answer')
        if not answer:
            return Response(
                {'detail': 'answer field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Session al (opsiyonel)
        session = None
        session_id = request.data.get('session_id')
        if session_id:
            try:
                session = PlaybackSession.objects.get(
                    id=session_id,
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        interaction = TimelineService.answer_poll(
            user=request.user,
            node=node,
            answer=answer,
            session=session,
            video_ts=request.data.get('video_ts'),
        )
        
        # Sonuçları da döndür
        results = TimelineService.get_poll_results(node)
        
        return Response({
            'status': 'answered',
            'node_id': str(node.id),
            'interaction_id': str(interaction.id),
            'results': results,
        })
    
    def get(self, request, course_id, content_id, node_id):
        """Poll sonuçlarını getir."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        node = get_object_or_404(
            TimelineNode.objects.filter(
                content=content,
                node_type=TimelineNode.NodeType.POLL,
            ),
            id=node_id
        )
        
        results = TimelineService.get_poll_results(node)
        
        return Response(results)

