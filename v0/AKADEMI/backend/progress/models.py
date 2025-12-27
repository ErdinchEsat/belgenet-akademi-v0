"""
Progress Models
===============

Video ilerleme takibi için modeller.

NOT: Mevcut courses.ContentProgress modelini genişletmek yerine,
yeni modeller oluşturuyoruz. Migration ile entegre edilecek.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class VideoProgress(TenantAwareModel):
    """
    Video ilerleme durumu.
    
    Mevcut courses.ContentProgress'ten farklı olarak:
    - Session bazlı takip
    - watched_seconds seek-independent
    - Server-side validation
    - Kullanıcı tercihleri (hız, altyazı)
    
    Her (tenant, user, content) için tek kayıt.
    """
    
    # İlişkiler
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name=_('İçerik'),
    )
    
    # İzleme metrikleri
    watched_seconds = models.PositiveIntegerField(
        _('İzlenen Süre (sn)'),
        default=0,
        help_text=_('Seek hariç gerçek izleme süresi'),
    )
    
    last_position_seconds = models.PositiveIntegerField(
        _('Son Pozisyon (sn)'),
        default=0,
        help_text=_('Videonun kaldığı yer'),
    )
    
    # Tamamlanma durumu
    completion_ratio = models.DecimalField(
        _('Tamamlanma Oranı'),
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text=_('0.0000 - 1.0000 arası'),
    )
    
    is_completed = models.BooleanField(
        _('Tamamlandı'),
        default=False,
        db_index=True,
    )
    
    completed_at = models.DateTimeField(
        _('Tamamlanma Tarihi'),
        null=True,
        blank=True,
    )
    
    # Son session bilgisi
    last_session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Son Oturum'),
    )
    
    last_device_id = models.CharField(
        _('Son Cihaz'),
        max_length=255,
        blank=True,
        null=True,
    )
    
    # Kullanıcı tercihleri
    preferred_speed = models.DecimalField(
        _('Tercih Edilen Hız'),
        max_digits=3,
        decimal_places=2,
        default=1.0,
        help_text=_('0.5 - 2.0 arası'),
    )
    
    preferred_caption_lang = models.CharField(
        _('Tercih Edilen Altyazı'),
        max_length=10,
        blank=True,
        null=True,
    )
    
    class Meta:
        verbose_name = _('Video İlerlemesi')
        verbose_name_plural = _('Video İlerlemeleri')
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user', 'content'],
                name='unique_user_content_progress'
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'user', 'course']),
            models.Index(fields=['tenant', 'content', 'is_completed']),
            models.Index(fields=['user', 'is_completed']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.content.title} ({self.completion_ratio:.0%})"
    
    @property
    def content_duration_seconds(self) -> int:
        """İçerik süresi (saniye)."""
        return (self.content.duration_minutes or 0) * 60
    
    def calculate_completion_ratio(self) -> float:
        """Tamamlanma oranını hesapla."""
        duration = self.content_duration_seconds
        if duration <= 0:
            return 0.0
        return min(self.watched_seconds / duration, 1.0)
    
    def update_watched_seconds(self, delta_seconds: int, session=None):
        """
        İzlenen süreyi güncelle.
        
        Args:
            delta_seconds: Eklenen süre (saniye)
            session: Mevcut playback session
        """
        if delta_seconds <= 0:
            return
        
        self.watched_seconds += delta_seconds
        
        # Completion ratio güncelle
        self.completion_ratio = self.calculate_completion_ratio()
        
        # Session bilgisini güncelle
        if session:
            self.last_session = session
            self.last_device_id = session.device_id
        
        # Tamamlanma kontrolü (%80 varsayılan)
        completion_threshold = 0.80  # TODO: Course'dan al
        if not self.is_completed and self.completion_ratio >= completion_threshold:
            self.mark_completed()
        
        self.save()
    
    def mark_completed(self):
        """Tamamlandı olarak işaretle."""
        self.is_completed = True
        self.completed_at = timezone.now()


class ProgressWatchWindow(models.Model):
    """
    İzleme penceresi kaydı.
    
    Seek manipülasyonunu engellemek için contiguous watch window yaklaşımı.
    Her kesintisiz izleme periyodu bir window olarak kaydedilir.
    
    Örnek:
    - Video başladı: 0:00
    - 2:30'a kadar izlendi → Window(0, 150)
    - 5:00'a seek yapıldı
    - 6:00'a kadar izlendi → Window(300, 360)
    
    Toplam watched = 150 + 60 = 210 saniye
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='watch_windows',
        verbose_name=_('Tenant'),
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.CASCADE,
        related_name='watch_windows',
        verbose_name=_('Oturum'),
    )
    
    progress = models.ForeignKey(
        VideoProgress,
        on_delete=models.CASCADE,
        related_name='watch_windows',
        verbose_name=_('İlerleme'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watch_windows',
        verbose_name=_('Kullanıcı'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='watch_windows',
        verbose_name=_('İçerik'),
    )
    
    # Zaman aralığı (video time)
    start_video_ts = models.PositiveIntegerField(
        _('Başlangıç (sn)'),
        help_text=_('Video başlangıç zamanı'),
    )
    
    end_video_ts = models.PositiveIntegerField(
        _('Bitiş (sn)'),
        help_text=_('Video bitiş zamanı'),
    )
    
    # Hesaplanan süre
    duration_seconds = models.PositiveIntegerField(
        _('Süre (sn)'),
        default=0,
    )
    
    # Doğrulama
    is_verified = models.BooleanField(
        _('Doğrulanmış'),
        default=True,
        help_text=_('Server tarafından doğrulandı mı?'),
    )
    
    playback_rate = models.DecimalField(
        _('Oynatma Hızı'),
        max_digits=3,
        decimal_places=2,
        default=1.0,
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    
    class Meta:
        verbose_name = _('İzleme Penceresi')
        verbose_name_plural = _('İzleme Pencereleri')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'session']),
            models.Index(fields=['tenant', 'user', 'content']),
        ]
    
    def __str__(self):
        return f"{self.content.title} [{self.start_video_ts}-{self.end_video_ts}]"
    
    def save(self, *args, **kwargs):
        """Duration'ı otomatik hesapla."""
        self.duration_seconds = max(0, self.end_video_ts - self.start_video_ts)
        super().save(*args, **kwargs)

