# B6 – Canlı Ders (Live Class) Modülü: Uçtan Uca ToDo List

> **Son Güncelleme:** 27 Aralık 2024
> **Hedef Mimari:** Provider-agnostic adapter pattern (Jitsi → BBB → Zoom)
> **MVP Provider:** Jitsi Meet (self-hosted)

---

## Genel Bakış

Bu ToDo listesi, EduTech/Akademi LMS içinde "Canlı Ders (Online Meeting/Classroom)" modülünü kurumsal ölçekte, düşük maliyet ve sürdürülebilir işletim hedefiyle uçtan uca ele alır.

### Öncelik Seviyeleri
- **P0**: MVP (v0.1) - İlk sürümde olması zorunlu
- **P1**: v0.2-0.3 - Kısa vadeli hedef
- **P2**: İleri vizyon - Roadmap backlog

---

## 1) Ürün Kapsamı ve Kullanıcı Akışları

### 1.1 Canlı Ders Türleri Tanımı
- [ ] **Planlı Ders (Scheduled Class)**
  - Açıklama: Takvimde önceden planlanan, kursa bağlı sınıf dersleri. Start/end zamanı belirlenir.
  - DoD: `LiveSession.type = 'SCHEDULED'` kaydedilebilir; takvimde görünür; hatırlatıcı gönderilir.
  - Kod/Path: `backend/live/models.py::LiveSession.Type.SCHEDULED`
  - Öncelik: P0

- [ ] **Anlık Toplantı (Ad-hoc Meeting)**
  - Açıklama: Eğitmenin anında başlattığı toplantı. Plansız, hızlı erişim.
  - DoD: "Şimdi Başlat" butonu çalışır; 30 saniye içinde oda açılır.
  - Kod/Path: `backend/live/models.py::LiveSession.Type.ADHOC`
  - Öncelik: P0

- [ ] **Webinar (One-to-Many)**
  - Açıklama: Tek yönlü yayın ağırlıklı. Katılımcılar varsayılan olarak sessiz başlar.
  - DoD: Webinar modunda sadece moderatörler konuşabilir; Q&A paneli aktif.
  - Kod/Path: `backend/live/models.py::LiveSession.Type.WEBINAR`
  - Öncelik: P1

### 1.2 Rol Matrisi
- [ ] **Rol Tanımları ve Yetkileri**
  - Açıklama: Eğitmen (Host), Öğrenci (Participant), Moderatör (Co-host), Admin (Super) yetki matrisini tanımla.
  - DoD: Her rol için can_start, can_mute_others, can_share_screen, can_record, can_kick gibi permission'lar tanımlı.
  - Kod/Path: `backend/live/permissions.py::LiveSessionRolePermissions`
  - Öncelik: P0

```
| Yetki              | Eğitmen | Öğrenci | Moderatör | Admin |
|--------------------|---------|---------|-----------|-------|
| start_session      | ✓       | ✗       | ✓         | ✓     |
| end_session        | ✓       | ✗       | ✓         | ✓     |
| join_session       | ✓       | ✓       | ✓         | ✓     |
| share_screen       | ✓       | △       | ✓         | ✓     |
| mute_others        | ✓       | ✗       | ✓         | ✓     |
| kick_participant   | ✓       | ✗       | ✓         | ✓     |
| start_recording    | ✓       | ✗       | ✓         | ✓     |
| use_whiteboard     | ✓       | △       | ✓         | ✓     |
| send_chat          | ✓       | ✓       | ✓         | ✓     |

△ = Policy'ye bağlı (tenant/session ayarı)
```

### 1.3 Lobby/Waiting Room Politikası
- [ ] **Waiting Room Mekanizması**
  - Açıklama: Öğrenciler lobby'de bekler, eğitmen gelince otomatik kabul veya manuel onay.
  - DoD: `LiveSessionPolicy.lobby_enabled` flag; webhook ile "participant_joined_lobby" yakalanır.
  - Kod/Path: `backend/live/models.py::LiveSessionPolicy.lobby_enabled`
  - Öncelik: P1

### 1.4 Tenant Bazlı Sağlayıcı Seçimi
- [ ] **Feature Flag ve Konfigürasyon**
  - Açıklama: Her tenant için Jitsi/BBB/Zoom seçilebilir. Default: Jitsi.
  - DoD: Admin panelinden sağlayıcı seçilebilir; session oluştururken doğru adapter kullanılır.
  - Kod/Path: `backend/live/models.py::LiveProviderConfig`
  - Öncelik: P0

---

## 2) Domain Modeli ve Veritabanı Şeması

### 2.1 LiveSession Modeli
- [ ] **Ana Canlı Ders Modeli**
  - Açıklama: Canlı ders oturumu. Course/Content ile ilişkili. Provider-agnostic room_id tutar.
  - DoD: Migration çalışır; tüm alanlar için null/default değerler mantıklı; index'ler oluşturulmuş.
  - Kod/Path: `backend/live/models.py::LiveSession`
  - Öncelik: P0

```python
class LiveSession(TenantAwareModel):
    """
    Canlı ders oturumu.
    """
    class Type(models.TextChoices):
        SCHEDULED = 'scheduled', _('Planlı Ders')
        ADHOC = 'adhoc', _('Anlık Toplantı')
        WEBINAR = 'webinar', _('Webinar')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Taslak')
        SCHEDULED = 'scheduled', _('Planlandı')
        LIVE = 'live', _('Yayında')
        ENDED = 'ended', _('Bitti')
        CANCELLED = 'cancelled', _('İptal')

    # İlişkiler
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='live_sessions')
    content = models.ForeignKey('courses.CourseContent', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Temel bilgiler
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SCHEDULED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Zamanlama
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Provider bilgileri
    provider = models.CharField(max_length=20, choices=[('jitsi', 'Jitsi'), ('bbb', 'BBB'), ('zoom', 'Zoom')])
    room_id = models.CharField(max_length=100, unique=True)
    room_url = models.URLField(blank=True)
    room_password = models.CharField(max_length=50, blank=True)
    
    # Ayarlar
    max_participants = models.PositiveIntegerField(default=100)
    recording_enabled = models.BooleanField(default=True)
    auto_recording = models.BooleanField(default=False)
    waiting_room_enabled = models.BooleanField(default=True)
    
    # İstatistikler (cache)
    participant_count = models.PositiveIntegerField(default=0)
    peak_participants = models.PositiveIntegerField(default=0)
    total_duration_minutes = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = _('Canlı Ders')
        verbose_name_plural = _('Canlı Dersler')
        ordering = ['-scheduled_start']
        indexes = [
            models.Index(fields=['status', 'scheduled_start']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['room_id']),
        ]
```

