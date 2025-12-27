"""
Transcript Service
==================

Transkript yönetim servisi.
"""

import re
import logging
from typing import List, Dict, Optional
from django.db import transaction
from django.db.models import Q

from backend.courses.models import CourseContent
from ..models import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


class TranscriptService:
    """
    Transkript yönetim servisi.
    
    Sorumluluklar:
    - Transkript CRUD
    - SRT/VTT parse
    - Arama
    - Segment getirme
    """
    
    @classmethod
    def get_transcript(
        cls,
        content: CourseContent,
        language: str = 'tr',
    ) -> Optional[Transcript]:
        """
        İçerik için transkript getir.
        """
        return Transcript.objects.filter(
            content=content,
            language=language,
            status=Transcript.TranscriptStatus.COMPLETED,
        ).prefetch_related('segments').first()
    
    @classmethod
    def get_available_languages(cls, content: CourseContent) -> List[str]:
        """
        İçerik için mevcut transkript dillerini getir.
        """
        return list(
            Transcript.objects.filter(
                content=content,
                status=Transcript.TranscriptStatus.COMPLETED,
            ).values_list('language', flat=True)
        )
    
    @classmethod
    def get_segment_at_time(
        cls,
        transcript: Transcript,
        video_ts: float,
    ) -> Optional[TranscriptSegment]:
        """
        Belirli bir zamandaki segmenti getir.
        """
        return TranscriptSegment.objects.filter(
            transcript=transcript,
            start_ts__lte=video_ts,
            end_ts__gte=video_ts,
        ).first()
    
    @classmethod
    def get_segments_in_range(
        cls,
        transcript: Transcript,
        start_ts: float,
        end_ts: float,
    ) -> List[TranscriptSegment]:
        """
        Zaman aralığındaki segmentleri getir.
        """
        return list(
            TranscriptSegment.objects.filter(
                transcript=transcript,
                start_ts__gte=start_ts,
                end_ts__lte=end_ts,
            ).order_by('sequence')
        )
    
    @classmethod
    def search_transcript(
        cls,
        transcript: Transcript,
        query: str,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Transkriptte arama yap.
        
        Returns:
            [
                {
                    'segment_id': uuid,
                    'start_ts': 120.5,
                    'end_ts': 125.0,
                    'text': '...',
                    'highlight': '...keyword...',
                    'relevance': 0.85
                }
            ]
        """
        # Basit case-insensitive arama
        query_lower = query.lower()
        
        segments = TranscriptSegment.objects.filter(
            transcript=transcript,
            text__icontains=query,
        ).order_by('sequence')[:limit]
        
        results = []
        for segment in segments:
            # Highlight oluştur
            text_lower = segment.text.lower()
            pos = text_lower.find(query_lower)
            
            if pos >= 0:
                # Keyword etrafında context göster
                start = max(0, pos - 30)
                end = min(len(segment.text), pos + len(query) + 30)
                highlight = segment.text[start:end]
                
                if start > 0:
                    highlight = '...' + highlight
                if end < len(segment.text):
                    highlight = highlight + '...'
                
                results.append({
                    'segment_id': segment.id,
                    'start_ts': segment.start_ts,
                    'end_ts': segment.end_ts,
                    'text': segment.text,
                    'highlight': highlight,
                    'relevance': 1.0,  # Basit arama için sabit
                })
        
        return results
    
    @classmethod
    @transaction.atomic
    def import_srt(
        cls,
        content: CourseContent,
        srt_content: str,
        language: str = 'tr',
    ) -> Transcript:
        """
        SRT formatından transkript içe aktar.
        """
        # Mevcut transkripti kontrol et
        existing = Transcript.objects.filter(
            content=content,
            language=language,
        ).first()
        
        if existing:
            # Güncelle
            transcript = existing
            transcript.raw_content = srt_content
            transcript.status = Transcript.TranscriptStatus.PROCESSING
            transcript.save()
            
            # Eski segmentleri sil
            transcript.segments.all().delete()
        else:
            # Yeni oluştur
            transcript = Transcript.objects.create(
                tenant=content.module.course.tenant,
                course=content.module.course,
                content=content,
                language=language,
                source=Transcript.TranscriptSource.IMPORTED,
                status=Transcript.TranscriptStatus.PROCESSING,
                raw_content=srt_content,
            )
        
        # Parse SRT
        segments = cls._parse_srt(srt_content)
        
        # Segmentleri kaydet
        full_text_parts = []
        for i, seg in enumerate(segments):
            TranscriptSegment.objects.create(
                transcript=transcript,
                sequence=i + 1,
                start_ts=seg['start'],
                end_ts=seg['end'],
                text=seg['text'],
            )
            full_text_parts.append(seg['text'])
        
        # Transkripti güncelle
        full_text = ' '.join(full_text_parts)
        transcript.full_text = full_text
        transcript.word_count = len(full_text.split())
        transcript.segment_count = len(segments)
        if segments:
            transcript.duration_seconds = int(segments[-1]['end'])
        transcript.status = Transcript.TranscriptStatus.COMPLETED
        transcript.save()
        
        logger.info(f"Transcript imported: content={content.id}, segments={len(segments)}")
        
        return transcript
    
    @classmethod
    def _parse_srt(cls, srt_content: str) -> List[Dict]:
        """
        SRT formatını parse et.
        
        Returns:
            [{'start': 0.0, 'end': 2.5, 'text': '...'}]
        """
        segments = []
        
        # SRT blokları: numara, zaman, metin, boş satır
        pattern = r'(\d+)\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+(.+?)(?=\n\n|\Z)'
        
        matches = re.findall(pattern, srt_content, re.DOTALL)
        
        for match in matches:
            _, start_time, end_time, text = match
            
            start_seconds = cls._time_to_seconds(start_time)
            end_seconds = cls._time_to_seconds(end_time)
            
            # Satır sonlarını temizle
            text = text.strip().replace('\n', ' ')
            
            segments.append({
                'start': start_seconds,
                'end': end_seconds,
                'text': text,
            })
        
        return segments
    
    @classmethod
    def _time_to_seconds(cls, time_str: str) -> float:
        """
        SRT zaman formatını saniyeye çevir.
        
        '00:01:30,500' -> 90.5
        """
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    @classmethod
    def get_text_around_time(
        cls,
        transcript: Transcript,
        video_ts: float,
        context_seconds: int = 60,
    ) -> str:
        """
        Belirli bir zaman etrafındaki transkript metnini getir.
        
        AI context için kullanılır.
        """
        start = max(0, video_ts - context_seconds)
        end = video_ts + context_seconds
        
        segments = cls.get_segments_in_range(transcript, start, end)
        
        return ' '.join([s.text for s in segments])

