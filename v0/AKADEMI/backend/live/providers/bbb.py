"""
BigBlueButton Provider
======================

BigBlueButton için adapter implementasyonu.
Checksum signature ile API authentication.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode
from xml.etree import ElementTree

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


class BBBProvider(LiveClassProvider):
    """
    BigBlueButton adapter.
    
    BBB API ile oda oluşturma, katılım, kayıt yönetimi.
    
    Gerekli config alanları:
        - bbb_server_url: https://bbb.example.com/bigbluebutton
        - bbb_shared_secret: <secret>
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.server_url = config.bbb_server_url.rstrip('/')
        self.secret = config.bbb_shared_secret
        
        if not all([self.server_url, self.secret]):
            raise ValueError("BBB config incomplete: server_url, secret required")
    
    def _get_checksum(self, call_name: str, query_string: str) -> str:
        """API checksum hesapla."""
        data = f"{call_name}{query_string}{self.secret}"
        return hashlib.sha1(data.encode()).hexdigest()
    
    def _make_api_call(self, call_name: str, params: dict = None) -> ElementTree.Element:
        """BBB API çağrısı yap."""
        params = params or {}
        query_string = urlencode(params)
        checksum = self._get_checksum(call_name, query_string)
        
        url = f"{self.server_url}/api/{call_name}?{query_string}&checksum={checksum}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return ElementTree.fromstring(response.content)
        except requests.RequestException as e:
            logger.error(f"BBB API call failed: {call_name} - {e}")
            raise
    
    def create_room(self, session) -> RoomInfo:
        """
        BBB'de meeting oluştur.
        """
        params = {
            'meetingID': session.room_id,
            'name': session.title,
            'attendeePW': 'attendee',  # Öğrenci şifresi
            'moderatorPW': 'moderator',  # Moderatör şifresi
            'welcome': session.description or f"Hoş geldiniz: {session.title}",
            'record': 'true' if session.recording_enabled else 'false',
            'autoStartRecording': 'true' if session.auto_recording else 'false',
            'allowStartStopRecording': 'true',
            'maxParticipants': session.max_participants,
            'muteOnStart': 'true' if session.students_start_muted else 'false',
            'webcamsOnlyForModerator': 'true' if session.students_video_off else 'false',
        }
        
        # Waiting room (guest policy)
        if session.waiting_room_enabled:
            params['guestPolicy'] = 'ASK_MODERATOR'
        else:
            params['guestPolicy'] = 'ALWAYS_ACCEPT'
        
        root = self._make_api_call('create', params)
        
        return_code = root.find('returncode')
        if return_code is None or return_code.text != 'SUCCESS':
            message = root.find('message')
            error_msg = message.text if message is not None else 'Unknown error'
            raise ValueError(f"BBB create failed: {error_msg}")
        
        logger.info(f"BBB meeting created: {session.room_id}")
        
        moderator_pw = root.find('moderatorPW')
        attendee_pw = root.find('attendeePW')
        
        return RoomInfo(
            room_id=session.room_id,
            room_url=f"{self.server_url.replace('/bigbluebutton', '')}/html5client/join",
            password=attendee_pw.text if attendee_pw is not None else 'attendee',
            moderator_url=None,  # Join URL ile oluşturulacak
            metadata={
                'provider': 'bbb',
                'moderator_password': moderator_pw.text if moderator_pw is not None else 'moderator',
            }
        )
    
    def start_session(self, session) -> bool:
        """
        BBB'de oturum başlat.
        
        BBB'de meeting create ile başlar, ayrıca start gerekmez.
        """
        logger.info(f"BBB session started: {session.room_id}")
        return True
    
    def end_session(self, session) -> bool:
        """
        BBB'de oturumu sonlandır.
        """
        params = {
            'meetingID': session.room_id,
            'password': 'moderator',  # Moderator password
        }
        
        try:
            root = self._make_api_call('end', params)
            return_code = root.find('returncode')
            success = return_code is not None and return_code.text == 'SUCCESS'
            
            if success:
                logger.info(f"BBB session ended: {session.room_id}")
            
            return success
        except Exception as e:
            logger.error(f"BBB end session failed: {e}")
            return False
    
    def generate_join_url(self, session, user, role: str) -> JoinInfo:
        """
        BBB join URL oluştur.
        """
        is_moderator = role in ['host', 'moderator']
        password = 'moderator' if is_moderator else 'attendee'
        
        params = {
            'meetingID': session.room_id,
            'fullName': user.full_name,
            'password': password,
            'userID': str(user.id),
            'avatarURL': user.get_avatar_url(),
        }
        
        # Guest için
        if not is_moderator:
            params['guest'] = 'true'
        
        query_string = urlencode(params)
        checksum = self._get_checksum('join', query_string)
        
        join_url = f"{self.server_url}/api/join?{query_string}&checksum={checksum}"
        
        logger.debug(f"Generated BBB join URL for user {user.id}, role: {role}")
        
        return JoinInfo(
            join_url=join_url,
            token=None,  # BBB URL-based auth kullanır
            expires_at=None,  # URL expiry yok
            role=role,
            metadata={
                'moderator': is_moderator,
            }
        )
    
    def get_participants(self, session) -> List[ParticipantInfo]:
        """
        BBB'den aktif katılımcıları getir.
        """
        params = {'meetingID': session.room_id}
        
        try:
            root = self._make_api_call('getMeetingInfo', params)
            
            return_code = root.find('returncode')
            if return_code is None or return_code.text != 'SUCCESS':
                return []
            
            participants = []
            attendees = root.find('attendees')
            
            if attendees is not None:
                for attendee in attendees.findall('attendee'):
                    user_id = attendee.find('userID')
                    full_name = attendee.find('fullName')
                    role = attendee.find('role')
                    has_video = attendee.find('hasVideo')
                    has_audio = attendee.find('hasJoinedVoice')
                    is_presenter = attendee.find('isPresenter')
                    
                    participants.append(ParticipantInfo(
                        user_id=user_id.text if user_id is not None else '',
                        name=full_name.text if full_name is not None else 'Unknown',
                        role='moderator' if role is not None and role.text == 'MODERATOR' else 'participant',
                        is_presenter=is_presenter is not None and is_presenter.text == 'true',
                        has_video=has_video is not None and has_video.text == 'true',
                        has_audio=has_audio is not None and has_audio.text == 'true',
                    ))
            
            return participants
            
        except Exception as e:
            logger.error(f"BBB get_participants failed: {e}")
            return []
    
    def start_recording(self, session) -> str:
        """
        BBB'de kayıt başlat.
        
        BBB'de kayıt autoStartRecording ile veya moderatör tarafından başlatılır.
        """
        recording_id = f"bbb-rec-{session.room_id}-{int(time.time())}"
        logger.info(f"BBB recording initiated: {recording_id}")
        return recording_id
    
    def stop_recording(self, session) -> bool:
        """
        BBB'de kaydı durdur.
        """
        logger.info(f"BBB recording stopped for session: {session.room_id}")
        return True
    
    def get_recordings(self, session) -> List[RecordingInfo]:
        """
        BBB'den kayıtları getir.
        """
        params = {'meetingID': session.room_id}
        
        try:
            root = self._make_api_call('getRecordings', params)
            
            return_code = root.find('returncode')
            if return_code is None or return_code.text != 'SUCCESS':
                return []
            
            recordings = []
            recordings_elem = root.find('recordings')
            
            if recordings_elem is not None:
                for recording in recordings_elem.findall('recording'):
                    record_id = recording.find('recordID')
                    playback = recording.find('playback')
                    
                    if playback is not None:
                        format_elem = playback.find('format')
                        if format_elem is not None:
                            url_elem = format_elem.find('url')
                            length_elem = format_elem.find('length')
                            
                            recordings.append(RecordingInfo(
                                recording_id=record_id.text if record_id is not None else '',
                                url=url_elem.text if url_elem is not None else '',
                                duration_seconds=int(length_elem.text) * 60 if length_elem is not None else 0,
                                size_bytes=0,  # BBB API'de yok
                                format='mp4',
                                status='ready',
                            ))
            
            return recordings
            
        except Exception as e:
            logger.error(f"BBB get_recordings failed: {e}")
            return []
    
    def delete_room(self, session) -> bool:
        """
        BBB'de odayı sil.
        
        BBB'de oda ayrıca silinmez, session end ile temizlenir.
        """
        return self.end_session(session)
    
    def handle_webhook(self, payload: dict) -> NormalizedEvent:
        """
        BBB webhook event'ini işle.
        
        BBB webhooks modülü ile gönderilen event'ler.
        """
        event_type = payload.get('event', {}).get('eventType', 'unknown')
        meeting_id = payload.get('event', {}).get('attributes', {}).get('meeting', {}).get('externalMeetingId', '')
        timestamp_str = payload.get('event', {}).get('timestamp', '')
        
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.utcnow()
        
        # Normalize event type
        normalized_type = self._normalize_event_type(event_type)
        
        # Extract user info
        attributes = payload.get('event', {}).get('attributes', {})
        user = attributes.get('user', {})
        
        normalized_payload = {
            'room_id': meeting_id,
            'participant_id': user.get('externalUserId'),
            'participant_name': user.get('name'),
        }
        
        return NormalizedEvent(
            event_type=normalized_type,
            session_id=meeting_id,
            timestamp=timestamp,
            payload=normalized_payload,
            provider='bbb',
            raw_event=payload,
        )
    
    def _normalize_event_type(self, bbb_event: str) -> str:
        """BBB event tipini normalize et."""
        mapping = {
            'user-joined': NormalizedEvent.PARTICIPANT_JOINED,
            'user-left': NormalizedEvent.PARTICIPANT_LEFT,
            'meeting-started': NormalizedEvent.SESSION_STARTED,
            'meeting-ended': NormalizedEvent.SESSION_ENDED,
            'rap-archive-started': NormalizedEvent.RECORDING_STARTED,
            'rap-archive-ended': NormalizedEvent.RECORDING_STOPPED,
            'rap-publish-ended': NormalizedEvent.RECORDING_READY,
            'user-audio-muted': NormalizedEvent.PARTICIPANT_MUTED,
            'user-audio-unmuted': NormalizedEvent.PARTICIPANT_UNMUTED,
        }
        return mapping.get(bbb_event, bbb_event)
    
    def health_check(self) -> bool:
        """
        BBB server sağlık kontrolü.
        """
        try:
            root = self._make_api_call('getMeetings', {})
            return_code = root.find('returncode')
            return return_code is not None and return_code.text == 'SUCCESS'
        except Exception as e:
            logger.error(f"BBB health check failed: {e}")
            return False