### 2.2 LiveSessionParticipant Modeli
- [ ] **Katılımcı Kaydı**
  - Açıklama: Her katılımın join/leave zamanları, toplam süre, cihaz/IP bilgisi.
  - DoD: Bir kullanıcının aynı session'a birden fazla join/leave kaydı tutulabilir.
  - Kod/Path: `backend/live/models.py::LiveSessionParticipant`
  - Öncelik: P0

```python
class LiveSessionParticipant(models.Model):
    """
    Oturum katılımcısı - her join/leave bir kayıt.
    """
    class Role(models.TextChoices):
        HOST = 'host', _('Eğitmen')
        MODERATOR = 'moderator', _('Moderatör')
        PARTICIPANT = 'participant', _('Öğrenci')

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    
    # Zaman bilgileri
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    
    # Cihaz/Konum
    device_type = models.CharField(max_length=50, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=100, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)  # KVKK: IP hash
    
    # Durum
    is_active = models.BooleanField(default=True)
    kicked = models.BooleanField(default=False)
    kick_reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = _('Oturum Katılımcısı')
        indexes = [
            models.Index(fields=['session', 'user']),
            models.Index(fields=['session', 'is_active']),
        ]
```

### 2.3 LiveSessionAttendanceSummary Modeli
- [ ] **Katılım Özeti**
  - Açıklama: Kullanıcı başına tek satır. Toplam süre, katıldı mı, geç mi geldi.
  - DoD: Session kapandığında Celery task ile hesaplanır.
  - Kod/Path: `backend/live/models.py::LiveSessionAttendanceSummary`
  - Öncelik: P0

```python
class LiveSessionAttendanceSummary(models.Model):
    """
    Kullanıcı bazlı katılım özeti (session başına tek kayıt).
    """
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='attendance_summaries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Süre hesabı
    total_duration_seconds = models.PositiveIntegerField(default=0)
    join_count = models.PositiveIntegerField(default=1)
    first_join = models.DateTimeField()
    last_leave = models.DateTimeField(null=True, blank=True)
    
    # Katılım durumu
    attended = models.BooleanField(default=False)
    attendance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_join = models.BooleanField(default=False)
    early_leave = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Katılım Özeti')
        unique_together = ['session', 'user']
```

### 2.4 LiveSessionRecording Modeli
- [ ] **Kayıt Dosyası**
  - Açıklama: Provider'dan gelen kayıt. Transcoding durumu, storage URL, erişim kontrolü.
  - DoD: Recording tamamlandığında webhook ile yakalanır, S3'e taşınır, thumbnail oluşturulur.
  - Kod/Path: `backend/live/models.py::LiveSessionRecording`
  - Öncelik: P0

```python
class LiveSessionRecording(TenantAwareModel):
    """
    Canlı ders kaydı.
    """
    class Status(models.TextChoices):
        PROCESSING = 'processing', _('İşleniyor')
        READY = 'ready', _('Hazır')
        PUBLISHED = 'published', _('Yayında')
        FAILED = 'failed', _('Hata')
        DELETED = 'deleted', _('Silindi')

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='recordings')
    
    # Provider bilgileri
    provider_recording_id = models.CharField(max_length=200)
    provider_url = models.URLField(blank=True)
    
    # Storage
    file = models.ForeignKey('storage.FileUpload', on_delete=models.SET_NULL, null=True, blank=True)
    storage_url = models.URLField(blank=True)
    storage_path = models.CharField(max_length=500, blank=True)
    
    # Metadata
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size_bytes = models.BigIntegerField(default=0)
    format = models.CharField(max_length=20, default='mp4')
    resolution = models.CharField(max_length=20, blank=True)  # 1080p, 720p
    
    # Thumbnail
    thumbnail_url = models.URLField(blank=True)
    
    # Transkript
    transcript_status = models.CharField(max_length=20, default='none')  # none, processing, ready
    transcript_url = models.URLField(blank=True)
    
    # Yayın durumu
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    is_public = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Retention
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Ders Kaydı')
        indexes = [
            models.Index(fields=['session', 'status']),
        ]
```

### 2.5 LiveSessionArtifacts Modeli
- [ ] **Oturum Çıktıları**
  - Açıklama: Whiteboard export, chat log, paylaşılan dosyalar.
  - DoD: Session kapandığında otomatik toplanır.
  - Kod/Path: `backend/live/models.py::LiveSessionArtifacts`
  - Öncelik: P1

```python
class LiveSessionArtifact(TenantAwareModel):
    """
    Oturum çıktıları (whiteboard, chat, dosyalar).
    """
    class Type(models.TextChoices):
        WHITEBOARD = 'whiteboard', _('Whiteboard')
        CHAT = 'chat', _('Sohbet')
        FILE = 'file', _('Dosya')
        POLL = 'poll', _('Anket')
        NOTES = 'notes', _('Notlar')

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='artifacts')
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=200)
    
    # Dosya
    file = models.ForeignKey('storage.FileUpload', on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField(blank=True)  # JSON veya text (chat için)
    
    # Meta
    metadata = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = _('Oturum Çıktısı')
```

### 2.6 LiveSessionPolicy Modeli
- [ ] **Politika Ayarları**
  - Açıklama: Tenant/course bazlı kayıt zorunluluğu, katılım eşiği, toleranslar.
  - DoD: Policy hiyerarşisi: Session > Course > Tenant default.
  - Kod/Path: `backend/live/models.py::LiveSessionPolicy`
  - Öncelik: P1

