"""
Timeline Models
===============

Video üzerinde interaktif overlay node'ları.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class TimelineNode(TenantAwareModel):
    """
    Video timeline üzerinde etkileşim noktası.
    
    Video oynatılırken belirli zamanlarda gösterilen
    interaktif öğeler (quiz, poll, checkpoint, vs.).
    
    Node Types:
    - quiz: Video içi quiz göster (Quiz modeline referans)
    - poll: Hızlı anket
    - checkpoint: "Devam etmek için onayla" noktası
    - hotspot: Tıklanabilir bölge (koordinat bazlı)
    - info: Bilgi kartı (popup/tooltip)
    - cta: Call-to-action butonu
    - chapter: Bölüm işaretçisi
    """
    
    class NodeType(models.TextChoices):
        """Node türleri."""
        QUIZ = 'quiz', _('Quiz')
        POLL = 'poll', _('Anket')
        CHECKPOINT = 'checkpoint', _('Kontrol Noktası')
        HOTSPOT = 'hotspot', _('Tıklanabilir Bölge')
        INFO = 'info', _('Bilgi Kartı')
        CTA = 'cta', _('Aksiyon Butonu')
        CHAPTER = 'chapter', _('Bölüm')
    
    # İlişkiler
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='timeline_nodes',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='timeline_nodes',
        verbose_name=_('İçerik'),
    )
    
    # Node tipi
    node_type = models.CharField(
        _('Node Türü'),
        max_length=20,
        choices=NodeType.choices,
        db_index=True,
    )
    
    # Zamanlama
    start_ts = models.PositiveIntegerField(
        _('Başlangıç (sn)'),
        help_text=_('Node\'un gösterileceği video zamanı'),
        db_index=True,
    )
    
    end_ts = models.PositiveIntegerField(
        _('Bitiş (sn)'),
        null=True,
        blank=True,
        help_text=_('Node\'un gizleneceği zaman (opsiyonel)'),
    )
    
    # Node başlığı (UI'da gösterilir)
    title = models.CharField(
        _('Başlık'),
        max_length=200,
        blank=True,
    )
    
    # Node konfigürasyonu (tip'e göre değişir)
    config = models.JSONField(
        _('Konfigürasyon'),
        default=dict,
        help_text=_('Node türüne göre değişen ayarlar'),
    )
    """
    Config örnekleri:
    
    quiz:
    {
        "quiz_id": "uuid",
        "blocking": true,  // Video durdurulsun mu?
        "skip_allowed": false
    }
    
    poll:
    {
        "question": "Bu konuyu anladınız mı?",
        "options": ["Evet", "Hayır", "Kısmen"],
        "blocking": false
    }
    
    checkpoint:
    {
        "label": "Devam etmek için tıklayın",
        "blocking": true,
        "require_confirmation": true
    }
    
    hotspot:
    {
        "x": 0.25,  // % koordinat
        "y": 0.50,
        "width": 0.1,
        "height": 0.1,
        "action": "link",
        "action_data": {"url": "..."}
    }
    
    info:
    {
        "content": "Bu önemli bir bilgidir...",
        "position": "bottom-right",
        "auto_hide": 5  // saniye
    }
    
    cta:
    {
        "label": "Kaynağa Git",
        "action": "link",
        "url": "https://...",
        "style": "primary"
    }
    
    chapter:
    {
        "label": "Bölüm 2: İleri Konular"
    }
    """
    
    # Davranış ayarları
    is_blocking = models.BooleanField(
        _('Engelleyici'),
        default=False,
        help_text=_('Video durdurulup etkileşim beklenir mi?'),
    )
    
    is_required = models.BooleanField(
        _('Zorunlu'),
        default=False,
        help_text=_('İlerlemek için tamamlanması zorunlu mu?'),
    )
    
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    
    # Sıralama (aynı zamanda birden fazla node için)
    order = models.PositiveIntegerField(
        _('Sıra'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('Timeline Node')
        verbose_name_plural = _('Timeline Nodes')
        ordering = ['start_ts', 'order']
        indexes = [
            models.Index(fields=['tenant', 'content', 'start_ts']),
            models.Index(fields=['tenant', 'content', 'node_type']),
            models.Index(fields=['content', 'is_active', 'start_ts']),
        ]
    
    def __str__(self):
        return f"{self.get_node_type_display()} @ {self.start_ts}s - {self.content.title}"
    
    @property
    def duration(self) -> int:
        """Node görünme süresi (saniye)."""
        if self.end_ts:
            return self.end_ts - self.start_ts
        return 0


class TimelineNodeInteraction(TenantAwareModel):
    """
    Kullanıcının timeline node ile etkileşimi.
    
    Checkpoint onayı, poll cevabı, hotspot tıklaması gibi
    etkileşimleri kaydeder.
    """
    
    class InteractionType(models.TextChoices):
        """Etkileşim türleri."""
        VIEWED = 'viewed', _('Görüntülendi')
        CLICKED = 'clicked', _('Tıklandı')
        COMPLETED = 'completed', _('Tamamlandı')
        SKIPPED = 'skipped', _('Atlandı')
        ANSWERED = 'answered', _('Cevaplandı')
    
    node = models.ForeignKey(
        TimelineNode,
        on_delete=models.CASCADE,
        related_name='interactions',
        verbose_name=_('Node'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timeline_interactions',
        verbose_name=_('Kullanıcı'),
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_interactions',
        verbose_name=_('Oturum'),
    )
    
    interaction_type = models.CharField(
        _('Etkileşim Türü'),
        max_length=20,
        choices=InteractionType.choices,
    )
    
    # Etkileşim verisi (poll cevabı vs.)
    data = models.JSONField(
        _('Veri'),
        default=dict,
        blank=True,
    )
    
    # Video zamanı (etkileşim anında)
    video_ts = models.PositiveIntegerField(
        _('Video Zamanı'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Node Etkileşimi')
        verbose_name_plural = _('Node Etkileşimleri')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'node']),
            models.Index(fields=['node', 'interaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.node} ({self.interaction_type})"

