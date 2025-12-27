"""
Session Service
===============

Playback session iş mantığı.
"""

import hashlib
import logging
from typing import Optional, Tuple
from django.utils import timezone

from backend.courses.models import Course, CourseContent, ContentProgress, Enrollment
from ..models import PlaybackSession

logger = logging.getLogger(__name__)


class SessionService:
    """
    Playback session yönetim servisi.
    
    Sorumluluklar:
    - Session oluşturma
    - Resume bilgisi hesaplama
    - Heartbeat işleme
    - Session sonlandırma
    - Stale session temizleme
    """
    
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """IP adresini hash'le (GDPR uyumu)."""
        if not ip_address:
            return None
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_client_ip(request) -> str:
        """Request'ten client IP adresini al."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    @classmethod
    def create_session(
        cls,
        user,
        course: Course,
        content: CourseContent,
        device_id: str = None,
        user_agent: str = None,
        ip_address: str = None,
    ) -> Tuple[PlaybackSession, dict]:
        """
        Yeni playback session oluştur.
        
        Args:
            user: Kullanıcı
            course: Kurs
            content: İçerik
            device_id: Cihaz ID
            user_agent: User agent string
            ip_address: Client IP adresi
        
        Returns:
            Tuple[PlaybackSession, dict]: (Session, Resume bilgisi)
        """
        # Eski aktif session'ları kapat
        PlaybackSession.close_stale_sessions(user, content)
        
        # Yeni session oluştur
        session = PlaybackSession.objects.create(
            tenant=user.tenant,
            user=user,
            course=course,
            content=content,
            device_id=device_id,
            user_agent=user_agent,
            ip_hash=cls.hash_ip(ip_address),
            last_heartbeat_at=timezone.now(),
        )
        
        # Resume bilgisini al
        resume = cls.get_resume_info(user, course, content)
        
        logger.info(
            f"Session created: {session.id} for user {user.id} content {content.id}"
        )
        
        return session, resume
    
    @staticmethod
    def get_resume_info(user, course: Course, content: CourseContent) -> dict:
        """
        Resume bilgisini getir.
        
        ContentProgress'den son izleme durumunu çeker.
        """
        # Enrollment'ı kontrol et
        try:
            enrollment = Enrollment.objects.get(user=user, course=course)
        except Enrollment.DoesNotExist:
            return {
                'last_position_seconds': 0,
                'watched_seconds': 0,
                'is_completed': False,
                'completion_ratio': 0.0,
            }
        
        # ContentProgress'i al veya oluştur
        progress, _ = ContentProgress.objects.get_or_create(
            enrollment=enrollment,
            content=content,
            defaults={
                'watched_seconds': 0,
                'last_position_seconds': 0,
                'is_completed': False,
                'progress_percent': 0,
            }
        )
        
        # Completion ratio hesapla
        content_duration = content.duration_minutes * 60 if content.duration_minutes else 0
        completion_ratio = 0.0
        if content_duration > 0:
            completion_ratio = min(progress.watched_seconds / content_duration, 1.0)
        
        return {
            'last_position_seconds': progress.last_position_seconds,
            'watched_seconds': progress.watched_seconds,
            'is_completed': progress.is_completed,
            'completion_ratio': round(completion_ratio, 4),
        }
    
    @staticmethod
    def process_heartbeat(
        session: PlaybackSession,
        position_seconds: int = None,
        playback_rate: float = 1.0,
    ) -> PlaybackSession:
        """
        Heartbeat işle.
        
        Args:
            session: Playback session
            position_seconds: Mevcut video pozisyonu
            playback_rate: Oynatma hızı
        
        Returns:
            Güncellenmiş session
        """
        session.heartbeat(position_seconds)
        
        logger.debug(
            f"Heartbeat: session={session.id}, position={position_seconds}"
        )
        
        return session
    
    @staticmethod
    def end_session(
        session: PlaybackSession,
        reason: str = None,
        final_position: int = None,
    ) -> PlaybackSession:
        """
        Session'ı sonlandır.
        
        Args:
            session: Playback session
            reason: Sonlanma nedeni
            final_position: Son pozisyon
        
        Returns:
            Sonlandırılmış session
        """
        if final_position is not None:
            session.last_position_seconds = final_position
        
        session.end_session(reason)
        
        logger.info(
            f"Session ended: {session.id}, reason={reason}"
        )
        
        return session
    
    @staticmethod
    def cleanup_stale_sessions(minutes: int = 30):
        """
        Timeout olmuş session'ları temizle.
        
        Celery task olarak periyodik çalıştırılabilir.
        """
        threshold = timezone.now() - timezone.timedelta(minutes=minutes)
        
        stale_sessions = PlaybackSession.objects.filter(
            is_active=True,
            last_heartbeat_at__lt=threshold,
        )
        
        count = stale_sessions.update(
            is_active=False,
            ended_at=timezone.now(),
            ended_reason=PlaybackSession.EndReason.TIMEOUT,
        )
        
        if count > 0:
            logger.info(f"Cleaned up {count} stale sessions")
        
        return count

