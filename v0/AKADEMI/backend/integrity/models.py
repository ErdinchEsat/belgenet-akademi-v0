"""
Integrity Models
================

Video oynatma bütünlüğü ve güvenlik modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class DeviceFingerprint(TenantAwareModel):
    """
    Cihaz parmak izi.
    
    Kullanıcının cihaz ve tarayıcı bilgilerini saklar.
    Multi-device detection için kullanılır.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_fingerprints',
        verbose_name=_('Kullanıcı'),
    )
    
    # Fingerprint hash
    fingerprint_hash = models.CharField(
        _('Parmak İzi Hash'),
        max_length=255,
        db_index=True,
    )
    
    # Cihaz bilgileri
    device_type = models.CharField(
        _('Cihaz Tipi'),
        max_length=50,
        blank=True,
        help_text=_('desktop, mobile, tablet'),
    )
    
    os = models.CharField(
        _('İşletim Sistemi'),
        max_length=100,
        blank=True,
    )
    
    browser = models.CharField(
        _('Tarayıcı'),
        max_length=100,
        blank=True,
    )
    
    user_agent = models.TextField(
        _('User Agent'),
        blank=True,
    )
    
    # Ekran bilgileri
    screen_resolution = models.CharField(
        _('Ekran Çözünürlüğü'),
        max_length=50,
        blank=True,
    )
    
    timezone = models.CharField(
        _('Zaman Dilimi'),
        max_length=100,
        blank=True,
    )
    
    language = models.CharField(
        _('Dil'),
        max_length=20,
        blank=True,
    )
    
    # IP bilgisi (hash olarak)
    ip_hash = models.CharField(
        _('IP Hash'),
        max_length=255,
        blank=True,
    )
    
    # Güven skoru
    trust_score = models.FloatField(
        _('Güven Skoru'),
        default=1.0,
        help_text=_('0-1 arası, düşük = şüpheli'),
    )
    
    # Durum
    is_trusted = models.BooleanField(
        _('Güvenilir'),
        default=True,
    )
    
    is_blocked = models.BooleanField(
        _('Engellendi'),
        default=False,
    )
    
    # Kullanım sayısı
    session_count = models.PositiveIntegerField(
        _('Oturum Sayısı'),
        default=0,
    )
    
    first_seen_at = models.DateTimeField(
        _('İlk Görülme'),
        auto_now_add=True,
    )
    
    last_seen_at = models.DateTimeField(
        _('Son Görülme'),
        auto_now=True,
    )
    
    class Meta:
        verbose_name = _('Cihaz Parmak İzi')
        verbose_name_plural = _('Cihaz Parmak İzleri')
        unique_together = ['tenant', 'user', 'fingerprint_hash']
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_trusted']),
            models.Index(fields=['fingerprint_hash']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.fingerprint_hash[:8]}...)"


