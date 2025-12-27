"""
Progress Service
================

Video ilerleme iş mantığı.
Server-side validation ve watched_seconds hesaplama.
"""

import logging
from typing import Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from backend.courses.models import Course, CourseContent, Enrollment
from backend.player.models import PlaybackSession
from ..models import VideoProgress, ProgressWatchWindow

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Video ilerleme yönetim servisi.
    
    Sorumluluklar:
    - Progress oluşturma/getirme
    - watched_seconds server-side hesaplama
    - Watch window kaydı
    - Completion kontrolü
    - Sequencing policy tetikleme
    """
    
    # Completion için minimum izleme oranı
    DEFAULT_COMPLETION_THRESHOLD = 0.80
    
    # Maksimum tek seferde eklenebilecek süre (abuse prevention)
    MAX_DELTA_SECONDS = 60
    
    @classmethod
    def get_or_create_progress(
        cls,
        user,
        course: Course,
        content: CourseContent,
    ) -> Tuple[VideoProgress, bool]:
        """
        Progress kaydını getir veya oluştur.
        
        Returns:
            Tuple[VideoProgress, created]: (Progress objesi, Yeni oluşturuldu mu?)
        """
        progress, created = VideoProgress.objects.get_or_create(
            tenant=user.tenant,
            user=user,
            content=content,
            defaults={
                'course': course,
                'watched_seconds': 0,
                'last_position_seconds': 0,
                'completion_ratio': Decimal('0'),
                'is_completed': False,
            }
        )
        
        if created:
            logger.info(f"Progress created: user={user.id}, content={content.id}")
        
        return progress, created
    
    @classmethod
    def get_progress(cls, user, content: CourseContent) -> Optional[VideoProgress]:
        """Progress kaydını getir (yoksa None)."""
        try:
            return VideoProgress.objects.get(
                tenant=user.tenant,
                user=user,
                content=content,
            )
        except VideoProgress.DoesNotExist:
            return None
    
    @classmethod
    @transaction.atomic
    def update_progress(
        cls,
        user,
        course: Course,
        content: CourseContent,
        session: PlaybackSession,
        last_position_seconds: int,
        client_watched_delta_seconds: int = 0,
        playback_rate: float = 1.0,
        caption_lang: str = None,
    ) -> VideoProgress:
        """
        Progress'i güncelle.
        
        Server-side validation ile watched_seconds hesaplanır.
        Seek yapıldığında watched_seconds artmaz.
        
        Args:
            user: Kullanıcı
            course: Kurs
            content: İçerik
            session: Aktif playback session
            last_position_seconds: Mevcut video pozisyonu
            client_watched_delta_seconds: Client'ın bildirdiği izleme süresi
            playback_rate: Oynatma hızı
            caption_lang: Altyazı dili
        
        Returns:
            Güncellenmiş VideoProgress
        """
        # Progress'i al veya oluştur
        progress, _ = cls.get_or_create_progress(user, course, content)
        
        # Session doğrulama
        if session.user != user or session.content != content:
            logger.warning(f"Session mismatch: session={session.id}, user={user.id}")
            raise ValueError("Invalid session")
        
        if not session.is_active:
            logger.warning(f"Inactive session: {session.id}")
            raise ValueError("Session is not active")
        
        # Delta süre doğrulama
        validated_delta = cls._validate_delta_seconds(
            client_delta=client_watched_delta_seconds,
            playback_rate=playback_rate,
            last_position=progress.last_position_seconds,
            new_position=last_position_seconds,
        )
        
        # Watch window oluştur (delta > 0 ise)
        if validated_delta > 0:
            cls._create_watch_window(
                progress=progress,
                session=session,
                start_ts=progress.last_position_seconds,
                end_ts=last_position_seconds,
                playback_rate=playback_rate,
            )
        
        # Progress güncelle
        progress.watched_seconds += validated_delta
        progress.last_position_seconds = last_position_seconds
        progress.last_session = session
        progress.last_device_id = session.device_id
        
        # Kullanıcı tercihlerini güncelle
        if playback_rate:
            progress.preferred_speed = Decimal(str(playback_rate))
        if caption_lang:
            progress.preferred_caption_lang = caption_lang
        
        # Completion ratio hesapla
        progress.completion_ratio = Decimal(str(progress.calculate_completion_ratio()))
        
        # Tamamlanma kontrolü
        completion_threshold = cls._get_completion_threshold(course)
        if not progress.is_completed and float(progress.completion_ratio) >= completion_threshold:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            logger.info(f"Content completed: user={user.id}, content={content.id}")
            
            # TODO: Sequencing policy tetikle
            # from backend.sequencing.services import PolicyEngine
            # PolicyEngine.evaluate_unlock(user, content)
        
        progress.save()
        
        logger.debug(
            f"Progress updated: user={user.id}, content={content.id}, "
            f"watched={progress.watched_seconds}, position={last_position_seconds}"
        )
        
        return progress
    
    @classmethod
    def _validate_delta_seconds(
        cls,
        client_delta: int,
        playback_rate: float,
        last_position: int,
        new_position: int,
    ) -> int:
        """
        Delta süreyi doğrula.
        
        Kurallar:
        1. Negatif delta kabul edilmez
        2. Gerçek zamandan fazla olamaz (playback_rate'e göre)
        3. Seek yapıldıysa (position ileri/geri atladıysa) delta 0 olur
        """
        if client_delta <= 0:
            return 0
        
        # Maksimum delta kontrolü
        max_delta = min(cls.MAX_DELTA_SECONDS, int(cls.MAX_DELTA_SECONDS * playback_rate))
        validated_delta = min(client_delta, max_delta)
        
        # Seek tespiti
        # Eğer pozisyon değişimi delta'dan çok farklıysa seek yapılmıştır
        position_delta = abs(new_position - last_position)
        
        # Tolerans: delta + %20 margin
        tolerance = validated_delta * 1.2
        
        if position_delta > tolerance * 2:
            # Büyük seek atlandı, delta'yı sıfırla
            logger.debug(
                f"Seek detected: pos_delta={position_delta}, client_delta={client_delta}"
            )
            return 0
        
        return validated_delta
    
    @classmethod
    def _create_watch_window(
        cls,
        progress: VideoProgress,
        session: PlaybackSession,
        start_ts: int,
        end_ts: int,
        playback_rate: float,
    ) -> Optional[ProgressWatchWindow]:
        """İzleme penceresi oluştur."""
        if end_ts <= start_ts:
            return None
        
        window = ProgressWatchWindow.objects.create(
            tenant=progress.tenant,
            session=session,
            progress=progress,
            user=progress.user,
            content=progress.content,
            start_video_ts=start_ts,
            end_video_ts=end_ts,
            playback_rate=Decimal(str(playback_rate)),
            is_verified=True,
        )
        
        return window
    
    @classmethod
    def _get_completion_threshold(cls, course: Course) -> float:
        """Kursun completion threshold'unu getir."""
        # Course'daki completion_percent'i kullan
        if hasattr(course, 'completion_percent') and course.completion_percent:
            return course.completion_percent / 100.0
        return cls.DEFAULT_COMPLETION_THRESHOLD
    
    @classmethod
    def sync_to_enrollment(cls, progress: VideoProgress):
        """
        Progress'i Enrollment ile senkronize et.
        
        Mevcut courses.ContentProgress ve Enrollment modelleri ile uyum.
        """
        try:
            enrollment = Enrollment.objects.get(
                user=progress.user,
                course=progress.course,
            )
            
            # Enrollment'ın completed_contents listesini güncelle
            if progress.is_completed:
                content_id = progress.content.id
                if content_id not in enrollment.completed_contents:
                    enrollment.completed_contents.append(content_id)
                    enrollment.save(update_fields=['completed_contents'])
                    enrollment.update_progress()
                    
        except Enrollment.DoesNotExist:
            logger.warning(
                f"Enrollment not found: user={progress.user.id}, course={progress.course.id}"
            )