```python
class LiveSessionPolicy(models.Model):
    """
    Canlı ders politikaları.
    
    Öncelik: session_level > course_level > tenant_level
    """
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    session = models.OneToOneField(LiveSession, on_delete=models.CASCADE, null=True, blank=True)
    
    # Kayıt politikası
    recording_required = models.BooleanField(default=True)
    auto_recording = models.BooleanField(default=False)
    recording_retention_days = models.PositiveIntegerField(default=90)
    
    # Katılım politikası
    attendance_threshold_percent = models.PositiveIntegerField(default=70)
    minimum_duration_minutes = models.PositiveIntegerField(default=5)
    late_join_tolerance_minutes = models.PositiveIntegerField(default=10)
    early_leave_tolerance_minutes = models.PositiveIntegerField(default=10)
    
    # Güvenlik
    lobby_enabled = models.BooleanField(default=True)
    require_authentication = models.BooleanField(default=True)
    allow_guests = models.BooleanField(default=False)
    
    # Öğrenci izinleri
    students_can_share_screen = models.BooleanField(default=False)
    students_can_use_whiteboard = models.BooleanField(default=True)
    students_can_unmute_self = models.BooleanField(default=True)
    students_start_muted = models.BooleanField(default=True)
    students_video_off = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Canlı Ders Politikası')
```

### 2.7 LiveProviderConfig Modeli
- [ ] **Sağlayıcı Konfigürasyonu**
  - Açıklama: Tenant bazlı Jitsi/BBB/Zoom ayarları.
  - DoD: JWT secret, domain, API key gibi hassas bilgiler encrypted.
  - Kod/Path: `backend/live/models.py::LiveProviderConfig`
  - Öncelik: P0

```python
class LiveProviderConfig(TenantAwareModel):
    """
    Tenant bazlı canlı ders sağlayıcı konfigürasyonu.
    """
    class Provider(models.TextChoices):
        JITSI = 'jitsi', 'Jitsi Meet'
        BBB = 'bbb', 'BigBlueButton'
        ZOOM = 'zoom', 'Zoom'

    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.JITSI)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Jitsi config
    jitsi_domain = models.CharField(max_length=200, blank=True)
    jitsi_app_id = models.CharField(max_length=100, blank=True)
    jitsi_jwt_secret = models.CharField(max_length=500, blank=True)  # encrypted
    
    # BBB config
    bbb_server_url = models.URLField(blank=True)
    bbb_shared_secret = models.CharField(max_length=200, blank=True)  # encrypted
    
    # Zoom config
    zoom_account_id = models.CharField(max_length=100, blank=True)
    zoom_client_id = models.CharField(max_length=100, blank=True)
    zoom_client_secret = models.CharField(max_length=200, blank=True)  # encrypted
    
    # Genel ayarlar
    max_concurrent_rooms = models.PositiveIntegerField(default=10)
    default_room_duration_minutes = models.PositiveIntegerField(default=120)
    
    class Meta:
        verbose_name = _('Sağlayıcı Konfigürasyonu')
        unique_together = ['tenant', 'provider']
```

### 2.8 Migration ve Index Oluşturma
- [ ] **İlk Migration**
  - Açıklama: Tüm modeller için initial migration oluştur.
  - DoD: `python manage.py makemigrations live` başarılı; `migrate` hatasız çalışır.
  - Kod/Path: `backend/live/migrations/0001_initial.py`
  - Öncelik: P0

---

## 3) Provider Abstraction (Adapter Pattern)

### 3.1 Base Provider Interface
- [ ] **LiveClassProvider Abstract Base Class**
  - Açıklama: Tüm provider adapter'ların implement edeceği interface.
  - DoD: ABC ile tanımlı; tüm metodlar documented; type hints mevcut.
  - Kod/Path: `backend/live/providers/base.py::LiveClassProvider`
  - Öncelik: P0

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class RoomInfo:
    """Provider'dan dönen oda bilgisi."""
    room_id: str
    room_url: str
    password: Optional[str] = None
    moderator_url: Optional[str] = None
    dial_in: Optional[str] = None

@dataclass
class JoinInfo:
    """Katılım için gerekli bilgiler."""
    join_url: str
    token: Optional[str] = None
    expires_at: Optional[datetime] = None

@dataclass
class ParticipantInfo:
    """Katılımcı bilgisi."""
    user_id: str
    name: str
    role: str
    is_presenter: bool
    has_video: bool
    has_audio: bool
    joined_at: datetime

@dataclass
class RecordingInfo:
    """Kayıt bilgisi."""
    recording_id: str
    url: str
    duration_seconds: int
    size_bytes: int
    format: str
    created_at: datetime

class LiveClassProvider(ABC):
    """
    Canlı ders sağlayıcı abstract interface.
    
    Tüm provider adapter'lar bu interface'i implement eder.
    """
    
    @abstractmethod
    def create_room(self, session: 'LiveSession') -> RoomInfo:
        """Yeni oda oluşturur."""
        pass
    
    @abstractmethod
    def start_session(self, session: 'LiveSession') -> bool:
        """Oturumu başlatır."""
        pass
    
    @abstractmethod
    def end_session(self, session: 'LiveSession') -> bool:
        """Oturumu sonlandırır."""
        pass
    
    @abstractmethod
    def generate_join_url(self, session: 'LiveSession', user, role: str) -> JoinInfo:
        """Katılım URL'i oluşturur."""
        pass
    
    @abstractmethod
    def get_participants(self, session: 'LiveSession') -> List[ParticipantInfo]:
        """Aktif katılımcıları getirir."""
        pass
    
    @abstractmethod
    def start_recording(self, session: 'LiveSession') -> str:
        """Kaydı başlatır, recording_id döner."""
        pass
    
    @abstractmethod
    def stop_recording(self, session: 'LiveSession') -> bool:
        """Kaydı durdurur."""
        pass
    
    @abstractmethod
    def get_recordings(self, session: 'LiveSession') -> List[RecordingInfo]:
        """Oturum kayıtlarını getirir."""
        pass
    
    @abstractmethod
    def delete_room(self, session: 'LiveSession') -> bool:
        """Odayı siler."""
        pass
    
    @abstractmethod
    def handle_webhook(self, payload: dict) -> dict:
        """Webhook event'ini işler, normalized event döner."""
        pass
```

### 3.2 Jitsi Adapter
- [ ] **JitsiProvider Implementation**
  - Açıklama: Jitsi Meet için JWT tabanlı adapter. Self-hosted Jitsi destekler.
  - DoD: create_room, join_url, recording API çalışır; JWT claims doğru.
  - Kod/Path: `backend/live/providers/jitsi.py::JitsiProvider`
  - Öncelik: P0

```python
import jwt
import time
from datetime import datetime, timedelta
from typing import List, Optional
from .base import LiveClassProvider, RoomInfo, JoinInfo, ParticipantInfo, RecordingInfo