class IntegrityCheck(TenantAwareModel):
    """
    Bütünlük kontrol kaydı.
    
    Her playback session için periyodik bütünlük kontrolü.
    """
    
    class CheckStatus(models.TextChoices):
        """Kontrol durumları."""
        PASSED = 'passed', _('Geçti')
        WARNING = 'warning', _('Uyarı')
        FAILED = 'failed', _('Başarısız')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.CASCADE,
        related_name='integrity_checks',
        verbose_name=_('Oynatma Oturumu'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='integrity_checks',
        verbose_name=_('Kullanıcı'),
    )
    
    device = models.ForeignKey(
        DeviceFingerprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integrity_checks',
        verbose_name=_('Cihaz'),
    )
    
    # Kontrol sonucu
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=CheckStatus.choices,
        default=CheckStatus.PASSED,
    )
    
    # Kontrol skorları (0-1 arası)
    visibility_score = models.FloatField(
        _('Görünürlük Skoru'),
        default=1.0,
        help_text=_('Tab aktif olma oranı'),
    )
    
    playback_score = models.FloatField(
        _('Oynatma Skoru'),
        default=1.0,
        help_text=_('Normal oynatma davranışı'),
    )
    
    timing_score = models.FloatField(
        _('Zamanlama Skoru'),
        default=1.0,
        help_text=_('İzleme süresi tutarlılığı'),
    )
    
    overall_score = models.FloatField(
        _('Genel Skor'),
        default=1.0,
    )
    
    # Kontrol detayları
    checks_performed = models.JSONField(
        _('Yapılan Kontroller'),
        default=list,
    )
    """
    Checks örneği:
    [
        {"check": "tab_visibility", "passed": true, "value": 0.95},
        {"check": "playback_speed", "passed": true, "value": 1.0},
        {"check": "seek_pattern", "passed": false, "value": 0.3},
        {"check": "timing_consistency", "passed": true, "value": 0.9}
    ]
    """
    
    # Video pozisyonu
    video_position = models.PositiveIntegerField(
        _('Video Pozisyonu'),
        default=0,
    )
    
    # Client tarafından gönderilen veri
    client_data = models.JSONField(
        _('Client Verisi'),
        default=dict,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Bütünlük Kontrolü')
        verbose_name_plural = _('Bütünlük Kontrolleri')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'session', '-created_at']),
            models.Index(fields=['tenant', 'user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.session.id} - {self.status} ({self.overall_score:.2f})"


class PlaybackAnomaly(TenantAwareModel):
    """
    Oynatma anomalisi.
    
    Tespit edilen şüpheli davranışlar.
    """
    
    class AnomalyType(models.TextChoices):
        """Anomali türleri."""
        SPEED_MANIPULATION = 'speed', _('Hız Manipülasyonu')
        EXCESSIVE_SEEKING = 'seek', _('Aşırı Atlama')
        TAB_INACTIVE = 'tab', _('Tab Pasif')
        TIMING_MISMATCH = 'timing', _('Zamanlama Uyuşmazlığı')
        MULTI_DEVICE = 'multi_device', _('Çoklu Cihaz')
        RAPID_COMPLETION = 'rapid', _('Hızlı Tamamlama')
        POSITION_JUMP = 'jump', _('Pozisyon Atlama')
        SESSION_HIJACK = 'hijack', _('Oturum Ele Geçirme')
    
    class AnomalySeverity(models.TextChoices):
        """Anomali şiddeti."""
        LOW = 'low', _('Düşük')
        MEDIUM = 'medium', _('Orta')
        HIGH = 'high', _('Yüksek')
        CRITICAL = 'critical', _('Kritik')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.CASCADE,
        related_name='anomalies',
        verbose_name=_('Oynatma Oturumu'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playback_anomalies',
        verbose_name=_('Kullanıcı'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='anomalies',
        verbose_name=_('İçerik'),
    )
    
    # Anomali bilgileri
    anomaly_type = models.CharField(
        _('Anomali Türü'),
        max_length=20,
        choices=AnomalyType.choices,
    )
    
    severity = models.CharField(
        _('Şiddet'),
        max_length=20,
        choices=AnomalySeverity.choices,
        default=AnomalySeverity.LOW,
    )
    
    # Detaylar
    description = models.TextField(
        _('Açıklama'),
    )
    
    details = models.JSONField(
        _('Detaylar'),
        default=dict,
    )
    """
    Details örneği:
    {
        "detected_speed": 16.0,
        "expected_speed": 1.0,
        "video_position": 120,
        "detection_method": "server_timing"
    }
    """
    
    # Video zamanı
    video_ts = models.PositiveIntegerField(
        _('Video Zamanı'),
        null=True,
        blank=True,
    )
    
    # İşlem durumu
    is_reviewed = models.BooleanField(
        _('İncelendi'),
        default=False,
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_anomalies',
        verbose_name=_('İnceleyen'),
    )
    
    reviewed_at = models.DateTimeField(
        _('İnceleme Zamanı'),
        null=True,
        blank=True,
    )
    
    review_notes = models.TextField(
        _('İnceleme Notları'),
        blank=True,
    )
    
    # Aksiyon alındı mı?
    action_taken = models.CharField(
        _('Alınan Aksiyon'),
        max_length=100,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Oynatma Anomalisi')
        verbose_name_plural = _('Oynatma Anomalileri')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'anomaly_type', 'severity']),
            models.Index(fields=['is_reviewed']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_anomaly_type_display()} ({self.severity})"


class UserIntegrityScore(TenantAwareModel):
    """
    Kullanıcı bütünlük skoru.
    
    Kullanıcının genel güvenilirlik profili.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='integrity_score',
        verbose_name=_('Kullanıcı'),
    )
    
    # Skor (0-100)
    score = models.PositiveIntegerField(
        _('Skor'),
        default=100,
    )
    
    # Metrikler
    total_checks = models.PositiveIntegerField(
        _('Toplam Kontrol'),
        default=0,
    )
    
    passed_checks = models.PositiveIntegerField(
        _('Geçen Kontrol'),
        default=0,
    )
    
    failed_checks = models.PositiveIntegerField(
        _('Başarısız Kontrol'),
        default=0,
    )
    
    anomaly_count = models.PositiveIntegerField(
        _('Anomali Sayısı'),
        default=0,
    )
    
    # Risk seviyesi
    risk_level = models.CharField(
        _('Risk Seviyesi'),
        max_length=20,
        default='low',
        help_text=_('low, medium, high'),
    )
    
    # Kısıtlamalar
    is_restricted = models.BooleanField(
        _('Kısıtlı'),
        default=False,
    )
    
    restriction_reason = models.TextField(
        _('Kısıtlama Nedeni'),
        blank=True,
    )
    
    restricted_at = models.DateTimeField(
        _('Kısıtlama Zamanı'),
        null=True,
        blank=True,
    )
    
    # Son güncelleme
    last_check_at = models.DateTimeField(
        _('Son Kontrol'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Kullanıcı Bütünlük Skoru')
        verbose_name_plural = _('Kullanıcı Bütünlük Skorları')
    
    def __str__(self):
        return f"{self.user.email} - Skor: {self.score}"
    
    @property
    def pass_rate(self) -> float:
        """Geçme oranı."""
        if self.total_checks == 0:
            return 1.0
        return self.passed_checks / self.total_checks


class IntegrityConfig(TenantAwareModel):
    """
    Tenant bazlı bütünlük yapılandırması.
    """
    
    # Eşik değerleri
    min_visibility_score = models.FloatField(
        _('Min. Görünürlük Skoru'),
        default=0.7,
    )
    
    min_playback_score = models.FloatField(
        _('Min. Oynatma Skoru'),
        default=0.6,
    )
    
    min_overall_score = models.FloatField(
        _('Min. Genel Skor'),
        default=0.5,
    )
    
    # Anomali limitleri
    max_anomalies_per_session = models.PositiveIntegerField(
        _('Oturum Başına Max. Anomali'),
        default=5,
    )
    
    max_anomalies_per_day = models.PositiveIntegerField(
        _('Günlük Max. Anomali'),
        default=20,
    )
    
    # Otomatik aksiyon
    auto_restrict_threshold = models.PositiveIntegerField(
        _('Otomatik Kısıtlama Eşiği'),
        default=50,
        help_text=_('Bu skorun altına düşerse kısıtla'),
    )
    
    # Kontrol sıklığı (saniye)
    check_interval = models.PositiveIntegerField(
        _('Kontrol Aralığı (sn)'),
        default=30,
    )
    
    # Aktif mi?
    is_enabled = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    
    class Meta:
        verbose_name = _('Bütünlük Yapılandırması')
        verbose_name_plural = _('Bütünlük Yapılandırmaları')
    
    def __str__(self):
        return f"{self.tenant.name} - Bütünlük Ayarları"

