"""
Webhook Service
===============

Provider webhook işleme servisi.
"""

import logging
from typing import Dict, Any

from django.db import transaction

from ..models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionRecording,
)
from ..providers import get_provider_for_config
from ..providers.base import NormalizedEvent

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook işleme servisi.
    """
    
    @classmethod
    def handle_webhook(
        cls,
        provider: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Webhook event'ini işle.
        
        Args:
            provider: jitsi, bbb, zoom
            payload: Webhook payload
            headers: HTTP headers
            
        Returns:
            dict: İşleme sonucu
        """
        from ..models import LiveProviderConfig
        
        # Room ID'yi payload'dan çıkar
        room_id = cls._extract_room_id(provider, payload)
        
        if not room_id:
            raise ValueError("Room ID not found in webhook payload")
        
        # Session bul
        try:
            session = LiveSession.objects.get(room_id=room_id)
        except LiveSession.DoesNotExist:
            logger.warning(f"Session not found for room: {room_id}")
            raise ValueError(f"Session not found: {room_id}")
        
        # Provider config al
        config = LiveProviderConfig.objects.filter(
            tenant=session.tenant,
            provider=provider,
            is_active=True
        ).first()
        
        if not config:
            raise ValueError(f"No active {provider} config for tenant")
        
        # Provider instance al
        provider_instance = get_provider_for_config(config)
        
        # Signature doğrula
        signature = headers.get('X-Webhook-Signature', headers.get('x-webhook-signature', ''))
        if signature and not provider_instance.validate_webhook_signature(payload, signature):
            raise ValueError("Invalid webhook signature")
        
        # Event'i normalize et
        event = provider_instance.handle_webhook(payload)
        
        # Event'i işle
        result = cls._process_event(session, event)
        
        return {
            'event_type': event.event_type,
            'session_id': str(session.id),
            'processed': True,
            **result
        }
    
    @classmethod
    def _extract_room_id(cls, provider: str, payload: Dict[str, Any]) -> str:
        """Payload'dan room ID çıkar."""
        if provider == 'jitsi':
            return payload.get('room', payload.get('roomName', ''))
        elif provider == 'bbb':
            return payload.get('event', {}).get('attributes', {}).get('meeting', {}).get('externalMeetingId', '')
        elif provider == 'zoom':
            return payload.get('payload', {}).get('object', {}).get('id', '')
        return ''
    
    @classmethod
    @transaction.atomic
    def _process_event(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Event'i işle."""
        result = {}
        
        if event.event_type == NormalizedEvent.SESSION_STARTED:
            result = cls._handle_session_started(session, event)
        
        elif event.event_type == NormalizedEvent.SESSION_ENDED:
            result = cls._handle_session_ended(session, event)
        
        elif event.event_type == NormalizedEvent.PARTICIPANT_JOINED:
            result = cls._handle_participant_joined(session, event)
        
        elif event.event_type == NormalizedEvent.PARTICIPANT_LEFT:
            result = cls._handle_participant_left(session, event)
        
        elif event.event_type == NormalizedEvent.RECORDING_READY:
            result = cls._handle_recording_ready(session, event)
        
        elif event.event_type == NormalizedEvent.RECORDING_STARTED:
            result = cls._handle_recording_started(session, event)
        
        elif event.event_type == NormalizedEvent.RECORDING_STOPPED:
            result = cls._handle_recording_stopped(session, event)
        
        else:
            logger.info(f"Unhandled event type: {event.event_type}")
        
        return result
    
    @classmethod
    def _handle_session_started(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Session başladı event'i."""
        if session.status != LiveSession.Status.LIVE:
            session.status = LiveSession.Status.LIVE
            session.actual_start = event.timestamp
            session.save(update_fields=['status', 'actual_start'])
            logger.info(f"Session started via webhook: {session.id}")
        
        return {'action': 'session_started'}
    
    @classmethod
    def _handle_session_ended(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Session bitti event'i."""
        if session.status == LiveSession.Status.LIVE:
            session.status = LiveSession.Status.ENDED
            session.actual_end = event.timestamp
            if session.actual_start:
                session.total_duration_minutes = int(
                    (session.actual_end - session.actual_start).total_seconds() / 60
                )
            session.save()
            
            # Attendance hesaplama task'ı tetikle
            from ..tasks import calculate_attendance_task
            calculate_attendance_task.delay(str(session.id))
            
            logger.info(f"Session ended via webhook: {session.id}")
        
        return {'action': 'session_ended'}
    
    @classmethod
    def _handle_participant_joined(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Katılımcı katıldı event'i."""
        user_id = event.payload.get('participant_id')
        
        if not user_id:
            # Webhook'tan gelen katılımcı için kayıt oluşturamayız
            # Çünkü user ID'yi bilmiyoruz
            logger.debug("Participant joined but no user_id in webhook")
            return {'action': 'participant_joined', 'user_id': None}
        
        # Session katılımcı sayısını güncelle
        session.participant_count = session.participants.filter(is_active=True).count() + 1
        session.peak_participants = max(session.peak_participants, session.participant_count)
        session.save(update_fields=['participant_count', 'peak_participants'])
        
        return {'action': 'participant_joined', 'user_id': user_id}
    
    @classmethod
    def _handle_participant_left(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Katılımcı ayrıldı event'i."""
        user_id = event.payload.get('participant_id')
        
        if user_id:
            # Aktif participant bul ve güncelle
            from backend.users.models import User
            try:
                user = User.objects.get(id=user_id)
                participant = LiveSessionParticipant.objects.filter(
                    session=session,
                    user=user,
                    is_active=True
                ).order_by('-joined_at').first()
                
                if participant:
                    participant.left_at = event.timestamp
                    participant.is_active = False
                    if participant.joined_at:
                        participant.duration_seconds = int(
                            (event.timestamp - participant.joined_at).total_seconds()
                        )
                    participant.save()
            except User.DoesNotExist:
                pass
        
        # Session katılımcı sayısını güncelle
        session.participant_count = session.participants.filter(is_active=True).count()
        session.save(update_fields=['participant_count'])
        
        return {'action': 'participant_left', 'user_id': user_id}
    
    @classmethod
    def _handle_recording_ready(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Kayıt hazır event'i."""
        from .recording_service import RecordingService
        
        recording_id = event.payload.get('recording_id')
        recording_url = event.payload.get('recording_url', '')
        
        if not recording_id:
            logger.warning("Recording ready but no recording_id")
            return {'action': 'recording_ready', 'recording_id': None}
        
        # Kayıt oluştur
        recording = RecordingService.create_recording(
            session=session,
            provider_recording_id=recording_id,
            provider_url=recording_url
        )
        
        # Processing task tetikle
        from ..tasks import process_recording_task
        process_recording_task.delay(str(recording.id))
        
        logger.info(f"Recording ready: {recording.id}")
        
        return {'action': 'recording_ready', 'recording_id': str(recording.id)}
    
    @classmethod
    def _handle_recording_started(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Kayıt başladı event'i."""
        logger.info(f"Recording started for session: {session.id}")
        return {'action': 'recording_started'}
    
    @classmethod
    def _handle_recording_stopped(cls, session: LiveSession, event: NormalizedEvent) -> Dict[str, Any]:
        """Kayıt durdu event'i."""
        logger.info(f"Recording stopped for session: {session.id}")
        return {'action': 'recording_stopped'}

