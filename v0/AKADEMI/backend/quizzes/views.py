"""
Quizzes Views
=============

Quiz API endpoint'leri.
"""

import logging
import random
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession
from backend.libs.tenant_aware.mixins import TenantFilterMixin

from .models import Quiz, QuizAttempt
from .serializers import (
    QuizSerializer,
    QuizQuestionSerializer,
    AttemptStartSerializer,
    AttemptResponseSerializer,
    QuizSubmitSerializer,
)
from .services import GradingService

logger = logging.getLogger(__name__)


class QuizViewSet(TenantFilterMixin, viewsets.GenericViewSet):
    """
    Quiz API.
    
    Endpoints:
        GET    /quizzes/{id}/                    → Quiz detayı
        POST   /quizzes/{id}/attempts/           → Quiz başlat
        GET    /quizzes/{id}/attempts/{aid}/     → Attempt detayı
        POST   /quizzes/{id}/attempts/{aid}/submit → Quiz gönder
    """
    
    queryset = Quiz.objects.filter(is_active=True)
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def retrieve(self, request, *args, **kwargs):
        """
        Quiz detayını getir.
        
        GET /api/v1/quizzes/{id}/
        
        Response 200:
        {
            "id": "uuid",
            "title": "Quiz Başlığı",
            "questions": [...],
            ...
        }
        """
        quiz = self.get_object()
        
        # Soruları hazırla
        questions = list(quiz.questions.all())
        
        # Karıştırma ayarları
        if quiz.shuffle_questions:
            random.shuffle(questions)
        
        serializer = self.get_serializer(quiz)
        data = serializer.data
        
        # Soruları ayarla
        question_data = []
        for q in questions:
            q_data = QuizQuestionSerializer(q).data
            
            if quiz.shuffle_options and q.options:
                q_data['options'] = random.sample(q.options, len(q.options))
            
            question_data.append(q_data)
        
        data['questions'] = question_data
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def attempts(self, request, *args, **kwargs):
        """
        Quiz denemesi başlat.
        
        POST /api/v1/quizzes/{id}/attempts/
        
        Request:
        {
            "course_id": 123,
            "content_id": 456,
            "session_id": "uuid"
        }
        
        Response 201:
        {
            "id": "uuid",
            "quiz": "uuid",
            "status": "started",
            "questions": [...]
        }
        """
        quiz = self.get_object()
        
        serializer = AttemptStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # İlişkileri al
        course = None
        content = None
        session = None
        
        if data.get('course_id'):
            course = get_object_or_404(Course, id=data['course_id'])
        
        if data.get('content_id'):
            content = get_object_or_404(CourseContent, id=data['content_id'])
        
        if data.get('session_id'):
            try:
                session = PlaybackSession.objects.get(
                    id=data['session_id'],
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        try:
            attempt = GradingService.start_attempt(
                user=request.user,
                quiz=quiz,
                course=course,
                content=content,
                session=session,
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Response
        response_data = AttemptResponseSerializer(attempt).data
        
        # Soruları ekle
        questions = list(quiz.questions.all())
        if quiz.shuffle_questions:
            random.shuffle(questions)
        
        question_data = []
        for q in questions:
            q_data = QuizQuestionSerializer(q).data
            if quiz.shuffle_options and q.options:
                q_data['options'] = random.sample(q.options, len(q.options))
            question_data.append(q_data)
        
        response_data['questions'] = question_data
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='attempts/(?P<attempt_id>[^/.]+)/submit')
    def submit(self, request, id=None, attempt_id=None):
        """
        Quiz cevaplarını gönder.
        
        POST /api/v1/quizzes/{id}/attempts/{attemptId}/submit
        
        Request:
        {
            "answers": [
                {"question_id": "uuid", "answer": "A"}
            ]
        }
        
        Response 200:
        {
            "attempt_id": "uuid",
            "score": 80,
            "max_score": 100,
            "passed": true,
            "answers": [...]
        }
        """
        quiz = self.get_object()
        
        # Attempt kontrolü
        attempt = get_object_or_404(
            QuizAttempt.objects.filter(
                quiz=quiz,
                user=request.user,
            ),
            id=attempt_id
        )
        
        # Request doğrulama
        serializer = QuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            attempt = GradingService.submit_answers(
                attempt=attempt,
                answers=data['answers'],
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sonuçları getir
        result = GradingService.get_attempt_result(attempt)
        
        return Response(result)
    
    @action(detail=True, methods=['get'], url_path='attempts/(?P<attempt_id>[^/.]+)')
    def attempt_detail(self, request, id=None, attempt_id=None):
        """
        Attempt detayını getir.
        
        GET /api/v1/quizzes/{id}/attempts/{attemptId}/
        """
        quiz = self.get_object()
        
        attempt = get_object_or_404(
            QuizAttempt.objects.filter(
                quiz=quiz,
                user=request.user,
            ),
            id=attempt_id
        )
        
        # Eğer gönderilmişse sonuçları da göster
        if attempt.status in [QuizAttempt.Status.SUBMITTED, QuizAttempt.Status.GRADED]:
            result = GradingService.get_attempt_result(attempt)
            return Response(result)
        
        # Değilse sadece attempt bilgisi
        serializer = AttemptResponseSerializer(attempt)
        return Response(serializer.data)

