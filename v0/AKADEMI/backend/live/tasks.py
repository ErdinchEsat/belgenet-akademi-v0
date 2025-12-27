"""
Live Session Celery Tasks
=========================

Asenkron görevler: bildirimler, kayıt işleme, temizlik.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_reminder_24h(self, session_id: str):
    """
    24 saat öncesi hatırlatıcı.
    
    Args:
        session_id: LiveSession UUID
    """
    from .models import LiveSession
    from backend.courses.models import Enrollment
    
    try:
        session = LiveSession.objects.get(id=session_id)
        
        # Session hala aktif mi kontrol et
        if session.status not in [LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]:
            logger.info(f"Session {session_id} no longer scheduled, skipping reminder")
            return
        
        # Enrolled users
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            # Bildirim tercihi kontrolü
            if not user.notify_email:
                continue
            
            # E-posta gönder
            send_session_reminder_email.delay(
                user_id=str(user.id),
                session_id=session_id,
                reminder_type='24h'
            )
        
        logger.info(f"24h reminders sent for session {session_id}")
        
    except LiveSession.DoesNotExist:
        logger.error(f"Session not found: {session_id}")
    except Exception as e:
        logger.error(f"Failed to send 24h reminders: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_reminder_1h(self, session_id: str):
    """
    1 saat öncesi hatırlatıcı.
    """
    from .models import LiveSession
    from backend.courses.models import Enrollment
    
    try:
        session = LiveSession.objects.get(id=session_id)
        
        if session.status not in [LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]:
            return
        
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            # E-posta + Push
            if user.notify_email:
                send_session_reminder_email.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='1h'
                )
            
            if user.notify_push:
                send_session_reminder_push.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='1h'
                )
        
        logger.info(f"1h reminders sent for session {session_id}")
        
    except LiveSession.DoesNotExist:
        logger.error(f"Session not found: {session_id}")
    except Exception as e:
        logger.error(f"Failed to send 1h reminders: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_reminder_10m(self, session_id: str):
    """
    10 dakika öncesi hatırlatıcı (sadece push).
    """
    from .models import LiveSession
    from backend.courses.models import Enrollment
    
    try:
        session = LiveSession.objects.get(id=session_id)
        
        if session.status not in [LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]:
            return
        
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            if user.notify_push:
                send_session_reminder_push.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='10m'
                )
        
        logger.info(f"10m reminders sent for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to send 10m reminders: {e}")


@shared_task
def send_session_reminder_email(user_id: str, session_id: str, reminder_type: str):
    """
    Hatırlatıcı e-postası gönder.
    """
    from .models import LiveSession
    from backend.users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        session = LiveSession.objects.get(id=session_id)
        
        # E-posta şablonu ve gönderimi
        # TODO: E-posta servisi entegrasyonu
        logger.info(f"Would send {reminder_type} email to {user.email} for session {session.title}")
        
    except Exception as e:
        logger.error(f"Failed to send reminder email: {e}")


@shared_task
def send_session_reminder_push(user_id: str, session_id: str, reminder_type: str):
    """
    Hatırlatıcı push bildirimi gönder.
    """
    from .models import LiveSession
    from backend.users.models import User
    
    try:
        user = User.objects.get(id=user_id)
        session = LiveSession.objects.get(id=session_id)
        
        # Push notification
        # TODO: Push servisi entegrasyonu (Firebase, OneSignal, vb.)
        logger.info(f"Would send {reminder_type} push to {user.email} for session {session.title}")
        
    except Exception as e:
        logger.error(f"Failed to send reminder push: {e}")


@shared_task
def notify_session_started(session_id: str):
    """
    Oturum başladı bildirimi.
    """
    from .models import LiveSession
    from backend.courses.models import Enrollment
    
    try:
        session = LiveSession.objects.get(id=session_id)
        
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            if user.notify_push:
                send_session_reminder_push.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='started'
                )
        
        logger.info(f"Session started notifications sent: {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to send session started notifications: {e}")


@shared_task
def notify_session_cancelled(session_id: str, reason: str = ''):
    """
    Oturum iptal bildirimi.
    """
    from .models import LiveSession
    from backend.courses.models import Enrollment
    
    try:
        session = LiveSession.objects.get(id=session_id)
        
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            # E-posta + Push
            if user.notify_email:
                send_session_reminder_email.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='cancelled'
                )
            
            if user.notify_push:
                send_session_reminder_push.delay(
                    user_id=str(user.id),
                    session_id=session_id,
                    reminder_type='cancelled'
                )
        
        logger.info(f"Session cancelled notifications sent: {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to send session cancelled notifications: {e}")


@shared_task
def notify_recording_published(recording_id: str):
    """
    Kayıt yayınlandı bildirimi.
    """
    from .models import LiveSessionRecording
    from backend.courses.models import Enrollment
    
    try:
        recording = LiveSessionRecording.objects.get(id=recording_id)
        session = recording.session
        
        enrollments = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).select_related('user')
        
        for enrollment in enrollments:
            user = enrollment.user
            
            if user.notify_email:
                # E-posta gönder
                logger.info(f"Would send recording published email to {user.email}")
        
        logger.info(f"Recording published notifications sent: {recording_id}")
        
    except Exception as e:
        logger.error(f"Failed to send recording published notifications: {e}")


@shared_task(bind=True, max_retries=3)
def calculate_attendance_task(self, session_id: str):
    """
    Katılım özetlerini hesapla.
    
    Session kapandığında çağrılır.
    """
    from .models import LiveSession
    from .services.attendance_service import AttendanceService
    
    try:
        session = LiveSession.objects.get(id=session_id)
        AttendanceService.calculate_attendance_summary(session)
        logger.info(f"Attendance calculated for session: {session_id}")
        
    except LiveSession.DoesNotExist:
        logger.error(f"Session not found: {session_id}")
    except Exception as e:
        logger.error(f"Failed to calculate attendance: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_recording_task(self, recording_id: str):
    """
    Kayıt dosyasını işle.
    
    Provider'dan indir, storage'a yükle, thumbnail oluştur.
    """
    from .models import LiveSessionRecording
    from .services.recording_service import RecordingService
    
    try:
        recording = LiveSessionRecording.objects.get(id=recording_id)
        
        if recording.status != LiveSessionRecording.Status.PROCESSING:
            logger.info(f"Recording {recording_id} not in processing status")
            return
        
        # Provider URL'den indir
        if recording.provider_url:
            # TODO: Dosya indirme ve storage'a yükleme
            # Bu işlem provider'a ve storage backend'ine göre değişir
            logger.info(f"Would download recording from: {recording.provider_url}")
            
            # Örnek: Storage'a yükle
            # storage_url = StorageService.upload_recording(recording.provider_url)
            # RecordingService.process_recording(recording, storage_url, storage_path)
            
            # Şimdilik sadece status güncelle
            recording.status = LiveSessionRecording.Status.READY
            recording.save(update_fields=['status'])
        
        # Thumbnail oluştur
        RecordingService.generate_thumbnail(recording)
        
        logger.info(f"Recording processed: {recording_id}")
        
    except LiveSessionRecording.DoesNotExist:
        logger.error(f"Recording not found: {recording_id}")
    except Exception as e:
        logger.error(f"Failed to process recording: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def cleanup_expired_recordings():
    """
    Süresi dolan kayıtları temizle.
    
    Celery beat ile günlük çalışır.
    """
    from .services.recording_service import RecordingService
    
    try:
        count = RecordingService.cleanup_expired_recordings()
        logger.info(f"Cleaned up {count} expired recordings")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired recordings: {e}")


@shared_task
def cleanup_stale_participants():
    """
    Heartbeat almayan katılımcıları temizle.
    
    5 dakikadan fazla heartbeat almayan aktif katılımcıları çıkar.
    """
    from .models import LiveSessionParticipant
    
    try:
        threshold = timezone.now() - timedelta(minutes=5)
        
        stale = LiveSessionParticipant.objects.filter(
            is_active=True,
            last_heartbeat__lt=threshold
        )
        
        count = 0
        for participant in stale:
            participant.left_at = participant.last_heartbeat or timezone.now()
            participant.is_active = False
            if participant.joined_at:
                participant.duration_seconds = int(
                    (participant.left_at - participant.joined_at).total_seconds()
                )
            participant.save()
            count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} stale participants")
        
    except Exception as e:
        logger.error(f"Failed to cleanup stale participants: {e}")


@shared_task
def check_webhook_health():
    """
    Webhook sağlık kontrolü.
    
    Son 1 saatte webhook failure rate kontrol et.
    """
    # TODO: Webhook log/metrics kontrolü
    logger.info("Webhook health check completed")


# Celery Beat Schedule için örnek
# settings.py veya celery.py'da tanımlanmalı:
#
# CELERY_BEAT_SCHEDULE = {
#     'cleanup-expired-recordings': {
#         'task': 'backend.live.tasks.cleanup_expired_recordings',
#         'schedule': crontab(hour=2, minute=0),  # Her gün 02:00
#     },
#     'cleanup-stale-participants': {
#         'task': 'backend.live.tasks.cleanup_stale_participants',
#         'schedule': crontab(minute='*/5'),  # Her 5 dakika
#     },
#     'check-webhook-health': {
#         'task': 'backend.live.tasks.check_webhook_health',
#         'schedule': crontab(minute='*/15'),  # Her 15 dakika
#     },
# }

