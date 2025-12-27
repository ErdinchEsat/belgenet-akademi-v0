"""
Summary Service
===============

Video özet servisi.
"""

import logging
from typing import Optional, List
from django.db import transaction

from backend.courses.models import CourseContent
from ..models import Transcript, VideoSummary
from .transcript_service import TranscriptService

logger = logging.getLogger(__name__)


class SummaryService:
    """
    Video özet servisi.
    
    Sorumluluklar:
    - Özet oluşturma
    - Özet getirme
    - Bölüm özeti
    """
    
    @classmethod
    def get_summary(
        cls,
        content: CourseContent,
        summary_type: str = VideoSummary.SummaryType.BRIEF,
        language: str = 'tr',
    ) -> Optional[VideoSummary]:
        """
        Mevcut özeti getir.
        """
        return VideoSummary.objects.filter(
            content=content,
            summary_type=summary_type,
            language=language,
        ).first()
    
    @classmethod
    def get_all_summaries(cls, content: CourseContent) -> List[VideoSummary]:
        """
        İçerik için tüm özetleri getir.
        """
        return list(
            VideoSummary.objects.filter(content=content)
            .order_by('summary_type')
        )
    
    @classmethod
    @transaction.atomic
    def create_summary(
        cls,
        content: CourseContent,
        summary_type: str = VideoSummary.SummaryType.BRIEF,
        language: str = 'tr',
        start_ts: int = None,
        end_ts: int = None,
    ) -> VideoSummary:
        """
        Yeni özet oluştur.
        
        TODO: Gerçek AI entegrasyonu
        """
        # Transkript al
        transcript = TranscriptService.get_transcript(content, language)
        
        if not transcript:
            raise ValueError(f"'{language}' dilinde transkript bulunamadı")
        
        # Özet için text al
        if start_ts is not None and end_ts is not None:
            # Bölüm özeti
            segments = TranscriptService.get_segments_in_range(
                transcript, start_ts, end_ts
            )
            source_text = ' '.join([s.text for s in segments])
        else:
            # Tam özet
            source_text = transcript.full_text
        
        # AI özet oluştur
        # TODO: Gerçek AI entegrasyonu
        summary_result = cls._generate_summary(
            source_text=source_text,
            summary_type=summary_type,
            content_title=content.title,
        )
        
        # Mevcut özeti kontrol et
        existing = cls.get_summary(content, summary_type, language)
        
        if existing:
            existing.summary_text = summary_result['summary']
            existing.model_used = summary_result.get('model', 'mock')
            existing.tokens_used = summary_result.get('tokens_used', 0)
            existing.start_ts = start_ts
            existing.end_ts = end_ts
            existing.save()
            summary = existing
        else:
            summary = VideoSummary.objects.create(
                tenant=content.module.course.tenant,
                content=content,
                summary_type=summary_type,
                language=language,
                summary_text=summary_result['summary'],
                start_ts=start_ts,
                end_ts=end_ts,
                model_used=summary_result.get('model', 'mock'),
                tokens_used=summary_result.get('tokens_used', 0),
            )
        
        logger.info(f"Summary created: content={content.id}, type={summary_type}")
        
        return summary
    
    @classmethod
    def _generate_summary(
        cls,
        source_text: str,
        summary_type: str,
        content_title: str,
    ) -> dict:
        """
        AI özet oluştur.
        
        TODO: Gerçek AI entegrasyonu
        """
        # Mock response
        word_count = len(source_text.split())
        
        if summary_type == VideoSummary.SummaryType.BRIEF:
            summary = (
                f"'{content_title}' videosu yaklaşık {word_count} kelimelik "
                f"bir içerik sunmaktadır. Bu video, konunun temel kavramlarını "
                f"açıklamakta ve pratik örnekler içermektedir."
            )
        
        elif summary_type == VideoSummary.SummaryType.BULLET_POINTS:
            summary = (
                f"• '{content_title}' videosunun ana konuları:\n"
                f"• Temel kavramların tanıtımı\n"
                f"• Pratik uygulama örnekleri\n"
                f"• Sık karşılaşılan hatalar ve çözümleri\n"
                f"• Özet ve tekrar"
            )
        
        elif summary_type == VideoSummary.SummaryType.KEY_TAKEAWAYS:
            summary = (
                f"🎯 Önemli Noktalar:\n\n"
                f"1. Bu videoda öğrendiklerinizi uygulamaya geçirin\n"
                f"2. Anlamadığınız kısımları tekrar izleyin\n"
                f"3. Not alarak öğrenmenizi pekiştirin\n"
                f"4. Sorularınızı AI asistana sorabilirsiniz"
            )
        
        elif summary_type == VideoSummary.SummaryType.DETAILED:
            summary = (
                f"'{content_title}' Detaylı Özeti\n\n"
                f"Bu video {word_count} kelimelik kapsamlı bir içerik sunmaktadır. "
                f"Video boyunca ele alınan konular aşağıda detaylı olarak özetlenmiştir.\n\n"
                f"Giriş bölümünde temel kavramlar tanıtılmakta, ardından pratik "
                f"örneklerle konu pekiştirilmektedir. Sonuç bölümünde ise öğrenilenlerin "
                f"bir özeti sunulmaktadır.\n\n"
                f"Videonun tamamını izlemeniz önerilir."
            )
        
        else:
            summary = (
                f"'{content_title}' için özet oluşturuldu. "
                f"İçerik {word_count} kelime içermektedir."
            )
        
        return {
            'summary': summary,
            'tokens_used': len(summary.split()) * 2,
            'model': 'mock-model-v1',
        }
    
    @classmethod
    @transaction.atomic
    def delete_summary(cls, summary: VideoSummary) -> None:
        """Özeti sil."""
        summary.delete()

