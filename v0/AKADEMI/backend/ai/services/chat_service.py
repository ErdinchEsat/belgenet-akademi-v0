"""
AI Chat Service
===============

AI tutor chat servisi.
"""

import logging
from typing import Dict, Optional, List
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession
from backend.notes.models import VideoNote
from ..models import (
    Transcript, AIConversation, AIMessage, AIQuota
)
from .transcript_service import TranscriptService

logger = logging.getLogger(__name__)


class AIChatService:
    """
    AI tutor chat servisi.
    
    Sorumluluklar:
    - Soru-cevap işleme
    - Context hazırlama (RAG)
    - Konuşma yönetimi
    - Kota kontrolü
    """
    
    @classmethod
    def get_or_create_quota(cls, user) -> AIQuota:
        """Kullanıcı kotasını getir veya oluştur."""
        quota, created = AIQuota.objects.get_or_create(
            user=user,
            tenant=user.tenant,
        )
        
        # Günlük reset kontrolü
        if quota.daily_reset_at and quota.daily_reset_at.date() < timezone.now().date():
            quota.daily_questions_used = 0
            quota.daily_reset_at = timezone.now()
            quota.save()
        
        return quota
    
    @classmethod
    def check_quota(cls, user) -> Dict:
        """
        Kota kontrolü yap.
        
        Returns:
            {'can_ask': bool, 'remaining': int, 'message': str}
        """
        quota = cls.get_or_create_quota(user)
        
        if not quota.can_ask_question:
            return {
                'can_ask': False,
                'remaining': 0,
                'message': 'Günlük soru limitinize ulaştınız.',
            }
        
        return {
            'can_ask': True,
            'remaining': quota.remaining_questions,
            'message': None,
        }
    
    @classmethod
    @transaction.atomic
    def ask_question(
        cls,
        user,
        course: Course,
        content: CourseContent,
        question: str,
        conversation_id: str = None,
        video_ts: int = None,
        session: PlaybackSession = None,
        include_transcript: bool = True,
        include_notes: bool = False,
    ) -> Dict:
        """
        AI'a soru sor.
        
        Returns:
            {
                'conversation_id': uuid,
                'message': AIMessage,
                'sources': [...],
                'quota': {...}
            }
        """
        # Kota kontrolü
        quota_check = cls.check_quota(user)
        if not quota_check['can_ask']:
            raise ValueError(quota_check['message'])
        
        # Konuşma al veya oluştur
        if conversation_id:
            try:
                conversation = AIConversation.objects.get(
                    id=conversation_id,
                    user=user,
                )
            except AIConversation.DoesNotExist:
                conversation = None
        else:
            conversation = None
        
        if not conversation:
            # Yeni konuşma oluştur
            title = question[:50] + '...' if len(question) > 50 else question
            conversation = AIConversation.objects.create(
                tenant=user.tenant,
                user=user,
                course=course,
                content=content,
                session=session,
                title=title,
                context={
                    'video_ts': video_ts,
                },
            )
        
        # Kullanıcı mesajını kaydet
        user_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.MessageRole.USER,
            content=question,
            video_ts=video_ts,
        )
        
        # Context hazırla (RAG)
        context = cls._prepare_context(
            user=user,
            content=content,
            video_ts=video_ts,
            include_transcript=include_transcript,
            include_notes=include_notes,
        )
        
        # AI yanıtı oluştur
        # TODO: Gerçek AI entegrasyonu (OpenAI, Anthropic, vb.)
        ai_response = cls._generate_response(
            question=question,
            context=context,
            conversation=conversation,
        )
        
        # AI mesajını kaydet
        ai_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.MessageRole.ASSISTANT,
            content=ai_response['answer'],
            video_ts=video_ts,
            sources=ai_response.get('sources', []),
            tokens_used=ai_response.get('tokens_used', 0),
            model_used=ai_response.get('model', 'mock'),
        )
        
        # Konuşma sayacını güncelle
        AIConversation.objects.filter(id=conversation.id).update(
            message_count=F('message_count') + 2
        )
        
        # Kota güncelle
        quota = cls.get_or_create_quota(user)
        quota.daily_questions_used += 1
        quota.monthly_tokens_used += ai_response.get('tokens_used', 0)
        quota.save()
        
        logger.info(f"AI question answered: user={user.id}, conversation={conversation.id}")
        
        return {
            'conversation_id': conversation.id,
            'message': ai_message,
            'sources': ai_response.get('sources', []),
            'quota': {
                'remaining': quota.remaining_questions,
                'daily_limit': quota.daily_questions_limit,
            },
        }
    
    @classmethod
    def _prepare_context(
        cls,
        user,
        content: CourseContent,
        video_ts: int = None,
        include_transcript: bool = True,
        include_notes: bool = False,
    ) -> Dict:
        """
        AI için context hazırla.
        """
        context = {
            'content_title': content.title,
            'content_description': content.description or '',
            'course_title': content.module.course.title,
        }
        
        # Transkript ekle
        if include_transcript:
            transcript = TranscriptService.get_transcript(content)
            if transcript and video_ts is not None:
                context['transcript'] = TranscriptService.get_text_around_time(
                    transcript, video_ts, context_seconds=120
                )
        
        # Kullanıcı notlarını ekle
        if include_notes:
            notes = VideoNote.objects.filter(
                user=user,
                content=content,
            ).order_by('video_ts')[:10]
            
            context['user_notes'] = [
                {
                    'video_ts': n.video_ts,
                    'text': n.content_text,
                }
                for n in notes
            ]
        
        return context
    
    @classmethod
    def _generate_response(
        cls,
        question: str,
        context: Dict,
        conversation: AIConversation,
    ) -> Dict:
        """
        AI yanıtı oluştur.
        
        TODO: Gerçek AI entegrasyonu
        """
        # Mock response
        # Gerçek uygulamada burada OpenAI/Anthropic API çağrısı yapılır
        
        transcript_context = context.get('transcript', '')
        
        # Basit mock yanıt
        if transcript_context:
            answer = (
                f"'{context['content_title']}' içeriğiyle ilgili sorunuzu aldım. "
                f"Video transkriptine göre bu konuda şunları söyleyebilirim:\n\n"
                f"Videonun ilgili bölümünde {transcript_context[:200]}... "
                f"konularından bahsedilmektedir.\n\n"
                f"Daha detaylı bilgi için videonun ilgili bölümüne göz atabilirsiniz."
            )
        else:
            answer = (
                f"'{context['content_title']}' hakkındaki sorunuz için "
                f"teşekkür ederim. Bu konuyla ilgili size yardımcı olmaya hazırım. "
                f"Sorunuzu daha iyi yanıtlayabilmem için videonun belirli bir "
                f"bölümünü işaret ederek soru sorabilirsiniz."
            )
        
        return {
            'answer': answer,
            'sources': [
                {
                    'type': 'content',
                    'content_id': str(conversation.content.id) if conversation.content else None,
                    'title': context.get('content_title'),
                },
            ],
            'tokens_used': len(answer.split()) * 2,  # Mock token hesabı
            'model': 'mock-model-v1',
        }
    
    @classmethod
    def get_user_conversations(
        cls,
        user,
        course: Course = None,
        content: CourseContent = None,
        limit: int = 20,
    ) -> List[AIConversation]:
        """
        Kullanıcının konuşmalarını getir.
        """
        queryset = AIConversation.objects.filter(user=user)
        
        if course:
            queryset = queryset.filter(course=course)
        if content:
            queryset = queryset.filter(content=content)
        
        return list(
            queryset.order_by('-last_activity_at')[:limit]
        )
    
    @classmethod
    def get_conversation_detail(
        cls,
        user,
        conversation_id: str,
    ) -> Optional[AIConversation]:
        """
        Konuşma detayını getir.
        """
        try:
            return AIConversation.objects.prefetch_related(
                'messages'
            ).get(
                id=conversation_id,
                user=user,
            )
        except AIConversation.DoesNotExist:
            return None
    
    @classmethod
    @transaction.atomic
    def delete_conversation(
        cls,
        user,
        conversation_id: str,
    ) -> bool:
        """
        Konuşmayı sil.
        """
        deleted, _ = AIConversation.objects.filter(
            id=conversation_id,
            user=user,
        ).delete()
        
        return deleted > 0

