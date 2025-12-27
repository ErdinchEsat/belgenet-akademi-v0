"""
Live Session Signals
====================

Django signals for audit logging and event handling.
"""

import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionRecording,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LiveSession)
def log_session_save(sender, instance, created, **kwargs):
    """Session kaydedildiğinde log tut."""
    if created:
        logger.info(
            f"LiveSession created: {instance.id} - {instance.title}",
            extra={
                'session_id': str(instance.id),
                'tenant_id': str(instance.tenant_id),
                'course_id': str(instance.course_id),
                'created_by': str(instance.created_by_id) if instance.created_by else None,
            }
        )
    else:
        # Status değişikliği özellikle logla
        update_fields = kwargs.get('update_fields')
        if update_fields and 'status' in update_fields:
            logger.info(
                f"LiveSession status changed: {instance.id} -> {instance.status}",
                extra={
                    'session_id': str(instance.id),
                    'status': instance.status,
                }
            )


@receiver(post_save, sender=LiveSessionParticipant)
def log_participant_event(sender, instance, created, **kwargs):
    """Katılımcı eventi logla."""
    if created:
        logger.info(
            f"Participant joined: {instance.user.email} -> {instance.session.room_id}",
            extra={
                'event': 'participant_joined',
                'session_id': str(instance.session_id),
                'user_id': str(instance.user_id),
                'role': instance.role,
            }
        )
    else:
        # Leave event
        update_fields = kwargs.get('update_fields')
        if update_fields and 'is_active' in update_fields and not instance.is_active:
            logger.info(
                f"Participant left: {instance.user.email} -> {instance.session.room_id}",
                extra={
                    'event': 'participant_left',
                    'session_id': str(instance.session_id),
                    'user_id': str(instance.user_id),
                    'duration_seconds': instance.duration_seconds,
                }
            )


@receiver(post_save, sender=LiveSessionRecording)
def log_recording_event(sender, instance, created, **kwargs):
    """Recording eventi logla."""
    if created:
        logger.info(
            f"Recording created: {instance.id}",
            extra={
                'event': 'recording_created',
                'recording_id': str(instance.id),
                'session_id': str(instance.session_id),
            }
        )
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields and 'status' in update_fields:
            logger.info(
                f"Recording status changed: {instance.id} -> {instance.status}",
                extra={
                    'event': 'recording_status_changed',
                    'recording_id': str(instance.id),
                    'status': instance.status,
                }
            )


@receiver(pre_delete, sender=LiveSession)
def log_session_delete(sender, instance, **kwargs):
    """Session silinmeden önce log tut."""
    logger.warning(
        f"LiveSession deleted: {instance.id} - {instance.title}",
        extra={
            'session_id': str(instance.id),
            'tenant_id': str(instance.tenant_id),
        }
    )


# Audit log entries için (opsiyonel)
# Bu bölüm logs/audit modülü ile entegre çalışabilir

def create_audit_entry(action: str, session, user=None, details: dict = None):
    """
    Audit log entry oluştur.
    
    Args:
        action: create, start, end, cancel, join, leave
        session: LiveSession instance
        user: İşlemi yapan kullanıcı
        details: Ek detaylar
    """
    try:
        # logs/audit modülü varsa kullan
        # from logs.audit.models import AuditLog
        # AuditLog.objects.create(...)
        
        logger.info(
            f"Audit: {action} on session {session.id}",
            extra={
                'audit_action': action,
                'session_id': str(session.id),
                'user_id': str(user.id) if user else None,
                'details': details or {},
            }
        )
    except Exception as e:
        logger.error(f"Failed to create audit entry: {e}")

