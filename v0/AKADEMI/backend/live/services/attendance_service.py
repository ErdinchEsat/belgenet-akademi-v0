"""
Attendance Service
==================

Katılım takibi ve hesaplama servisi.
"""

import hashlib
import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ..models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionAttendanceSummary,
    LiveSessionPolicy,
)

logger = logging.getLogger(__name__)


class AttendanceService:
    """
    Katılım takibi servisi.
    """
    
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """
        IP adresini hash'le (KVKK uyumu).
        
        Args:
            ip_address: Ham IP adresi
            
        Returns:
            str: SHA-256 hash
        """
        if not ip_address:
            return ''
        
        # Salt ekle
        salt = 'edutech-live-session-2024'
        data = f"{salt}:{ip_address}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @classmethod
    @transaction.atomic
    def record_join(
        cls,
        session: LiveSession,
        user,
        role: str = 'participant',
        device_type: str = '',
        browser: str = '',
        ip_address: str = ''
    ) -> LiveSessionParticipant:
        """
        Katılımı kaydet.
        
        Args:
            session: Oturum
            user: Kullanıcı
            role: host, moderator, participant
            device_type: Cihaz türü
            browser: Tarayıcı bilgisi
            ip_address: IP adresi
            
        Returns:
            LiveSessionParticipant: Oluşturulan kayıt
        """
        participant = LiveSessionParticipant.objects.create(
            session=session,
            user=user,
            role=role,
            joined_at=timezone.now(),
            device_type=device_type[:50] if device_type else '',
            browser=browser[:100] if browser else '',
            ip_hash=cls.hash_ip(ip_address),
        )
        
        # Session katılımcı sayısını güncelle
        session.participant_count = session.participants.filter(is_active=True).count()
        session.peak_participants = max(session.peak_participants, session.participant_count)
        session.save(update_fields=['participant_count', 'peak_participants'])
        
        logger.info(f"Participant joined: {user.email} -> {session.room_id}")
        
        return participant
    
    @classmethod
    @transaction.atomic
    def record_leave(cls, participant: LiveSessionParticipant) -> None:
        """
        Ayrılmayı kaydet.
        
        Args:
            participant: Katılımcı kaydı
        """
        if not participant.is_active:
            return
        
        now = timezone.now()
        participant.left_at = now
        participant.is_active = False
        
        if participant.joined_at:
            participant.duration_seconds = int((now - participant.joined_at).total_seconds())
        
        participant.save()
        
        # Session katılımcı sayısını güncelle
        session = participant.session
        session.participant_count = session.participants.filter(is_active=True).count()
        session.save(update_fields=['participant_count'])
        
        logger.info(f"Participant left: {participant.user.email} -> {session.room_id}")
    
    @classmethod
    def update_heartbeat(
        cls,
        participant: LiveSessionParticipant,
        is_background: bool = False
    ) -> None:
        """
        Heartbeat güncelle.
        
        Args:
            participant: Katılımcı kaydı
            is_background: Sekme arka planda mı
        """
        now = timezone.now()
        
        # Arka plan süresini hesapla
        if is_background and participant.last_heartbeat:
            delta = (now - participant.last_heartbeat).total_seconds()
            participant.background_duration_seconds += int(delta)
        
        participant.last_heartbeat = now
        participant.save(update_fields=['last_heartbeat', 'background_duration_seconds'])
    
    @classmethod
    @transaction.atomic
    def calculate_attendance_summary(cls, session: LiveSession) -> None:
        """
        Oturum için katılım özetlerini hesapla.
        
        Session kapandığında çağrılır.
        
        Args:
            session: Oturum
        """
        if session.status != LiveSession.Status.ENDED:
            logger.warning(f"Session not ended, skipping attendance calculation: {session.id}")
            return
        
        # Policy al
        policy = LiveSessionPolicy.get_effective_policy(session)
        
        # Session süresi
        session_duration = session.total_duration_minutes * 60  # saniye
        if session_duration == 0:
            if session.actual_start and session.actual_end:
                session_duration = int((session.actual_end - session.actual_start).total_seconds())
            else:
                session_duration = session.duration_minutes * 60
        
        # Tüm katılımları kullanıcı bazında grupla
        participants = LiveSessionParticipant.objects.filter(session=session)
        
        user_participations = {}
        for p in participants:
            if p.user_id not in user_participations:
                user_participations[p.user_id] = []
            user_participations[p.user_id].append(p)
        
        # Her kullanıcı için özet oluştur
        for user_id, user_parts in user_participations.items():
            cls._create_or_update_summary(
                session=session,
                user_id=user_id,
                participations=user_parts,
                session_duration=session_duration,
                policy=policy
            )
        
        logger.info(f"Attendance calculated for session: {session.id}, users: {len(user_participations)}")
    
    @classmethod
    def _create_or_update_summary(
        cls,
        session: LiveSession,
        user_id,
        participations: list,
        session_duration: int,
        policy: Optional[LiveSessionPolicy]
    ) -> LiveSessionAttendanceSummary:
        """
        Kullanıcı için katılım özeti oluştur/güncelle.
        """
        user = participations[0].user
        
        # Toplam süre hesapla
        total_duration = sum(p.duration_seconds for p in participations)
        background_duration = sum(p.background_duration_seconds for p in participations)
        
        # İlk katılım ve son ayrılış
        first_join = min(p.joined_at for p in participations)
        last_leave = max((p.left_at or p.joined_at) for p in participations)
        
        # Katılım yüzdesi
        effective_duration = total_duration - background_duration
        if session_duration > 0:
            attendance_percent = (effective_duration / session_duration) * 100
        else:
            attendance_percent = 0
        attendance_percent = min(100, max(0, attendance_percent))
        
        # Policy'ye göre attended kararı
        threshold = policy.attendance_threshold_percent if policy else 70
        min_duration = policy.minimum_duration_minutes * 60 if policy else 300  # 5 dk
        
        attended = (
            attendance_percent >= threshold or
            effective_duration >= min_duration
        )
        
        # Geç katılım kontrolü
        late_tolerance = timedelta(minutes=policy.late_join_tolerance_minutes if policy else 10)
        late_join = (first_join - session.actual_start) > late_tolerance if session.actual_start else False
        
        # Erken ayrılış kontrolü
        early_tolerance = timedelta(minutes=policy.early_leave_tolerance_minutes if policy else 10)
        early_leave = (session.actual_end - last_leave) > early_tolerance if session.actual_end else False
        
        # Özet oluştur/güncelle
        summary, created = LiveSessionAttendanceSummary.objects.update_or_create(
            session=session,
            user=user,
            defaults={
                'total_duration_seconds': total_duration,
                'join_count': len(participations),
                'first_join': first_join,
                'last_leave': last_leave,
                'attended': attended,
                'attendance_percent': round(attendance_percent, 2),
                'late_join': late_join,
                'early_leave': early_leave,
                'background_duration_seconds': background_duration,
            }
        )
        
        return summary
    
    @classmethod
    def get_attendance_report(cls, session: LiveSession) -> dict:
        """
        Yoklama raporu oluştur.
        
        Args:
            session: Oturum
            
        Returns:
            dict: Rapor verisi
        """
        from backend.courses.models import Enrollment
        
        summaries = LiveSessionAttendanceSummary.objects.filter(
            session=session
        ).select_related('user')
        
        # Enrolled count
        total_enrolled = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).count()
        
        total_attended = summaries.filter(attended=True).count()
        attendance_rate = (total_attended / total_enrolled * 100) if total_enrolled > 0 else 0
        
        return {
            'session': session,
            'total_enrolled': total_enrolled,
            'total_attended': total_attended,
            'attendance_rate': round(attendance_rate, 2),
            'summaries': list(summaries),
        }

