"""
Telemetry Models
================

Video oynatıcı event tracking modelleri.
Append-only yapıda, yüksek hacimli yazma için optimize edilmiş.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TelemetryEvent(models.Model):
    """
    Video oynatıcı olayı.
    
    Append-only tablo - güncelleme yapılmaz.
    Yüksek hacimli yazma için optimize edilmiş.
    
    Event Types:
    - play: Oynatma başladı
    - pause: Durduruldu
    - seek: Atlama yapıldı
    - seeked: Atlama tamamlandı
    - timeupdate: Zaman güncellendi (her X saniyede)
    - ended: Video bitti
    - rate_change: Hız değişti
    - fullscreen: Tam ekran
    - pip: Picture-in-Picture
    - buffer_start: Buffering başladı
    - buffer_end: Buffering bitti
    - error: Hata oluştu
    - quality_change: Kalite değişti
    """
    
    class EventType(models.TextChoices):
        """Event türleri."""
        PLAY = 'play', _('Oynat')
        PAUSE = 'pause', _('Durdur')
        SEEK = 'seek', _('Atla')
        SEEKED = 'seeked', _('Atlama Tamamlandı')
        TIMEUPDATE = 'timeupdate', _('Zaman Güncelleme')
        ENDED = 'ended', _('Bitti')
        RATE_CHANGE = 'rate_change', _('Hız Değişimi')
        FULLSCREEN = 'fullscreen', _('Tam Ekran')
        PIP = 'pip', _('Picture-in-Picture')
        BUFFER_START = 'buffer_start', _('Buffer Başladı')
        BUFFER_END = 'buffer_end', _('Buffer Bitti')
        ERROR = 'error', _('Hata')
        QUALITY_CHANGE = 'quality_change', _('Kalite Değişimi')
        VISIBILITY_CHANGE = 'visibility_change', _('Görünürlük Değişimi')
        VOLUME_CHANGE = 'volume_change', _('Ses Değişimi')
        CAPTION_CHANGE = 'caption_change', _('Altyazı Değişimi')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # Tenant ve ilişkiler
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='telemetry_events',
        verbose_name=_('Tenant'),
        db_index=True,
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.CASCADE,
        related_name='telemetry_events',
        verbose_name=_('Oturum'),
        db_index=True,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telemetry_events',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='telemetry_events',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='telemetry_events',
        verbose_name=_('İçerik'),
        db_index=True,
    )
    
    # Dedupe key - client tarafından üretilir
    client_event_id = models.CharField(
        _('Client Event ID'),
        max_length=100,
        help_text=_('Client tarafından üretilen benzersiz event ID'),
    )
    
    # Event bilgileri
    event_type = models.CharField(
        _('Event Türü'),
        max_length=30,
        choices=EventType.choices,
        db_index=True,
    )
    
    # Video zaman bilgisi
    video_ts = models.PositiveIntegerField(
        _('Video Zamanı (sn)'),
        null=True,
        blank=True,
        help_text=_('Event anındaki video pozisyonu'),
    )
    
    # Zaman damgaları
    server_ts = models.DateTimeField(
        _('Server Zamanı'),
        default=timezone.now,
        db_index=True,
    )
    
    client_ts = models.DateTimeField(
        _('Client Zamanı'),
        null=True,
        blank=True,
    )
    
    # Ek veri
    payload = models.JSONField(
        _('Payload'),
        null=True,
        blank=True,
        help_text=_('Event\'e özgü ek veriler'),
    )
    
    class Meta:
        verbose_name = _('Telemetry Event')
        verbose_name_plural = _('Telemetry Events')
        ordering = ['-server_ts']
        
        # Dedupe constraint
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'session', 'client_event_id'],
                name='unique_telemetry_event'
            )
        ]
        
        indexes = [
            # Session bazlı sorgular
            models.Index(fields=['session', '-server_ts']),
            # Content analytics
            models.Index(fields=['tenant', 'content', 'event_type', '-server_ts']),
            # User analytics
            models.Index(fields=['tenant', 'user', '-server_ts']),
            # Event type bazlı
            models.Index(fields=['tenant', 'event_type', '-server_ts']),
        ]
    
    def __str__(self):
        return f"{self.event_type} @ {self.video_ts}s ({self.session_id})"


class TelemetryAggregate(models.Model):
    """
    Telemetry özet metrikleri.
    
    Periyodik olarak hesaplanan özet veriler.
    Heatmap, drop-off analizi vs. için kullanılır.
    
    NOT: Bu tablo Celery task'ları ile doldurulur.
    """
    
    class AggregateType(models.TextChoices):
        """Özet türleri."""
        HEATMAP = 'heatmap', _('Isı Haritası')
        DROPOFF = 'dropoff', _('Drop-off')
        REWIND = 'rewind', _('Geri Sarma')
        SKIP = 'skip', _('Atlama')
        ENGAGEMENT = 'engagement', _('Etkileşim')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='telemetry_aggregates',
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='telemetry_aggregates',
    )
    
    aggregate_type = models.CharField(
        _('Özet Türü'),
        max_length=20,
        choices=AggregateType.choices,
    )
    
    # Zaman aralığı
    period_start = models.DateTimeField(_('Dönem Başlangıcı'))
    period_end = models.DateTimeField(_('Dönem Bitişi'))
    
    # Özet verileri
    data = models.JSONField(
        _('Özet Verisi'),
        default=dict,
        help_text=_('Türe göre değişen özet verileri'),
    )
    
    # Örnek count
    sample_count = models.PositiveIntegerField(
        _('Örnek Sayısı'),
        default=0,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Telemetry Özeti')
        verbose_name_plural = _('Telemetry Özetleri')
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['tenant', 'content', 'aggregate_type']),
        ]
    
    def __str__(self):
        return f"{self.aggregate_type} - {self.content.title}"