class JitsiProvider(LiveClassProvider):
    """
    Jitsi Meet adapter.
    
    JWT ile authentication, moderator claims ile rol yönetimi.
    """
    
    def __init__(self, config: 'LiveProviderConfig'):
        self.domain = config.jitsi_domain
        self.app_id = config.jitsi_app_id
        self.secret = config.jitsi_jwt_secret
    
    def create_room(self, session: 'LiveSession') -> RoomInfo:
        room_name = f"{session.tenant.slug}-{session.id}"
        room_url = f"https://{self.domain}/{room_name}"
        return RoomInfo(
            room_id=room_name,
            room_url=room_url,
        )
    
    def generate_join_url(self, session: 'LiveSession', user, role: str) -> JoinInfo:
        """JWT token ile join URL oluştur."""
        now = int(time.time())
        exp = now + 300  # 5 dakika
        
        payload = {
            "aud": "jitsi",
            "iss": self.app_id,
            "sub": self.domain,
            "room": session.room_id,
            "exp": exp,
            "nbf": now - 10,
            "context": {
                "user": {
                    "id": str(user.id),
                    "name": user.full_name,
                    "email": user.email,
                    "avatar": user.get_avatar_url(),
                },
                "features": {
                    "recording": role in ['host', 'moderator'],
                    "livestreaming": False,
                    "transcription": False,
                }
            },
            "moderator": role in ['host', 'moderator'],
        }
        
        token = jwt.encode(payload, self.secret, algorithm="HS256")
        join_url = f"https://{self.domain}/{session.room_id}?jwt={token}"
        
        return JoinInfo(
            join_url=join_url,
            token=token,
            expires_at=datetime.fromtimestamp(exp),
        )
    
    # ... diğer metodlar
```

### 3.3 BBB Adapter
- [ ] **BBBProvider Implementation**
  - Açıklama: BigBlueButton API adapter. Checksum signature ile authentication.
  - DoD: create, join, end, getRecordings API çalışır.
  - Kod/Path: `backend/live/providers/bbb.py::BBBProvider`
  - Öncelik: P1

### 3.4 Zoom Adapter (Placeholder)
- [ ] **ZoomProvider Placeholder**
  - Açıklama: Zoom OAuth + Meeting/Webinar API placeholder.
  - DoD: Interface implement edilmiş, NotImplementedError fırlatır.
  - Kod/Path: `backend/live/providers/zoom.py::ZoomProvider`
  - Öncelik: P2

### 3.5 Provider Factory
- [ ] **Provider Factory Service**
  - Açıklama: Tenant config'e göre doğru provider instance'ı döner.
  - DoD: `get_provider(tenant)` çağrısı ile aktif provider alınır.
  - Kod/Path: `backend/live/providers/__init__.py::get_provider`
  - Öncelik: P0

```python
def get_provider(tenant: 'Tenant') -> LiveClassProvider:
    """Tenant için aktif provider'ı döner."""
    config = LiveProviderConfig.objects.filter(
        tenant=tenant,
        is_active=True,
        is_default=True,
    ).first()
    
    if not config:
        raise ValueError(f"No active provider for tenant: {tenant.slug}")
    
    if config.provider == 'jitsi':
        return JitsiProvider(config)
    elif config.provider == 'bbb':
        return BBBProvider(config)
    elif config.provider == 'zoom':
        return ZoomProvider(config)
    
    raise ValueError(f"Unknown provider: {config.provider}")
```

### 3.6 Normalized Event Model
- [ ] **Event Normalization**
  - Açıklama: Provider webhook'larını ortak event formatına çevir.
  - DoD: Jitsi/BBB event'leri aynı formatta işlenir.
  - Kod/Path: `backend/live/providers/events.py::NormalizedEvent`
  - Öncelik: P0

```python
@dataclass
class NormalizedEvent:
    """Provider-agnostic event."""
    event_type: str  # session_started, session_ended, participant_joined, participant_left, recording_ready
    session_id: str
    timestamp: datetime
    payload: dict
    provider: str
    raw_event: dict
```

---

## 4) API Contract (DRF)

### 4.1 Live Session Endpoints
- [ ] **POST /api/v1/live-sessions/** - Oluştur
  - Açıklama: Yeni canlı ders planla veya anlık başlat.
  - DoD: Eğitmen/Admin yetkisi; room otomatik oluşur; validation çalışır.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.create`
  - Öncelik: P0

