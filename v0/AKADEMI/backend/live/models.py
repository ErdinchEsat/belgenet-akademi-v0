"""
Live Session Models
===================

Canlı ders modülleri için veritabanı modelleri.
Provider-agnostic mimari ile tasarlanmıştır.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from backend.libs.tenant_aware.models import TenantAwareModel


class LiveProviderConfig(TenantAwareModel):
    """
    Tenant bazlı canlı ders sağlayıcı konfigürasyonu.
    
    Her tenant için farklı provider (Jitsi/BBB/Zoom) ayarları tutulur.
    Secrets encrypted olarak saklanmalıdır.
    """

    class Provider(models.TextChoices):
        """Desteklenen sağlayıcılar."""
        JITSI = 'jitsi', 'Jitsi Meet'
        BBB = 'bbb', 'BigBlueButton'
        ZOOM = 'zoom', 'Zoom'

    provider = models.CharField(
        _('Sağlayıcı'),
        max_length=20,
        choices=Provider.choices,
        default=Provider.JITSI,
    )
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    is_default = models.BooleanField(
        _('Varsayılan'),
        default=False,
    )
    
    # Jitsi config
    jitsi_domain = models.CharField(
        _('Jitsi Domain'),
        max_length=200,
        blank=True,
        help_text=_('Örn: meet.yourdomain.com'),
    )
    jitsi_app_id = models.CharField(
        _('Jitsi App ID'),
        max_length=100,
        blank=True,
    )
    jitsi_jwt_secret = models.CharField(
        _('Jitsi JWT Secret'),
        max_length=500,
        blank=True,
        help_text=_('JWT imzalama için gizli anahtar'),
    )
    
    # BBB config
    bbb_server_url = models.URLField(
        _('BBB Server URL'),
        blank=True,
    )
    bbb_shared_secret = models.CharField(
        _('BBB Shared Secret'),
        max_length=200,
        blank=True,
    )
    
    # Zoom config
    zoom_account_id = models.CharField(
        _('Zoom Account ID'),
        max_length=100,
        blank=True,
    )
    zoom_client_id = models.CharField(
        _('Zoom Client ID'),
        max_length=100,
        blank=True,
    )
    zoom_client_secret = models.CharField(
        _('Zoom Client Secret'),
        max_length=200,
        blank=True,
    )
    
    # Genel ayarlar
    max_concurrent_rooms = models.PositiveIntegerField(
        _('Maksimum Eşzamanlı Oda'),
        default=10,
    )
    default_room_duration_minutes = models.PositiveIntegerField(
        _('Varsayılan Oda Süresi (dk)'),
        default=120,
    )
    
    class Meta:
        verbose_name = _('Sağlayıcı Konfigürasyonu')
        verbose_name_plural = _('Sağlayıcı Konfigürasyonları')
        unique_together = ['tenant', 'provider']
        
    def __str__(self):
        return f"{self.tenant.name} - {self.get_provider_display()}"
    
    def save(self, *args, **kwargs):
        # Eğer bu default olarak işaretlendiyse, diğerlerini kaldır
        if self.is_default:
            LiveProviderConfig.objects.filter(
                tenant=self.tenant,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class LiveSession(TenantAwareModel):
    """
    Canlı ders oturumu.
    
    Planlı dersler, anlık toplantılar ve webinar'ları destekler.
    Provider-agnostic room_id ile herhangi bir sağlayıcıya bağlanabilir.
    """

    class Type(models.TextChoices):
        """Oturum türleri."""
        SCHEDULED = 'scheduled', _('Planlı Ders')
        ADHOC = 'adhoc', _('Anlık Toplantı')
        WEBINAR = 'webinar', _('Webinar')

    class Status(models.TextChoices):
        """Oturum durumları."""
        DRAFT = 'draft', _('Taslak')
        SCHEDULED = 'scheduled', _('Planlandı')
        LIVE = 'live', _('Yayında')
        ENDED = 'ended', _('Bitti')
        CANCELLED = 'cancelled', _('İptal')

    # İlişkiler
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='live_sessions',
        verbose_name=_('Kurs'),
    )
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_sessions',
        verbose_name=_('İçerik'),
        help_text=_('İlişkili kurs içeriği (opsiyonel)'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_live_sessions',
        verbose_name=_('Oluşturan'),
    )
    
    # Temel bilgiler
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=Type.choices,
        default=Type.SCHEDULED,
    )
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    
    # Zamanlama
    scheduled_start = models.DateTimeField(
        _('Planlanan Başlangıç'),
    )
    scheduled_end = models.DateTimeField(
        _('Planlanan Bitiş'),
    )
    actual_start = models.DateTimeField(
        _('Gerçek Başlangıç'),
        null=True,
        blank=True,
    )
    actual_end = models.DateTimeField(
        _('Gerçek Bitiş'),
        null=True,
        blank=True,
    )
    
    # Provider bilgileri
    provider = models.CharField(
        _('Sağlayıcı'),
        max_length=20,
        choices=LiveProviderConfig.Provider.choices,
        default=LiveProviderConfig.Provider.JITSI,
    )
    room_id = models.CharField(
        _('Oda ID'),
        max_length=100,
        unique=True,
        db_index=True,
    )
    room_url = models.URLField(
        _('Oda URL'),
        blank=True,
    )
    room_password = models.CharField(
        _('Oda Şifresi'),
        max_length=50,
        blank=True,
    )
    moderator_url = models.URLField(
        _('Moderatör URL'),
        blank=True,
        help_text=_('BBB için moderatör giriş URL\'i'),
    )
    
    # Ayarlar
    max_participants = models.PositiveIntegerField(
        _('Maksimum Katılımcı'),
        default=100,
    )
    recording_enabled = models.BooleanField(
        _('Kayıt Aktif'),
        default=True,
    )
    auto_recording = models.BooleanField(
        _('Otomatik Kayıt'),
        default=False,
        help_text=_('Ders başladığında otomatik kayıt başlat'),
    )
    waiting_room_enabled = models.BooleanField(
        _('Bekleme Odası'),
        default=True,
    )
    students_can_share_screen = models.BooleanField(
        _('Öğrenci Ekran Paylaşımı'),
        default=False,
    )
    students_start_muted = models.BooleanField(
        _('Öğrenci Sessiz Başlasın'),
        default=True,
    )
    students_video_off = models.BooleanField(
        _('Öğrenci Kamera Kapalı'),
        default=False,
    )
    
    # İstatistikler (cache)
    participant_count = models.PositiveIntegerField(
        _('Toplam Katılımcı'),
        default=0,
    )
    peak_participants = models.PositiveIntegerField(
        _('En Yüksek Katılımcı'),
        default=0,
    )
    total_duration_minutes = models.PositiveIntegerField(
        _('Toplam Süre (dk)'),
        default=0,
    )

    class Meta:
        verbose_name = _('Canlı Ders')
        verbose_name_plural = _('Canlı Dersler')
        ordering = ['-scheduled_start']
        indexes = [
            models.Index(fields=['status', 'scheduled_start']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['room_id']),
            models.Index(fields=['provider', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Yeni kayıt ise room_id oluştur
        if not self.room_id:
            self.room_id = f"{self.tenant.slug}-{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)
    
    @property
    def is_live(self) -> bool:
        """Oturum şu anda aktif mi?"""
        return self.status == self.Status.LIVE
    
    @property
    def is_upcoming(self) -> bool:
        """Oturum henüz başlamadı mı?"""
        return self.status in [self.Status.DRAFT, self.Status.SCHEDULED]
    
    @property
    def can_join(self) -> bool:
        """Oturuma katılınabilir mi?"""
        if self.status != self.Status.LIVE:
            return False
        if self.max_participants and self.participant_count >= self.max_participants:
            return False
        return True
    
    @property
    def duration_minutes(self) -> int:
        """Planlanan süre (dakika)."""
        if self.scheduled_start and self.scheduled_end:
            delta = self.scheduled_end - self.scheduled_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def start(self):
        """Oturumu başlat."""
        if self.status not in [self.Status.DRAFT, self.Status.SCHEDULED]:
            raise ValueError(f"Cannot start session in status: {self.status}")
        self.status = self.Status.LIVE
        self.actual_start = timezone.now()
        self.save(update_fields=['status', 'actual_start', 'updated_at'])
    
    def end(self):
        """Oturumu sonlandır."""
        if self.status != self.Status.LIVE:
            raise ValueError(f"Cannot end session in status: {self.status}")
        self.status = self.Status.ENDED
        self.actual_end = timezone.now()
        if self.actual_start:
            delta = self.actual_end - self.actual_start
            self.total_duration_minutes = int(delta.total_seconds() / 60)
        self.save(update_fields=['status', 'actual_end', 'total_duration_minutes', 'updated_at'])
    
    def cancel(self, reason: str = ''):
        """Oturumu iptal et."""
        if self.status == self.Status.ENDED:
            raise ValueError("Cannot cancel ended session")
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])


class LiveSessionParticipant(models.Model):
    """
    Oturum katılımcısı.
    
    Her join/leave bir kayıt olarak tutulur.
    Aynı kullanıcı birden fazla kez katılıp ayrılabilir.
    """

    class Role(models.TextChoices):
        """Katılımcı rolleri."""
        HOST = 'host', _('Eğitmen')
        MODERATOR = 'moderator', _('Moderatör')
        PARTICIPANT = 'participant', _('Öğrenci')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('Oturum'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='live_session_participations',
        verbose_name=_('Kullanıcı'),
    )
    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )
    
    # Zaman bilgileri
    joined_at = models.DateTimeField(
        _('Katılım Zamanı'),
    )
    left_at = models.DateTimeField(
        _('Ayrılma Zamanı'),
        null=True,
        blank=True,
    )
    duration_seconds = models.PositiveIntegerField(
        _('Süre (sn)'),
        default=0,
    )
    
    # Cihaz/Konum bilgileri
    device_type = models.CharField(
        _('Cihaz Türü'),
        max_length=50,
        blank=True,
        help_text=_('mobile, desktop, tablet'),
    )
    browser = models.CharField(
        _('Tarayıcı'),
        max_length=100,
        blank=True,
    )
    ip_hash = models.CharField(
        _('IP Hash'),
        max_length=64,
        blank=True,
        help_text=_('KVKK uyumu için IP hash\'i'),
    )
    
    # Durum
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
        help_text=_('Şu anda oturumda mı?'),
    )
    kicked = models.BooleanField(
        _('Atıldı'),
        default=False,
    )
    kick_reason = models.CharField(
        _('Atılma Nedeni'),
        max_length=200,
        blank=True,
    )
    
    # Heartbeat
    last_heartbeat = models.DateTimeField(
        _('Son Heartbeat'),
        null=True,
        blank=True,
    )
    background_duration_seconds = models.PositiveIntegerField(
        _('Arka Plan Süresi (sn)'),
        default=0,
        help_text=_('Sekme arka plandayken geçen süre'),
    )

    class Meta:
        verbose_name = _('Oturum Katılımcısı')
        verbose_name_plural = _('Oturum Katılımcıları')
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['session', 'user']),
            models.Index(fields=['session', 'is_active']),
            models.Index(fields=['joined_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.session.title}"
    
    def leave(self):
        """Oturumdan ayrıl."""
        self.left_at = timezone.now()
        self.is_active = False
        if self.joined_at:
            delta = self.left_at - self.joined_at
            self.duration_seconds = int(delta.total_seconds())
        self.save(update_fields=['left_at', 'is_active', 'duration_seconds'])


class LiveSessionAttendanceSummary(models.Model):
    """
    Kullanıcı bazlı katılım özeti.
    
    Her session-user çifti için tek kayıt.
    Session kapandığında hesaplanır.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='attendance_summaries',
        verbose_name=_('Oturum'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='live_attendance_summaries',
        verbose_name=_('Kullanıcı'),
    )
    
    # Süre hesabı
    total_duration_seconds = models.PositiveIntegerField(
        _('Toplam Süre (sn)'),
        default=0,
    )
    join_count = models.PositiveIntegerField(
        _('Katılım Sayısı'),
        default=1,
        help_text=_('Kaç kez katıldı'),
    )
    first_join = models.DateTimeField(
        _('İlk Katılım'),
    )
    last_leave = models.DateTimeField(
        _('Son Ayrılış'),
        null=True,
        blank=True,
    )
    
    # Katılım durumu
    attended = models.BooleanField(
        _('Katıldı'),
        default=False,
        help_text=_('Eşik değeri geçti mi?'),
    )
    attendance_percent = models.DecimalField(
        _('Katılım Yüzdesi'),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    late_join = models.BooleanField(
        _('Geç Katılım'),
        default=False,
    )
    early_leave = models.BooleanField(
        _('Erken Ayrılış'),
        default=False,
    )
    
    # Arka plan süresi
    background_duration_seconds = models.PositiveIntegerField(
        _('Arka Plan Süresi (sn)'),
        default=0,
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Katılım Özeti')
        verbose_name_plural = _('Katılım Özetleri')
        unique_together = ['session', 'user']
        ordering = ['-created_at']

    def __str__(self):
        status = "✓" if self.attended else "✗"
        return f"{self.user.email} - {self.session.title} [{status}]"
    
    @property
    def total_duration_minutes(self) -> int:
        """Toplam süre dakika cinsinden."""
        return self.total_duration_seconds // 60
    
    @property
    def effective_duration_seconds(self) -> int:
        """Efektif süre (arka plan süresi çıkarılmış)."""
        return max(0, self.total_duration_seconds - self.background_duration_seconds)


class LiveSessionRecording(TenantAwareModel):
    """
    Canlı ders kaydı.
    
    Provider'dan gelen kayıt dosyası.
    Storage'a taşınır, thumbnail oluşturulur.
    """

    class Status(models.TextChoices):
        """Kayıt durumları."""
        PROCESSING = 'processing', _('İşleniyor')
        READY = 'ready', _('Hazır')
        PUBLISHED = 'published', _('Yayında')
        FAILED = 'failed', _('Hata')
        DELETED = 'deleted', _('Silindi')

    session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name=_('Oturum'),
    )
    
    # Provider bilgileri
    provider_recording_id = models.CharField(
        _('Sağlayıcı Kayıt ID'),
        max_length=200,
    )
    provider_url = models.URLField(
        _('Sağlayıcı URL'),
        blank=True,
    )
    
    # Storage
    file = models.ForeignKey(
        'storage.FileUpload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_recordings',
        verbose_name=_('Dosya'),
    )
    storage_url = models.URLField(
        _('Storage URL'),
        blank=True,
    )
    storage_path = models.CharField(
        _('Storage Path'),
        max_length=500,
        blank=True,
    )
    
    # Metadata
    title = models.CharField(
        _('Başlık'),
        max_length=200,
        blank=True,
    )
    duration_seconds = models.PositiveIntegerField(
        _('Süre (sn)'),
        default=0,
    )
    file_size_bytes = models.BigIntegerField(
        _('Dosya Boyutu (byte)'),
        default=0,
    )
    format = models.CharField(
        _('Format'),
        max_length=20,
        default='mp4',
    )
    resolution = models.CharField(
        _('Çözünürlük'),
        max_length=20,
        blank=True,
        help_text=_('Örn: 1080p, 720p'),
    )
    
    # Thumbnail
    thumbnail_url = models.URLField(
        _('Thumbnail URL'),
        blank=True,
    )
    
    # Transkript
    transcript_status = models.CharField(
        _('Transkript Durumu'),
        max_length=20,
        default='none',
        choices=[
            ('none', _('Yok')),
            ('processing', _('İşleniyor')),
            ('ready', _('Hazır')),
            ('failed', _('Hata')),
        ],
    )
    transcript_url = models.URLField(
        _('Transkript URL'),
        blank=True,
    )
    
    # Yayın durumu
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        db_index=True,
    )
    is_public = models.BooleanField(
        _('Herkese Açık'),
        default=False,
    )
    published_at = models.DateTimeField(
        _('Yayın Tarihi'),
        null=True,
        blank=True,
    )
    
    # Retention
    expires_at = models.DateTimeField(
        _('Son Kullanma Tarihi'),
        null=True,
        blank=True,
    )
    
    # İstatistikler
    view_count = models.PositiveIntegerField(
        _('İzlenme Sayısı'),
        default=0,
    )
    download_count = models.PositiveIntegerField(
        _('İndirme Sayısı'),
        default=0,
    )

    class Meta:
        verbose_name = _('Ders Kaydı')
        verbose_name_plural = _('Ders Kayıtları')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.session.title} - {self.get_status_display()}"
    
    @property
    def duration_minutes(self) -> int:
        """Süre dakika cinsinden."""
        return self.duration_seconds // 60
    
    @property
    def file_size_mb(self) -> float:
        """Dosya boyutu MB cinsinden."""
        return round(self.file_size_bytes / (1024 * 1024), 2)
    
    def publish(self):
        """Kaydı yayınla."""
        if self.status != self.Status.READY:
            raise ValueError(f"Cannot publish recording in status: {self.status}")
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at', 'updated_at'])
    
    def unpublish(self):
        """Yayından kaldır."""
        if self.status != self.Status.PUBLISHED:
            raise ValueError(f"Cannot unpublish recording in status: {self.status}")
        self.status = self.Status.READY
        self.published_at = None
        self.save(update_fields=['status', 'published_at', 'updated_at'])


