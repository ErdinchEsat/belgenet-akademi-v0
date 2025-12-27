"""
Jitsi Meet Provider
===================

Jitsi Meet için adapter implementasyonu.
JWT tabanlı authentication ile self-hosted Jitsi'yi destekler.
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin

import jwt
import requests

from .base import (
    LiveClassProvider,
    RoomInfo,
    JoinInfo,
    ParticipantInfo,
    RecordingInfo,
    NormalizedEvent,
)

logger = logging.getLogger(__name__)


class JitsiProvider(LiveClassProvider):
    """
    Jitsi Meet adapter.
    
    JWT ile authentication, moderator claims ile rol yönetimi.
    Self-hosted Jitsi Meet için tasarlanmıştır.
    
    Gerekli config alanları:
        - jitsi_domain: meet.example.com
        - jitsi_app_id: myapp
        - jitsi_jwt_secret: <secret>
    """
    
    # Token geçerlilik süresi (saniye)
    TOKEN_EXPIRY = 300  # 5 dakika
    
    def __init__(self, config):
        super().__init__(config)
        self.domain = config.jitsi_domain
        self.app_id = config.jitsi_app_id
        self.secret = config.jitsi_jwt_secret
        
        if not all([self.domain, self.app_id, self.secret]):
            raise ValueError("Jitsi config incomplete: domain, app_id, secret required")
    
    def create_room(self, session) -> RoomInfo:
        """
        Jitsi'de oda oluştur.
        
        Jitsi'de oda önceden oluşturulmaz, ilk katılan kişi odayı oluşturur.
        Bu metod sadece URL ve metadata döner.
        """
        room_name = session.room_id
        room_url = f"https://{self.domain}/{room_name}"
        
        logger.info(f"Jitsi room prepared: {room_name}")
        
        return RoomInfo(
            room_id=room_name,
            room_url=room_url,
            metadata={
                'provider': 'jitsi',
                'domain': self.domain,
            }
        )
    
    def start_session(self, session) -> bool:
        """
        Jitsi'de oturum başlat.
        
        Jitsi'de explicit start gerekmez, bu metod sadece log tutar.
        """
        logger.info(f"Jitsi session started: {session.room_id}")
        return True
    
    def end_session(self, session) -> bool:
        """
        Jitsi'de oturumu sonlandır.
        
        Jitsi'de explicit end gerekmez. Tüm katılımcılar ayrıldığında oda kapanır.
        Prosody üzerinden oda kapatma yapılabilir (opsiyonel).
        """
        logger.info(f"Jitsi session ended: {session.room_id}")
        return True
    
    def generate_join_url(self, session, user, role: str) -> JoinInfo:
        """
        JWT token ile join URL oluştur.
        
        JWT payload:
        - aud: jitsi
        - iss: app_id
        - sub: domain
        - room: room_id
        - exp: expiry timestamp
        - context: user info, features
        - moderator: true/false
        """
        now = int(time.time())
        exp = now + self.TOKEN_EXPIRY
        
        # Moderator claim
        is_moderator = role in ['host', 'moderator']
        
        # Feature claims based on role
        features = {
            'recording': is_moderator,
            'livestreaming': False,
            'transcription': False,
            'outbound-call': False,
        }
        
        # Screen share permission
        if role == 'participant' and session.students_can_share_screen:
            features['screen-sharing'] = True
        elif is_moderator:
            features['screen-sharing'] = True
        
        payload = {
            'aud': 'jitsi',
            'iss': self.app_id,
            'sub': self.domain,
            'room': session.room_id,
            'exp': exp,
            'nbf': now - 10,  # 10 saniye tolerans
            'iat': now,
            'context': {
                'user': {
                    'id': str(user.id),
                    'name': user.full_name,
                    'email': user.email,
                    'avatar': user.get_avatar_url(),
                },
                'features': features,
            },
            'moderator': is_moderator,
        }
        
        # Lobby bypass for moderators
        if is_moderator and session.waiting_room_enabled:
            payload['context']['user']['lobby_bypass'] = True
        
        token = jwt.encode(payload, self.secret, algorithm='HS256')
        join_url = f"https://{self.domain}/{session.room_id}?jwt={token}"
        
        # Config parameters
        config_params = []
        
        # Mute on start
        if session.students_start_muted and not is_moderator:
            config_params.append('config.startWithAudioMuted=true')
        
        # Video off on start
        if session.students_video_off and not is_moderator:
            config_params.append('config.startWithVideoMuted=true')
        
        # Add config params to URL
        if config_params:
            join_url += '#' + '&'.join(config_params)
        
        logger.debug(f"Generated Jitsi join URL for user {user.id}, role: {role}")
        
        return JoinInfo(
            join_url=join_url,
            token=token,
            expires_at=datetime.fromtimestamp(exp),
            role=role,
            metadata={
                'moderator': is_moderator,
                'domain': self.domain,
            }
        )
    
    def get_participants(self, session) -> List[ParticipantInfo]:
        """
        Aktif katılımcıları getir.
        
        Jitsi'de participant bilgisi genelde webhook/SRTP ile gelir.
        Prosody üzerinden XMPP API ile sorgulanabilir (opsiyonel).
        """
        # Prosody REST API veya SRTP ile implement edilebilir
        # Şimdilik boş liste dön
        logger.warning("Jitsi get_participants not fully implemented - using webhooks instead")
        return []
    
    def start_recording(self, session) -> str:
        """
        Kaydı başlat.
        
        Jibri kullanılıyorsa external script veya API ile başlatılabilir.
        """
        recording_id = f"jitsi-rec-{session.room_id}-{int(time.time())}"
        logger.info(f"Jitsi recording started: {recording_id}")
        
        # Jibri API çağrısı yapılabilir
        # POST https://jibri.example.com/jibri/api/v1.0/startService
        
        return recording_id
    
    def stop_recording(self, session) -> bool:
        """
        Kaydı durdur.
        """
        logger.info(f"Jitsi recording stopped for session: {session.room_id}")
        
        # Jibri API çağrısı
        # POST https://jibri.example.com/jibri/api/v1.0/stopService
        
        return True
    
    def get_recordings(self, session) -> List[RecordingInfo]:
        """
        Oturum kayıtlarını getir.
        
        Jibri kayıtları genelde dosya sisteminde saklanır.
        Custom recording server kullanılabilir.
        """
        # Kayıtlar genelde Jibri tarafından bir dizine yazılır
        # Bu dizin taranarak kayıtlar listelenebilir
        logger.warning("Jitsi get_recordings not fully implemented")
        return []
    
    def delete_room(self, session) -> bool:
        """
        Odayı sil.
        
        Jitsi'de oda kalıcı değildir, herkes ayrılınca silinir.
        """
        logger.info(f"Jitsi room cleanup: {session.room_id}")
        return True
    
    def handle_webhook(self, payload: dict) -> NormalizedEvent:
        """
        Jitsi webhook event'ini işle.
        
        Jitsi webhook'ları genelde Prosody modülü ile gönderilir.
        
        Event tipleri:
        - participant_joined
        - participant_left
        - session_started (room_created)
        - session_ended (room_destroyed)
        - recording_started
        - recording_stopped
        """
        event_type = payload.get('event', payload.get('type', 'unknown'))
        room = payload.get('room', payload.get('roomName', ''))
        timestamp = payload.get('timestamp', time.time())
        
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Normalize event type
        normalized_type = self._normalize_event_type(event_type)
        
        # Extract participant info if present
        participant = payload.get('participant', {})
        
        normalized_payload = {
            'room_id': room,
            'participant_id': participant.get('id'),
            'participant_name': participant.get('name'),
            'participant_email': participant.get('email'),
        }
        
        # Add recording info if present
        if 'recording' in payload:
            normalized_payload['recording_id'] = payload['recording'].get('id')
            normalized_payload['recording_url'] = payload['recording'].get('url')
        
        return NormalizedEvent(
            event_type=normalized_type,
            session_id=room,
            timestamp=timestamp,
            payload=normalized_payload,
            provider='jitsi',
            raw_event=payload,
        )
    
    def _normalize_event_type(self, jitsi_event: str) -> str:
        """Jitsi event tipini normalize et."""
        mapping = {
            'participant_joined': NormalizedEvent.PARTICIPANT_JOINED,
            'participant_left': NormalizedEvent.PARTICIPANT_LEFT,
            'room_created': NormalizedEvent.SESSION_STARTED,
            'room_destroyed': NormalizedEvent.SESSION_ENDED,
            'session_started': NormalizedEvent.SESSION_STARTED,
            'session_ended': NormalizedEvent.SESSION_ENDED,
            'recording_started': NormalizedEvent.RECORDING_STARTED,
            'recording_stopped': NormalizedEvent.RECORDING_STOPPED,
            'recording_ready': NormalizedEvent.RECORDING_READY,
            'muted': NormalizedEvent.PARTICIPANT_MUTED,
            'unmuted': NormalizedEvent.PARTICIPANT_UNMUTED,
        }
        return mapping.get(jitsi_event, jitsi_event)
    
    def validate_webhook_signature(self, payload: dict, signature: str) -> bool:
        """
        Webhook imzasını doğrula.
        
        HMAC-SHA256 ile imza doğrulama.
        """
        if not signature:
            return False
        
        import json
        payload_str = json.dumps(payload, sort_keys=True)
        expected = hmac.new(
            self.secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def health_check(self) -> bool:
        """
        Jitsi server sağlık kontrolü.
        
        Jitsi health endpoint'ini kontrol eder.
        """
        try:
            response = requests.get(
                f"https://{self.domain}/http-bind",
                timeout=5
            )
            return response.status_code < 500
        except requests.RequestException as e:
            logger.error(f"Jitsi health check failed: {e}")
            return False