- [ ] **GET /api/v1/live-sessions/{id}/** - Detay
  - Açıklama: Tek session detayı.
  - DoD: Course enrollment kontrolü yapılır.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.retrieve`
  - Öncelik: P0

- [ ] **POST /api/v1/live-sessions/{id}/start/** - Başlat
  - Açıklama: Planlı dersi başlat, status=live yap.
  - DoD: Sadece eğitmen/moderatör; actual_start set edilir.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.start`
  - Öncelik: P0

- [ ] **POST /api/v1/live-sessions/{id}/join/** - Katıl
  - Açıklama: Join URL al, participant kaydı oluştur.
  - DoD: Role-based JWT/token döner; kayıt başlar.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.join`
  - Öncelik: P0

- [ ] **POST /api/v1/live-sessions/{id}/end/** - Bitir
  - Açıklama: Oturumu sonlandır.
  - DoD: status=ended; actual_end set; attendance hesapla task tetikle.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.end`
  - Öncelik: P0

- [ ] **GET /api/v1/live-sessions/{id}/attendance/** - Yoklama
  - Açıklama: Katılım özeti + kişi bazlı detay.
  - DoD: Eğitmen/Admin görebilir; CSV export destekli.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.attendance`
  - Öncelik: P0

- [ ] **GET /api/v1/live-sessions/{id}/recordings/** - Kayıtlar
  - Açıklama: Session kayıt listesi.
  - DoD: Sadece published olanlar öğrencilere görünür.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.recordings`
  - Öncelik: P0

- [ ] **POST /api/v1/live-sessions/{id}/recordings/{rid}/publish/** - Yayınla
  - Açıklama: Kaydı LMS'de yayınla.
  - DoD: status=published; öğrenciler görür.
  - Kod/Path: `backend/live/views.py::RecordingViewSet.publish`
  - Öncelik: P0

### 4.2 Webhook Endpoints
- [ ] **POST /api/v1/live-sessions/webhooks/{provider}/** - Webhook Handler
  - Açıklama: Jitsi/BBB webhook'larını al, normalized event'e çevir, işle.
  - DoD: Signature verification; event processing; retry desteği.
  - Kod/Path: `backend/live/views.py::WebhookView`
  - Öncelik: P0

### 4.3 Admin Config Endpoint
- [ ] **GET/PUT /api/v1/tenants/{id}/live-config/** - Sağlayıcı Config
  - Açıklama: Tenant için Jitsi/BBB ayarları.
  - DoD: Sadece Tenant Admin; secret'lar masked döner, write'da decrypt.
  - Kod/Path: `backend/live/views.py::LiveConfigView`
  - Öncelik: P0

### 4.4 Serializers
- [ ] **LiveSessionSerializer**
  - Açıklama: CRUD için ana serializer.
  - DoD: Nested course/content; read_only fields doğru.
  - Kod/Path: `backend/live/serializers.py::LiveSessionSerializer`
  - Öncelik: P0

- [ ] **LiveSessionDetailSerializer**
  - Açıklama: Detay için genişletilmiş serializer.
  - DoD: Participants count, recordings count, policy dahil.
  - Kod/Path: `backend/live/serializers.py::LiveSessionDetailSerializer`
  - Öncelik: P0

- [ ] **JoinResponseSerializer**
  - Açıklama: Join response için serializer.
  - DoD: join_url, token, role, expires_at.
  - Kod/Path: `backend/live/serializers.py::JoinResponseSerializer`
  - Öncelik: P0

- [ ] **AttendanceSerializer**
  - Açıklama: Yoklama raporu serializer.
  - DoD: User info + duration + attended flag.
  - Kod/Path: `backend/live/serializers.py::AttendanceSerializer`
  - Öncelik: P0

- [ ] **RecordingSerializer**
  - Açıklama: Kayıt serializer.
  - DoD: Duration, status, thumbnail, download_url.
  - Kod/Path: `backend/live/serializers.py::RecordingSerializer`
  - Öncelik: P0

### 4.5 Permission Classes
- [ ] **IsSessionInstructor**
  - Açıklama: Oturumu oluşturan veya kurs eğitmeni.
  - DoD: has_object_permission implement.
  - Kod/Path: `backend/live/permissions.py::IsSessionInstructor`
  - Öncelik: P0

- [ ] **CanJoinSession**
  - Açıklama: Kursa kayıtlı veya eğitmen.
  - DoD: Enrollment veya instructor kontrolü.
  - Kod/Path: `backend/live/permissions.py::CanJoinSession`
  - Öncelik: P0

---

## 5) Kayıt (Recording) Pipeline

### 5.1 Recording İş Akışı
- [ ] **Recording Status Machine**
  - Açıklama: processing → ready → published / failed state transitions.
  - DoD: Invalid transition'lar için exception.
  - Kod/Path: `backend/live/services/recording_service.py`
  - Öncelik: P0

### 5.2 Webhook ile Tespit
- [ ] **Recording Ready Webhook Handler**
  - Açıklama: Provider recording_ready event'ini yakala.
  - DoD: LiveSessionRecording kaydı oluşur; Celery task tetiklenir.
  - Kod/Path: `backend/live/services/webhook_service.py::handle_recording_ready`
  - Öncelik: P0

### 5.3 Storage Transfer
- [ ] **Recording Download & Upload Task**
  - Açıklama: Provider'dan indir, S3/MinIO'ya yükle.
  - DoD: Celery task; retry logic; progress tracking.
  - Kod/Path: `backend/live/tasks.py::process_recording_task`
  - Öncelik: P0

### 5.4 Thumbnail Oluşturma
- [ ] **Thumbnail Generation Task**
  - Açıklama: FFmpeg ile video thumbnail çıkar.
  - DoD: 5. saniyeden frame; 640x360 boyut; S3'e yükle.
  - Kod/Path: `backend/live/tasks.py::generate_thumbnail_task`
  - Öncelik: P1

### 5.5 Retention Policy
- [ ] **Recording Cleanup Task**
  - Açıklama: Süresi dolan kayıtları sil.
  - DoD: Celery beat ile günlük çalışır; tenant policy'ye göre sil.
  - Kod/Path: `backend/live/tasks.py::cleanup_expired_recordings`
  - Öncelik: P1

### 5.6 Erişim Kontrolü
- [ ] **Recording Access Check**
  - Açıklama: Kayda erişim: enrolled + published kontrolü.
  - DoD: Signed URL ile time-limited erişim.
  - Kod/Path: `backend/live/services/recording_service.py::get_access_url`
  - Öncelik: P0

---

## 6) Katılım Takibi (Attendance)

### 6.1 Join/Leave Event Toplama
- [ ] **Participant Event Handler**
  - Açıklama: Webhook'tan gelen join/leave event'lerini işle.
  - DoD: LiveSessionParticipant kaydı oluşur/güncellenir.
  - Kod/Path: `backend/live/services/attendance_service.py::handle_participant_event`
  - Öncelik: P0

### 6.2 Heartbeat Mekanizması
- [ ] **Frontend Heartbeat Endpoint**
  - Açıklama: Frontend her 30-60 sn'de heartbeat gönderir.
  - DoD: POST /api/v1/live-sessions/{id}/heartbeat/; last_seen güncellenir.
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.heartbeat`
  - Öncelik: P1

### 6.3 Katılım Hesaplama
- [ ] **Calculate Attendance Summary Task**
  - Açıklama: Session bittikten sonra her kullanıcı için özet hesapla.
  - DoD: Toplam süre, %70 eşiği, late/early flag.
  - Kod/Path: `backend/live/tasks.py::calculate_attendance_task`
  - Öncelik: P0

### 6.4 Attended Kuralı
- [ ] **Attendance Policy Application**
  - Açıklama: Policy'deki threshold'a göre attended flag belirle.
  - DoD: %70 toplam süre VEYA minimum X dakika.
  - Kod/Path: `backend/live/services/attendance_service.py::apply_attendance_policy`
  - Öncelik: P0

### 6.5 Hile Önleme (Basic)
- [ ] **Tab Visibility Detection**
  - Açıklama: Frontend tab arka plandayken sinyal gönderir.
  - DoD: Background süre ayrı tutulur; raporda gösterilir.
  - Kod/Path: `backend/live/models.py::LiveSessionParticipant.background_duration`
  - Öncelik: P1

### 6.6 Raporlar
- [ ] **Attendance Report Endpoint**
  - Açıklama: Ders bazlı yoklama raporu.
  - DoD: JSON + CSV export; filter destekli.
  - Kod/Path: `backend/live/views.py::AttendanceReportView`
  - Öncelik: P0

- [ ] **User Attendance History**
  - Açıklama: Kullanıcının tüm katılım geçmişi.
  - DoD: Course filter; date range filter.
  - Kod/Path: `backend/live/views.py::UserAttendanceView`
  - Öncelik: P1

---

## 7) Whiteboard ve Artifacts

### 7.1 BBB Whiteboard
- [ ] **BBB Whiteboard Export**
  - Açıklama: BBB oturum sonunda whiteboard PDF/PNG export.
  - DoD: Webhook ile tetik; artifact olarak kaydet.
  - Kod/Path: `backend/live/services/artifact_service.py::export_bbb_whiteboard`
  - Öncelik: P1

### 7.2 Jitsi Whiteboard
- [ ] **Jitsi Excalidraw Entegrasyonu**
  - Açıklama: Excalidraw embed; session ile ilişkilendir.
  - DoD: Board ID session'a bağlı; export endpoint.
  - Kod/Path: `backend/live/services/whiteboard_service.py`
  - Öncelik: P2

### 7.3 Chat Export
- [ ] **Chat Log Export**
  - Açıklama: Oturum sohbet logunu kaydet.
  - DoD: JSON formatında artifact; timestamp + sender + message.
  - Kod/Path: `backend/live/services/artifact_service.py::export_chat_log`
  - Öncelik: P1

### 7.4 Artifact Download
- [ ] **Artifact Download Endpoint**
  - Açıklama: Whiteboard/chat indirme.
  - DoD: Signed URL; access control.
  - Kod/Path: `backend/live/views.py::ArtifactViewSet.download`
  - Öncelik: P1

---

## 8) Bildirimler ve Takvim

### 8.1 Hatırlatıcı Bildirimleri
- [ ] **T-24h Reminder Task**
  - Açıklama: Ders başlamadan 24 saat önce bildirim.
  - DoD: Celery beat; email + push.
  - Kod/Path: `backend/live/tasks.py::send_reminder_24h`
  - Öncelik: P0

- [ ] **T-1h Reminder Task**
  - Açıklama: 1 saat önce bildirim.
  - DoD: Email + push.
  - Kod/Path: `backend/live/tasks.py::send_reminder_1h`
  - Öncelik: P0

- [ ] **T-10m Reminder Task**
  - Açıklama: 10 dakika önce bildirim.
  - DoD: Push only (email çok geç).
  - Kod/Path: `backend/live/tasks.py::send_reminder_10m`
  - Öncelik: P0

### 8.2 Durum Bildirimleri
- [ ] **Session Started Notification**
  - Açıklama: Ders başladı bildirimi.
  - DoD: Enrolled users'a push.
  - Kod/Path: `backend/live/tasks.py::notify_session_started`
  - Öncelik: P0

- [ ] **Session Cancelled Notification**
  - Açıklama: İptal/erteleme bildirimi.
  - DoD: Email + push; yeni tarih varsa belirt.
  - Kod/Path: `backend/live/tasks.py::notify_session_cancelled`
  - Öncelik: P0

- [ ] **Recording Published Notification**
  - Açıklama: Kayıt yayınlandı bildirimi.
  - DoD: Enrolled users'a email.
  - Kod/Path: `backend/live/tasks.py::notify_recording_published`
  - Öncelik: P1

### 8.3 Calendar Integration
- [ ] **ICS File Generation**
  - Açıklama: .ics takvim dosyası oluştur.
  - DoD: Title, description, datetime, join URL.
  - Kod/Path: `backend/live/services/calendar_service.py::generate_ics`
  - Öncelik: P0

- [ ] **Add to Calendar Endpoint**
  - Açıklama: ICS dosyası indirme endpoint.
  - DoD: GET /api/v1/live-sessions/{id}/calendar/
  - Kod/Path: `backend/live/views.py::LiveSessionViewSet.calendar`
  - Öncelik: P0

---

## 9) Güvenlik, KVKK ve Audit

### 9.1 Join Token Güvenliği
- [ ] **Short-lived Join Token**
  - Açıklama: 2-5 dakika geçerli token.
  - DoD: Expiry check; tek kullanımlık opsiyonu.
  - Kod/Path: `backend/live/services/token_service.py`
  - Öncelik: P0

- [ ] **Token Replay Prevention**
  - Açıklama: Aynı token'ın tekrar kullanılmasını engelle.
  - DoD: Redis'te kullanılmış token cache; TTL = token expiry.
  - Kod/Path: `backend/live/services/token_service.py::validate_token`
  - Öncelik: P1

### 9.2 Rate Limiting
- [ ] **Join Endpoint Rate Limit**
  - Açıklama: Brute-force koruması.
  - DoD: 10 request/dk per user; 100 request/dk per IP.
  - Kod/Path: `backend/live/throttling.py`
  - Öncelik: P0

### 9.3 Embed Güvenliği
- [ ] **CSP Headers for Iframe**
  - Açıklama: iframe embed için CSP ayarları.
  - DoD: frame-ancestors tenant domain only.
  - Kod/Path: `backend/live/middleware.py::LiveSessionCSPMiddleware`
  - Öncelik: P1

### 9.4 KVKK Uyumu
- [ ] **IP Hashing**
  - Açıklama: IP adresini hash'leyerek sakla.
  - DoD: SHA-256 + salt; raw IP tutma.
  - Kod/Path: `backend/live/utils.py::hash_ip`
  - Öncelik: P0

- [ ] **Log Minimization**
  - Açıklama: Sadece gerekli bilgileri logla.
  - DoD: PII maskeleme; retention policy.
  - Kod/Path: `backend/live/logging.py`
  - Öncelik: P0

### 9.5 Audit Logging
- [ ] **Session Lifecycle Audit**
  - Açıklama: create, start, end, cancel olaylarını logla.
  - DoD: AuditLog entry; user, action, timestamp.
  - Kod/Path: `backend/live/signals.py::log_session_event`
  - Öncelik: P0

- [ ] **Access Audit**
  - Açıklama: Join ve recording access logla.
  - DoD: User, resource, timestamp, IP hash.
  - Kod/Path: `backend/live/signals.py::log_access_event`
  - Öncelik: P0

---

## 10) Observability ve Operasyon

### 10.1 Metrikler
- [ ] **Prometheus Metrics**
  - Açıklama: concurrent_sessions, active_participants, webhook_latency.
  - DoD: /metrics endpoint; Grafana dashboard.
  - Kod/Path: `backend/live/metrics.py`
  - Öncelik: P1

### 10.2 Logging
- [ ] **Structured Logging**
  - Açıklama: JSON formatında log; session_id, tenant_id context.
  - DoD: Log aggregation uyumlu.
  - Kod/Path: `backend/live/logging.py`
  - Öncelik: P0

### 10.3 Health Check
- [ ] **Provider Health Check**
  - Açıklama: Jitsi/BBB erişilebilirlik kontrolü.
  - DoD: /health/live-provider endpoint; 5 sn timeout.
  - Kod/Path: `backend/live/health.py::check_provider_health`
  - Öncelik: P0

### 10.4 Admin Ops Dashboard
- [ ] **Live Ops Backend**
  - Açıklama: Aktif oturumlar, sunucu durumu, hatalar.
  - DoD: Admin API endpoint; son 100 event.
  - Kod/Path: `backend/live/views.py::LiveOpsView`
  - Öncelik: P1

### 10.5 Alerting
- [ ] **Webhook Failure Alert**
  - Açıklama: Webhook fail rate > %10 ise alert.
  - DoD: Celery task; Slack/email notification.
  - Kod/Path: `backend/live/tasks.py::check_webhook_health`
  - Öncelik: P1

---

## 11) Deployment ve Environment

### 11.1 Docker Compose
- [ ] **Live Module Docker Service**
  - Açıklama: docker-compose'a live service ekle.
  - DoD: Backend, Celery worker, Jitsi stack tanımlı.
  - Kod/Path: `infra/docker-compose.live.yml`
  - Öncelik: P0

### 11.2 Jitsi Self-Hosted Stack
- [ ] **Jitsi Docker Compose**
  - Açıklama: jitsi-web, jicofo, jvb, prosody containers.
  - DoD: docker-compose up ile çalışır; JWT auth aktif.
  - Kod/Path: `infra/jitsi/docker-compose.yml`
  - Öncelik: P0

### 11.3 Environment Variables
- [ ] **Live Config Env Vars**
  - Açıklama: JITSI_DOMAIN, JITSI_APP_ID, JITSI_JWT_SECRET.
  - DoD: .env.example dosyası; settings.py'da tanımlı.
  - Kod/Path: `.env.example`, `akademi/settings.py`
  - Öncelik: P0

### 11.4 Domain Routing
- [ ] **Nginx/Traefik Config**
  - Açıklama: meet.{tenant}.com routing.
  - DoD: SSL termination; WebSocket proxy.
  - Kod/Path: `infra/nginx/live.conf`
  - Öncelik: P1

### 11.5 Storage Lifecycle
- [ ] **S3 Lifecycle Policy**
  - Açıklama: Recording retention için S3 lifecycle rule.
  - DoD: 90 gün sonra Glacier; 180 gün sonra delete.
  - Kod/Path: `infra/s3/lifecycle.json`
  - Öncelik: P1

---

## 12) Test Stratejisi

### 12.1 Unit Tests
- [ ] **Provider Adapter Tests**
  - Açıklama: JitsiProvider metod testleri.
  - DoD: Mock ile API call simülasyonu; >90% coverage.
  - Kod/Path: `backend/live/tests/test_providers.py`
  - Öncelik: P0

- [ ] **Service Layer Tests**
  - Açıklama: AttendanceService, RecordingService testleri.
  - DoD: Edge case'ler; policy application.
  - Kod/Path: `backend/live/tests/test_services.py`
  - Öncelik: P0

### 12.2 Integration Tests
- [ ] **API Endpoint Tests**
  - Açıklama: ViewSet CRUD testleri.
  - DoD: Permission testleri; response format doğrulama.
  - Kod/Path: `backend/live/tests/test_views.py`
  - Öncelik: P0

- [ ] **Webhook Integration Tests**
  - Açıklama: Jitsi/BBB webhook payload testleri.
  - DoD: Signature verification; event processing.
  - Kod/Path: `backend/live/tests/test_webhooks.py`
  - Öncelik: P0

### 12.3 Load Tests
- [ ] **Concurrent Join Load Test**
  - Açıklama: 100 eşzamanlı katılım testi.
  - DoD: Locust script; <2 sn response time.
  - Kod/Path: `tests/load/live_session_load.py`
  - Öncelik: P1

### 12.4 Failure Scenarios
- [ ] **Provider Down Test**
  - Açıklama: Jitsi down olduğunda graceful degradation.
  - DoD: Error message; retry logic; fallback UI.
  - Kod/Path: `backend/live/tests/test_failures.py`
  - Öncelik: P1

---

## 13) AI-Native Genişleme (Backlog)

### 13.1 Otomatik Transkript
- [ ] **Recording → Transcript Pipeline**
  - Açıklama: Kayıt tamamlandığında Whisper ile transkript.
  - DoD: Celery task; VTT/SRT format; dil algılama.
  - Kod/Path: `backend/live/tasks.py::transcribe_recording`
  - Öncelik: P2

### 13.2 Ders Özeti
- [ ] **Transcript → Summary Pipeline**
  - Açıklama: Transkript'ten AI ile özet çıkar.
  - DoD: GPT-4 / Claude API; key points, timeline.
  - Kod/Path: `backend/ai/services/summary_service.py::summarize_transcript`
  - Öncelik: P2

### 13.3 Quiz Önerisi
- [ ] **Transcript → Quiz Pipeline**
  - Açıklama: Transkript'ten quiz soruları öner.
  - DoD: Multiple choice + open ended; topic extraction.
  - Kod/Path: `backend/ai/services/quiz_generator.py::generate_from_transcript`
  - Öncelik: P2

### 13.4 Etkileşim Skorlaması
- [ ] **Participation Score**
  - Açıklama: Konuşma süresi, chat aktivitesi, yoklama skoru.
  - DoD: 0-100 skor; dashboard'da gösterim.
  - Kod/Path: `backend/live/services/engagement_service.py`
  - Öncelik: P2

### 13.5 Eğitmen Koçluğu
- [ ] **Engagement Timeline Analysis**
  - Açıklama: "Hangi dakikada kopuş oldu" analizi.
  - DoD: Drop-off noktaları; öneriler.
  - Kod/Path: `backend/ai/services/instructor_coach.py`
  - Öncelik: P2

---

## 14) Frontend Komponentleri (React)

### 14.1 Live Session Card
- [ ] **LiveSessionCard Component**
  - Açıklama: Ders listesinde session kartı.
  - DoD: Title, datetime, status badge, join button.
  - Kod/Path: `frontend/features/live/components/LiveSessionCard.tsx`
  - Öncelik: P0

### 14.2 Join/Start Flow
- [ ] **JoinSessionButton Component**
  - Açıklama: Rol bazlı Join/Start butonu.
  - DoD: Eğitmen: Start, Öğrenci: Join; loading state.
  - Kod/Path: `frontend/features/live/components/JoinSessionButton.tsx`
  - Öncelik: P0

### 14.3 Session Room
- [ ] **LiveSessionRoom Page**
  - Açıklama: Jitsi iframe embed sayfası.
  - DoD: JWT ile auth; fullscreen toggle; leave button.
  - Kod/Path: `frontend/features/live/pages/LiveSessionRoom.tsx`
  - Öncelik: P0

### 14.4 Attendance Panel
- [ ] **AttendancePanel Component**
  - Açıklama: Eğitmen için katılımcı listesi.
  - DoD: Real-time update; kick/mute actions.
  - Kod/Path: `frontend/features/live/components/AttendancePanel.tsx`
  - Öncelik: P0

### 14.5 Recordings Tab
- [ ] **RecordingsTab Component**
  - Açıklama: Session kayıtları listesi.
  - DoD: Thumbnail, duration, publish toggle, download.
  - Kod/Path: `frontend/features/live/components/RecordingsTab.tsx`
  - Öncelik: P0

### 14.6 Schedule Modal
- [ ] **ScheduleSessionModal Component**
  - Açıklama: Yeni ders planlama modal.
  - DoD: Date/time picker; recurrence; course select.
  - Kod/Path: `frontend/features/live/components/ScheduleSessionModal.tsx`
  - Öncelik: P0

### 14.7 Device Test
- [ ] **DeviceTestScreen Component**
  - Açıklama: Mikrofon/kamera/speaker testi.
  - DoD: Preview; volume meter; speaker test.
  - Kod/Path: `frontend/features/live/components/DeviceTestScreen.tsx`
  - Öncelik: P1

### 14.8 Calendar Integration
- [ ] **LiveSessionCalendar Component**
  - Açıklama: Takvim görünümünde canlı dersler.
  - DoD: FullCalendar ile; click to join; ICS export.
  - Kod/Path: `frontend/features/live/components/LiveSessionCalendar.tsx`
  - Öncelik: P1

---

## 15) Uygulama Yapısı

### 15.1 Django App Oluşturma
- [ ] **Live App Initialization**
  - Açıklama: backend/live Django app oluştur.
  - DoD: apps.py, __init__.py, admin.py hazır.
  - Kod/Path: `backend/live/`
  - Öncelik: P0

```
backend/live/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── permissions.py
├── throttling.py
├── signals.py
├── tasks.py
├── migrations/
│   └── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── jitsi.py
│   ├── bbb.py
│   └── zoom.py
├── services/
│   ├── __init__.py
│   ├── session_service.py
│   ├── attendance_service.py
│   ├── recording_service.py
│   ├── webhook_service.py
│   ├── token_service.py
│   ├── calendar_service.py
│   └── artifact_service.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_providers.py
    ├── test_services.py
    ├── test_views.py
    └── test_webhooks.py
```

### 15.2 Settings Integration
- [ ] **Settings Update**
  - Açıklama: INSTALLED_APPS'e live ekle; config değişkenler.
  - DoD: 'backend.live' installed; LIVE_* settings tanımlı.
  - Kod/Path: `akademi/settings.py`
  - Öncelik: P0

### 15.3 URL Integration
- [ ] **URL Registration**
  - Açıklama: ana urls.py'a live endpoints ekle.
  - DoD: /api/v1/live-sessions/ active.
  - Kod/Path: `akademi/urls.py`
  - Öncelik: P0

---

## Uygulama Sırası (Önerilen)

### Sprint 1 (1 Hafta) - Core Infrastructure
1. Django app oluştur
2. Temel modeller (LiveSession, LiveSessionParticipant)
3. Jitsi Provider adapter
4. Basic ViewSet (create, retrieve, list)

### Sprint 2 (1 Hafta) - Session Lifecycle
1. Start/End/Join endpoints
2. Join token generation
3. Webhook handler
4. Participant tracking

### Sprint 3 (1 Hafta) - Recording & Attendance
1. Recording model ve service
2. Attendance calculation
3. Storage integration
4. Celery tasks

### Sprint 4 (1 Hafta) - Frontend & Polish
1. React komponentleri
2. Notification tasks
3. Calendar integration
4. Testing & Documentation

---

## Teknik Notlar

### JWT Token Yapısı (Jitsi)
```json
{
  "aud": "jitsi",
  "iss": "your-app-id",
  "sub": "meet.yourdomain.com",
  "room": "tenant-slug-session-uuid",
  "exp": 1703700000,
  "context": {
    "user": {
      "id": "user-uuid",
      "name": "Ahmet Yılmaz",
      "email": "ahmet@example.com",
      "avatar": "https://..."
    },
    "features": {
      "recording": true,
      "livestreaming": false
    }
  },
  "moderator": true
}
```

### Webhook Payload (Jitsi)
```json
{
  "event": "participant_joined",
  "room": "tenant-slug-session-uuid",
  "participant": {
    "id": "user-uuid",
    "name": "Ahmet Yılmaz"
  },
  "timestamp": 1703700000
}
```

### Celery Beat Schedule
```python
CELERYBEAT_SCHEDULE = {
    'send-24h-reminders': {
        'task': 'backend.live.tasks.send_reminder_24h',
        'schedule': crontab(minute=0, hour='*'),
    },
    'send-1h-reminders': {
        'task': 'backend.live.tasks.send_reminder_1h',
        'schedule': crontab(minute=0, hour='*'),
    },
    'cleanup-expired-recordings': {
        'task': 'backend.live.tasks.cleanup_expired_recordings',
        'schedule': crontab(minute=0, hour=2),  # Her gün 02:00
    },
}
```

---

**Son Güncelleme:** 27 Aralık 2024
**Hazırlayan:** AI Coding Agent - B6 Live Class Module Planning