class LiveSessionArtifact(TenantAwareModel):
    """
    Oturum çıktıları.
    
    Whiteboard export, chat log, paylaşılan dosyalar.
    """

    class Type(models.TextChoices):
        """Çıktı türleri."""
        WHITEBOARD = 'whiteboard', _('Whiteboard')
        CHAT = 'chat', _('Sohbet')
        FILE = 'file', _('Dosya')
        POLL = 'poll', _('Anket')
        NOTES = 'notes', _('Notlar')
        SHARED_NOTES = 'shared_notes', _('Paylaşılan Notlar')

    session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='artifacts',
        verbose_name=_('Oturum'),
    )
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=Type.choices,
    )
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    
    # Dosya
    file = models.ForeignKey(
        'storage.FileUpload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_artifacts',
        verbose_name=_('Dosya'),
    )
    content = models.TextField(
        _('İçerik'),
        blank=True,
        help_text=_('JSON veya text (chat için)'),
    )
    
    # Meta
    metadata = models.JSONField(
        _('Ek Veri'),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _('Oturum Çıktısı')
        verbose_name_plural = _('Oturum Çıktıları')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.session.title} - {self.title}"


class LiveSessionPolicy(models.Model):
    """
    Canlı ders politikaları.
    
    Öncelik: session_level > course_level > tenant_level
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # Scope (sadece biri dolu olmalı)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='live_policies',
        verbose_name=_('Tenant'),
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='live_policies',
        verbose_name=_('Kurs'),
    )
    session = models.OneToOneField(
        LiveSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='policy',
        verbose_name=_('Oturum'),
    )
    
    # Kayıt politikası
    recording_required = models.BooleanField(
        _('Kayıt Zorunlu'),
        default=True,
    )
    auto_recording = models.BooleanField(
        _('Otomatik Kayıt'),
        default=False,
    )
    recording_retention_days = models.PositiveIntegerField(
        _('Kayıt Saklama Süresi (gün)'),
        default=90,
    )
    
    # Katılım politikası
    attendance_threshold_percent = models.PositiveIntegerField(
        _('Katılım Eşiği (%)'),
        default=70,
        help_text=_('Katıldı sayılması için gereken minimum yüzde'),
    )
    minimum_duration_minutes = models.PositiveIntegerField(
        _('Minimum Süre (dk)'),
        default=5,
        help_text=_('Katıldı sayılması için gereken minimum süre'),
    )
    late_join_tolerance_minutes = models.PositiveIntegerField(
        _('Geç Katılım Toleransı (dk)'),
        default=10,
    )
    early_leave_tolerance_minutes = models.PositiveIntegerField(
        _('Erken Ayrılış Toleransı (dk)'),
        default=10,
    )
    
    # Güvenlik
    lobby_enabled = models.BooleanField(
        _('Bekleme Odası'),
        default=True,
    )
    require_authentication = models.BooleanField(
        _('Kimlik Doğrulama Zorunlu'),
        default=True,
    )
    allow_guests = models.BooleanField(
        _('Misafir İzni'),
        default=False,
    )
    
    # Öğrenci izinleri
    students_can_share_screen = models.BooleanField(
        _('Öğrenci Ekran Paylaşabilir'),
        default=False,
    )
    students_can_use_whiteboard = models.BooleanField(
        _('Öğrenci Whiteboard Kullanabilir'),
        default=True,
    )
    students_can_unmute_self = models.BooleanField(
        _('Öğrenci Kendini Açabilir'),
        default=True,
    )
    students_start_muted = models.BooleanField(
        _('Öğrenci Sessiz Başlasın'),
        default=True,
    )
    students_video_off = models.BooleanField(
        _('Öğrenci Kamera Kapalı'),
        default=False,
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Canlı Ders Politikası')
        verbose_name_plural = _('Canlı Ders Politikaları')

    def __str__(self):
        if self.session:
            return f"Policy: {self.session.title}"
        if self.course:
            return f"Policy: {self.course.title}"
        if self.tenant:
            return f"Policy: {self.tenant.name}"
        return "Default Policy"
    
    def clean(self):
        """Sadece bir scope dolu olmalı."""
        from django.core.exceptions import ValidationError
        
        scopes = [self.tenant, self.course, self.session]
        filled = sum(1 for s in scopes if s is not None)
        
        if filled == 0:
            raise ValidationError("En az bir scope (tenant/course/session) belirtilmeli")
        if filled > 1:
            raise ValidationError("Sadece bir scope (tenant/course/session) belirtilebilir")
    
    @classmethod
    def get_effective_policy(cls, session: LiveSession) -> 'LiveSessionPolicy':
        """
        Session için geçerli policy'yi döndür.
        
        Öncelik: session > course > tenant > defaults
        """
        # Session level
        try:
            return session.policy
        except cls.DoesNotExist:
            pass
        
        # Course level
        policy = cls.objects.filter(course=session.course).first()
        if policy:
            return policy
        
        # Tenant level
        policy = cls.objects.filter(tenant=session.tenant).first()
        if policy:
            return policy
        
        # Return default (create if not exists)
        return cls()  # Default values

