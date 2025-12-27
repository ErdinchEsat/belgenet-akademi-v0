"""
Player Models
=============

Playback session yönetimi için modeller.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class PlaybackSession(TenantAwareModel):
    """
    Video izleme oturumu.
    
    Her kullanıcı bir içeriği izlemeye başladığında yeni bir session oluşturulur.
    Session üzerinden progress tracking ve telemetry event'leri bağlanır.
    
    Lifecycle:
    1. POST /sessions/ → Session oluştur, resume bilgisini döndür
    2. PUT /sessions/{id}/heartbeat/ → Her 30 saniyede bir heartbeat
    3. PUT /sessions/{id}/end/ → Video bittiğinde veya sayfa kapanırken
    """
    
    class EndReason(models.TextChoices):
        """Oturum sonlanma nedenleri."""
        ENDED = 'ended', _('Video Bitti')
        PAUSED = 'paused', _('Durduruldu')
        TIMEOUT = 'timeout', _('Zaman Aşımı')
        LOGOUT = 'logout', _('Çıkış Yapıldı')
        ERROR = 'error', _('Hata')
        NAVIGATION = 'navigation', _('Sayfa Değişikliği')
    
    # İlişkiler
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playback_sessions',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='playback_sessions',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='playback_sessions',
        verbose_name=_('İçerik'),
    )
    
    # Cihaz bilgileri
    device_id = models.CharField(
        _('Cihaz ID'),
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=_('Client tarafından üretilen benzersiz cihaz tanımlayıcı'),
    )
    
    user_agent = models.TextField(
        _('User Agent'),
        blank=True,
        null=True,
    )
    
    ip_hash = models.CharField(
        _('IP Hash'),
        max_length=64,
        blank=True,
        null=True,
        help_text=_('GDPR uyumu için hash\'lenmiş IP'),
    )
    
    # Zamanlama
    started_at = models.DateTimeField(
        _('Başlangıç'),
        default=timezone.now,
        db_index=True,
    )
    
    ended_at = models.DateTimeField(
        _('Bitiş'),
        null=True,
        blank=True,
    )
    
    ended_reason = models.CharField(
        _('Bitiş Nedeni'),
        max_length=20,
        choices=EndReason.choices,
        blank=True,
        null=True,
    )
    
    last_heartbeat_at = models.DateTimeField(
        _('Son Heartbeat'),
        null=True,
        blank=True,
        help_text=_('Client\'ın son yaşam sinyali'),
    )
    
    # Session durumu
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
        db_index=True,
    )
    
    # Son izleme pozisyonu (heartbeat ile güncellenir)
    last_position_seconds = models.PositiveIntegerField(
        _('Son Pozisyon (sn)'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('İzleme Oturumu')
        verbose_name_plural = _('İzleme Oturumları')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'content', '-started_at']),
            models.Index(fields=['tenant', 'is_active', '-started_at']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.content.title} ({self.started_at})"
    
    @property
    def duration_seconds(self) -> int:
        """Oturum süresi (saniye)."""
        end = self.ended_at or timezone.now()
        return int((end - self.started_at).total_seconds())
    
    @property
    def is_stale(self) -> bool:
        """Oturum timeout olmuş mu? (5 dakika heartbeat yoksa)."""
        if not self.last_heartbeat_at:
            return False
        stale_threshold = timezone.now() - timezone.timedelta(minutes=5)
        return self.last_heartbeat_at < stale_threshold
    
    def end_session(self, reason: str = None):
        """Oturumu sonlandır."""
        self.is_active = False
        self.ended_at = timezone.now()
        self.ended_reason = reason or self.EndReason.ENDED
        self.save(update_fields=['is_active', 'ended_at', 'ended_reason', 'updated_at'])
    
    def heartbeat(self, position_seconds: int = None):
        """Heartbeat güncelle."""
        self.last_heartbeat_at = timezone.now()
        if position_seconds is not None:
            self.last_position_seconds = position_seconds
        self.save(update_fields=['last_heartbeat_at', 'last_position_seconds', 'updated_at'])
    
    @classmethod
    def get_active_session(cls, user, content):
        """Kullanıcının bu içerik için aktif session'ını getir."""
        return cls.objects.filter(
            user=user,
            content=content,
            is_active=True,
        ).order_by('-started_at').first()
    
    @classmethod
    def close_stale_sessions(cls, user, content):
        """Kullanıcının bu içerik için eski session'larını kapat."""
        cls.objects.filter(
            user=user,
            content=content,
            is_active=True,
        ).update(
            is_active=False,
            ended_at=timezone.now(),
            ended_reason=cls.EndReason.TIMEOUT,
        )

