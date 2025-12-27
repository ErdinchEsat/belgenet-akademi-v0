"""
Live Session Service
====================

Canlı ders iş mantığı servisi.
"""

import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ..models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionPolicy,
    LiveProviderConfig,
)
from ..providers import get_provider

logger = logging.getLogger(__name__)


class LiveSessionService:
    """
    Canlı ders işlem servisi.
    """
    
    @classmethod
    @transaction.atomic
    def create_session(
        cls,
        tenant,
        course,
        title: str,
        scheduled_start,
        scheduled_end,
        created_by,
        session_type: str = LiveSession.Type.SCHEDULED,
        description: str = '',
        content=None,
        **kwargs
    ) -> LiveSession:
        """
        Yeni canlı ders oluştur.
        
        Args:
            tenant: Tenant instance
            course: Course instance
            title: Ders başlığı
            scheduled_start: Planlanan başlangıç
            scheduled_end: Planlanan bitiş
            created_by: Oluşturan kullanıcı
            session_type: scheduled, adhoc, webinar
            description: Açıklama
            content: İlişkili CourseContent (opsiyonel)
            **kwargs: Ek ayarlar
            
        Returns:
            LiveSession: Oluşturulan oturum
        """
        # Provider config al
        config = LiveProviderConfig.objects.filter(
            tenant=tenant,
            is_active=True,
            is_default=True
        ).first()
        
        if not config:
            raise ValueError("Aktif canlı ders sağlayıcısı bulunamadı")
        
        # Varsayılan ayarları policy'den al
        policy = LiveSessionPolicy.get_effective_policy_for_course(course, tenant)
        
        session = LiveSession.objects.create(
            tenant=tenant,
            course=course,
            content=content,
            created_by=created_by,
            title=title,
            description=description,
            type=session_type,
            status=LiveSession.Status.SCHEDULED,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            provider=config.provider,
            recording_enabled=kwargs.get('recording_enabled', policy.recording_required if policy else True),
            auto_recording=kwargs.get('auto_recording', policy.auto_recording if policy else False),
            waiting_room_enabled=kwargs.get('waiting_room_enabled', policy.lobby_enabled if policy else True),
            students_can_share_screen=kwargs.get('students_can_share_screen', policy.students_can_share_screen if policy else False),
            students_start_muted=kwargs.get('students_start_muted', policy.students_start_muted if policy else True),
            students_video_off=kwargs.get('students_video_off', policy.students_video_off if policy else False),
            max_participants=kwargs.get('max_participants', 100),
        )
        
        # Provider'da oda oluştur
        try:
            provider = get_provider(tenant)
            room_info = provider.create_room(session)
            session.room_url = room_info.room_url
            session.room_password = room_info.password or ''
            session.save(update_fields=['room_url', 'room_password'])
        except Exception as e:
            logger.error(f"Provider room creation failed: {e}")
            # Session yine de oluşturuldu, provider sonra retry edilebilir
        
        logger.info(f"Live session created: {session.id} - {session.title}")
        
        # Hatırlatıcı task'larını planla
        cls._schedule_reminders(session)
        
        return session
    
    @classmethod
    def _schedule_reminders(cls, session: LiveSession):
        """Hatırlatıcı task'larını planla."""
        from ..tasks import send_reminder_24h, send_reminder_1h, send_reminder_10m
        
        now = timezone.now()
        start = session.scheduled_start
        
        # 24 saat önce
        remind_24h = start - timedelta(hours=24)
        if remind_24h > now:
            send_reminder_24h.apply_async(
                args=[str(session.id)],
                eta=remind_24h
            )
        
        # 1 saat önce
        remind_1h = start - timedelta(hours=1)
        if remind_1h > now:
            send_reminder_1h.apply_async(
                args=[str(session.id)],
                eta=remind_1h
            )
        
        # 10 dakika önce
        remind_10m = start - timedelta(minutes=10)
        if remind_10m > now:
            send_reminder_10m.apply_async(
                args=[str(session.id)],
                eta=remind_10m
            )
    
    @classmethod
    @transaction.atomic
    def start_session(cls, session: LiveSession) -> bool:
        """
        Oturumu başlat.
        
        Args:
            session: Başlatılacak oturum
            
        Returns:
            bool: Başarılı ise True
        """
        if session.status not in [LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]:
            raise ValueError(f"Cannot start session in status: {session.status}")
        
        # Provider'da başlat
        provider = get_provider(session.tenant)
        provider.start_session(session)
        
        # Status güncelle
        session.start()
        
        # Auto recording
        if session.auto_recording:
            try:
                recording_id = provider.start_recording(session)
                logger.info(f"Auto recording started: {recording_id}")
            except Exception as e:
                logger.error(f"Auto recording failed: {e}")
        
        logger.info(f"Live session started: {session.id}")
        return True
    
    @classmethod
    @transaction.atomic
    def end_session(cls, session: LiveSession) -> bool:
        """
        Oturumu sonlandır.
        
        Args:
            session: Sonlandırılacak oturum
            
        Returns:
            bool: Başarılı ise True
        """
        if session.status != LiveSession.Status.LIVE:
            raise ValueError(f"Cannot end session in status: {session.status}")
        
        # Provider'da sonlandır
        provider = get_provider(session.tenant)
        provider.end_session(session)
        
        # Status güncelle
        session.end()
        
        # Tüm aktif katılımcıları çıkar
        now = timezone.now()
        active_participants = LiveSessionParticipant.objects.filter(
            session=session,
            is_active=True
        )
        
        for participant in active_participants:
            participant.left_at = now
            participant.is_active = False
            if participant.joined_at:
                participant.duration_seconds = int((now - participant.joined_at).total_seconds())
            participant.save()
        
        logger.info(f"Live session ended: {session.id}")
        
        # Attendance hesaplama task'ı tetikle
        from ..tasks import calculate_attendance_task
        calculate_attendance_task.delay(str(session.id))
        
        return True
    
    @classmethod
    def get_upcoming_sessions(cls, tenant, user, limit: int = 10):
        """
        Yaklaşan oturumları getir.
        
        Args:
            tenant: Tenant instance
            user: User instance
            limit: Maksimum sonuç sayısı
            
        Returns:
            QuerySet: Yaklaşan oturumlar
        """
        from backend.courses.models import Enrollment
        
        now = timezone.now()
        queryset = LiveSession.objects.filter(
            tenant=tenant,
            scheduled_start__gte=now,
            status__in=[LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]
        )
        
        # Öğrenci sadece kayıtlı olduğu kursların derslerini görür
        if user.role == 'STUDENT':
            enrolled_courses = Enrollment.objects.filter(
                user=user,
                status=Enrollment.Status.ACTIVE
            ).values_list('course_id', flat=True)
            queryset = queryset.filter(course_id__in=enrolled_courses)
        
        return queryset.order_by('scheduled_start')[:limit]
    
    @classmethod
    def get_active_sessions(cls, tenant, user=None):
        """
        Aktif (yayında) oturumları getir.
        
        Args:
            tenant: Tenant instance
            user: User instance (opsiyonel)
            
        Returns:
            QuerySet: Aktif oturumlar
        """
        queryset = LiveSession.objects.filter(
            tenant=tenant,
            status=LiveSession.Status.LIVE
        )
        
        if user and user.role == 'STUDENT':
            from backend.courses.models import Enrollment
            enrolled_courses = Enrollment.objects.filter(
                user=user,
                status=Enrollment.Status.ACTIVE
            ).values_list('course_id', flat=True)
            queryset = queryset.filter(course_id__in=enrolled_courses)
        
        return queryset.order_by('-actual_start')

