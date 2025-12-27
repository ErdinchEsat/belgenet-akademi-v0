"""
Live Class Provider Base
========================

Tüm provider adapter'ların implement edeceği abstract interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.live.models import LiveSession, LiveProviderConfig
    from backend.users.models import User


@dataclass
class RoomInfo:
    """Provider'dan dönen oda bilgisi."""
    room_id: str
    room_url: str
    password: Optional[str] = None
    moderator_url: Optional[str] = None
    dial_in: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JoinInfo:
    """Katılım için gerekli bilgiler."""
    join_url: str
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    role: str = 'participant'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParticipantInfo:
    """Katılımcı bilgisi."""
    user_id: str
    name: str
    role: str
    is_presenter: bool = False
    has_video: bool = False
    has_audio: bool = False
    is_muted: bool = False
    joined_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordingInfo:
    """Kayıt bilgisi."""
    recording_id: str
    url: str
    duration_seconds: int
    size_bytes: int
    format: str = 'mp4'
    status: str = 'ready'
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedEvent:
    """
    Provider-agnostic event.
    
    Tüm provider webhook'ları bu formata normalize edilir.
    """
    event_type: str  # session_started, session_ended, participant_joined, participant_left, recording_ready
    session_id: str
    timestamp: datetime
    payload: Dict[str, Any]
    provider: str
    raw_event: Dict[str, Any] = field(default_factory=dict)
    
    # Event types
    SESSION_STARTED = 'session_started'
    SESSION_ENDED = 'session_ended'
    PARTICIPANT_JOINED = 'participant_joined'
    PARTICIPANT_LEFT = 'participant_left'
    RECORDING_STARTED = 'recording_started'
    RECORDING_STOPPED = 'recording_stopped'
    RECORDING_READY = 'recording_ready'
    PARTICIPANT_MUTED = 'participant_muted'
    PARTICIPANT_UNMUTED = 'participant_unmuted'
    SCREEN_SHARE_STARTED = 'screen_share_started'
    SCREEN_SHARE_STOPPED = 'screen_share_stopped'


class LiveClassProvider(ABC):
    """
    Canlı ders sağlayıcı abstract interface.
    
    Tüm provider adapter'lar bu interface'i implement eder.
    Bu sayede Jitsi, BBB veya Zoom tak-çıkar şeklinde kullanılabilir.
    """
    
    def __init__(self, config: 'LiveProviderConfig'):
        """
        Provider'ı yapılandır.
        
        Args:
            config: Tenant bazlı provider konfigürasyonu
        """
        self.config = config
        self.provider_name = config.provider
    
    @abstractmethod
    def create_room(self, session: 'LiveSession') -> RoomInfo:
        """
        Yeni oda oluşturur.
        
        Args:
            session: Oda oluşturulacak canlı ders oturumu
            
        Returns:
            RoomInfo: Oluşturulan oda bilgisi
        """
        pass
    
    @abstractmethod
    def start_session(self, session: 'LiveSession') -> bool:
        """
        Oturumu başlatır.
        
        Bazı provider'larda (BBB gibi) oturum ayrıca başlatılmalıdır.
        
        Args:
            session: Başlatılacak oturum
            
        Returns:
            bool: Başarılı ise True
        """
        pass
    
    @abstractmethod
    def end_session(self, session: 'LiveSession') -> bool:
        """
        Oturumu sonlandırır.
        
        Args:
            session: Sonlandırılacak oturum
            
        Returns:
            bool: Başarılı ise True
        """
        pass
    
    @abstractmethod
    def generate_join_url(
        self, 
        session: 'LiveSession', 
        user: 'User', 
        role: str
    ) -> JoinInfo:
        """
        Katılım URL'i oluşturur.
        
        Args:
            session: Katılınacak oturum
            user: Katılacak kullanıcı
            role: Kullanıcı rolü (host, moderator, participant)
            
        Returns:
            JoinInfo: Katılım bilgileri (URL, token, expiry)
        """
        pass
    
    @abstractmethod
    def get_participants(self, session: 'LiveSession') -> List[ParticipantInfo]:
        """
        Aktif katılımcıları getirir.
        
        Args:
            session: Katılımcıları sorgulanacak oturum
            
        Returns:
            List[ParticipantInfo]: Aktif katılımcı listesi
        """
        pass
    
    @abstractmethod
    def start_recording(self, session: 'LiveSession') -> str:
        """
        Kaydı başlatır.
        
        Args:
            session: Kayıt başlatılacak oturum
            
        Returns:
            str: Provider tarafından verilen recording_id
        """
        pass
    
    @abstractmethod
    def stop_recording(self, session: 'LiveSession') -> bool:
        """
        Kaydı durdurur.
        
        Args:
            session: Kayıt durdurulacak oturum
            
        Returns:
            bool: Başarılı ise True
        """
        pass
    
    @abstractmethod
    def get_recordings(self, session: 'LiveSession') -> List[RecordingInfo]:
        """
        Oturum kayıtlarını getirir.
        
        Args:
            session: Kayıtları sorgulanacak oturum
            
        Returns:
            List[RecordingInfo]: Kayıt listesi
        """
        pass
    
    @abstractmethod
    def delete_room(self, session: 'LiveSession') -> bool:
        """
        Odayı siler.
        
        Args:
            session: Silinecek odanın oturumu
            
        Returns:
            bool: Başarılı ise True
        """
        pass
    
    @abstractmethod
    def handle_webhook(self, payload: dict) -> NormalizedEvent:
        """
        Webhook event'ini işler.
        
        Provider'a özgü webhook payload'ını normalize eder.
        
        Args:
            payload: Ham webhook payload
            
        Returns:
            NormalizedEvent: Normalize edilmiş event
        """
        pass
    
    def validate_webhook_signature(self, payload: dict, signature: str) -> bool:
        """
        Webhook imzasını doğrular.
        
        Args:
            payload: Webhook payload
            signature: Header'dan gelen imza
            
        Returns:
            bool: Geçerli ise True
        """
        # Varsayılan implementasyon - override edilmeli
        return True
    
    def health_check(self) -> bool:
        """
        Provider sağlık kontrolü.
        
        Returns:
            bool: Provider erişilebilir ise True
        """
        # Varsayılan implementasyon - override edilebilir
        return True
    
    def get_room_status(self, session: 'LiveSession') -> dict:
        """
        Oda durumunu getirir.
        
        Args:
            session: Sorgulanacak oturum
            
        Returns:
            dict: Oda durum bilgisi
        """
        participants = self.get_participants(session)
        return {
            'is_active': len(participants) > 0,
            'participant_count': len(participants),
            'participants': [
                {
                    'user_id': p.user_id,
                    'name': p.name,
                    'role': p.role,
                    'has_video': p.has_video,
                    'has_audio': p.has_audio,
                }
                for p in participants
            ]
        }

