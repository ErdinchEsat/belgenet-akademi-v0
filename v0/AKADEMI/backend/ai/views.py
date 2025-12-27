"""
AI Views
========

AI API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession

from .models import Transcript, AIConversation, VideoSummary
from .serializers import (
    TranscriptResponseSerializer,
    TranscriptListSerializer,
    TranscriptSearchResponseSerializer,
    AskQuestionSerializer,
    AskQuestionResponseSerializer,
    AIMessageSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    SummaryRequestSerializer,
    SummaryResponseSerializer,
    QuotaSerializer,
)
from .services import TranscriptService, AIChatService, SummaryService

logger = logging.getLogger(__name__)


# ============ Transcript Views ============

class TranscriptView(APIView):
    """
    Transcript API.
    
    Endpoints:
        GET /transcript/           → Transkripti getir
        GET /transcript/languages/ → Mevcut dilleri getir
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_course_and_content(self, request, course_id, content_id):
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
        """Transkripti getir."""
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        language = request.query_params.get('language', 'tr')
        
        transcript = TranscriptService.get_transcript(content, language)
        
        if not transcript:
            # Mevcut dilleri döndür
            available = TranscriptService.get_available_languages(content)
            return Response({
                'detail': f"'{language}' dilinde transkript bulunamadı",
                'available_languages': available,
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TranscriptResponseSerializer(transcript)
        return Response(serializer.data)


class TranscriptLanguagesView(APIView):
    """Mevcut transkript dillerini getir."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id):
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        languages = TranscriptService.get_available_languages(content)
        
        return Response({'languages': languages})


class TranscriptSearchView(APIView):
    """
    Transcript Search API.
    
    Endpoint:
        GET /transcript/search/?q=keyword
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id):
        """Transkriptte arama yap."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'detail': 'q parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        language = request.query_params.get('language', 'tr')
        transcript = TranscriptService.get_transcript(content, language)
        
        if not transcript:
            return Response(
                {'detail': 'Transkript bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        results = TranscriptService.search_transcript(transcript, query)
        
        return Response({
            'query': query,
            'total': len(results),
            'results': results,
        })


# ============ AI Chat Views ============

class AIAskView(APIView):
    """
    AI Ask API.
    
    Endpoint:
        POST /ai/ask/  → AI'a soru sor
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id, content_id):
        """AI'a soru sor."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session al
        session = None
        if data.get('session_id'):
            try:
                session = PlaybackSession.objects.get(
                    id=data['session_id'],
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        try:
            result = AIChatService.ask_question(
                user=request.user,
                course=course,
                content=content,
                question=data['question'],
                conversation_id=data.get('conversation_id'),
                video_ts=data.get('video_ts'),
                session=session,
                include_transcript=data.get('include_transcript', True),
                include_notes=data.get('include_notes', False),
            )
            
            return Response({
                'conversation_id': str(result['conversation_id']),
                'message': AIMessageSerializer(result['message']).data,
                'sources': result.get('sources', []),
                'quota': result.get('quota'),
            })
        
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )


class AIConversationsView(APIView):
    """
    AI Conversations API.
    
    Endpoints:
        GET /ai/conversations/  → Konuşmaları listele
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id=None, content_id=None):
        """Konuşmaları listele."""
        course = None
        content = None
        
        if course_id:
            course = get_object_or_404(
                Course.objects.filter(tenant=request.user.tenant),
                id=course_id
            )
        
        if content_id and course:
            content = get_object_or_404(
                CourseContent.objects.filter(module__course=course),
                id=content_id
            )
        
        conversations = AIChatService.get_user_conversations(
            user=request.user,
            course=course,
            content=content,
        )
        
        serializer = ConversationSerializer(conversations, many=True)
        
        return Response({
            'total': len(conversations),
            'conversations': serializer.data,
        })


class AIConversationDetailView(APIView):
    """
    AI Conversation Detail API.
    
    Endpoints:
        GET    /ai/conversations/{id}/  → Konuşma detayı
        DELETE /ai/conversations/{id}/  → Konuşmayı sil
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, conversation_id):
        """Konuşma detayını getir."""
        conversation = AIChatService.get_conversation_detail(
            user=request.user,
            conversation_id=conversation_id,
        )
        
        if not conversation:
            return Response(
                {'detail': 'Konuşma bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)
    
    def delete(self, request, conversation_id):
        """Konuşmayı sil."""
        deleted = AIChatService.delete_conversation(
            user=request.user,
            conversation_id=conversation_id,
        )
        
        if not deleted:
            return Response(
                {'detail': 'Konuşma bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIQuotaView(APIView):
    """
    AI Quota API.
    
    Endpoint:
        GET /ai/quota/  → Kota bilgisi
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Kota bilgisini getir."""
        quota = AIChatService.get_or_create_quota(request.user)
        serializer = QuotaSerializer(quota)
        return Response(serializer.data)


# ============ Summary Views ============

class SummaryView(APIView):
    """
    Summary API.
    
    Endpoints:
        GET  /summary/  → Özeti getir
        POST /summary/  → Özet oluştur
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id):
        """Özeti getir."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        summary_type = request.query_params.get(
            'type', VideoSummary.SummaryType.BRIEF
        )
        language = request.query_params.get('language', 'tr')
        
        summary = SummaryService.get_summary(content, summary_type, language)
        
        if not summary:
            return Response(
                {'detail': 'Özet bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SummaryResponseSerializer(summary)
        return Response(serializer.data)
    
    def post(self, request, course_id, content_id):
        """Özet oluştur."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        serializer = SummaryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            summary = SummaryService.create_summary(
                content=content,
                summary_type=data.get('summary_type', VideoSummary.SummaryType.BRIEF),
                language=data.get('language', 'tr'),
                start_ts=data.get('start_ts'),
                end_ts=data.get('end_ts'),
            )
            
            response_serializer = SummaryResponseSerializer(summary)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SummaryListView(APIView):
    """
    Summary List API.
    
    Endpoint:
        GET /summaries/  → Tüm özetleri getir
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id):
        """Tüm özetleri getir."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        summaries = SummaryService.get_all_summaries(content)
        serializer = SummaryResponseSerializer(summaries, many=True)
        
        return Response({
            'content_id': content.id,
            'total': len(summaries),
            'summaries': serializer.data,
        })

