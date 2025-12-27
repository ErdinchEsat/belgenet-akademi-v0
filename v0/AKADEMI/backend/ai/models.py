"""
AI Models
=========

Video tabanlı AI özellikleri modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class Transcript(TenantAwareModel):
    """
    Video transkripti.
    
    Video için otomatik veya manuel oluşturulan transkript.
    Birden fazla dil destekler.
    """
    
    class TranscriptStatus(models.TextChoices):
        """Transkript durumları."""
        PENDING = 'pending', _('Beklemede')
        PROCESSING = 'processing', _('İşleniyor')
        COMPLETED = 'completed', _('Tamamlandı')
        FAILED = 'failed', _('Başarısız')
    
    class TranscriptSource(models.TextChoices):
        """Transkript kaynakları."""
        AUTO = 'auto', _('Otomatik (AI)')
        MANUAL = 'manual', _('Manuel')
        IMPORTED = 'imported', _('İçe Aktarılmış')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # İlişkiler
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='transcripts',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='transcripts',
        verbose_name=_('İçerik'),
    )
    
    # Dil
    language = models.CharField(
        _('Dil'),
        max_length=10,
        default='tr',
        db_index=True,
    )
    
    # Kaynak ve durum
    source = models.CharField(
        _('Kaynak'),
        max_length=20,
        choices=TranscriptSource.choices,
        default=TranscriptSource.AUTO,
    )
    
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=TranscriptStatus.choices,
        default=TranscriptStatus.PENDING,
    )
    
    # Raw content (SRT/VTT)
    raw_content = models.TextField(
        _('Ham İçerik'),
        blank=True,
    )
    
    # Full text (düz metin, arama için)
    full_text = models.TextField(
        _('Tam Metin'),
        blank=True,
        db_index=True,
    )
    
    # Meta
    word_count = models.PositiveIntegerField(
        _('Kelime Sayısı'),
        default=0,
    )
    
    segment_count = models.PositiveIntegerField(
        _('Segment Sayısı'),
        default=0,
    )
    
    duration_seconds = models.PositiveIntegerField(
        _('Süre (sn)'),
        default=0,
    )
    
    error_message = models.TextField(
        _('Hata Mesajı'),
        blank=True,
        null=True,
    )
    
    class Meta:
        verbose_name = _('Transkript')
        verbose_name_plural = _('Transkriptler')
        unique_together = ['content', 'language']
        indexes = [
            models.Index(fields=['tenant', 'content', 'language']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.content.title} - {self.language} ({self.status})"


class TranscriptSegment(models.Model):
    """
    Transkript segmenti.
    
    Video'nun belirli bir zaman aralığındaki metin.
    Full-text arama ve zaman navigasyonu için kullanılır.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name='segments',
        verbose_name=_('Transkript'),
    )
    
    # Zamanlama
    start_ts = models.FloatField(
        _('Başlangıç (sn)'),
        db_index=True,
    )
    
    end_ts = models.FloatField(
        _('Bitiş (sn)'),
    )
    
    # Metin
    text = models.TextField(
        _('Metin'),
    )
    
    # Sıra numarası
    sequence = models.PositiveIntegerField(
        _('Sıra'),
        db_index=True,
    )
    
    # Speaker (varsa)
    speaker = models.CharField(
        _('Konuşmacı'),
        max_length=100,
        blank=True,
        null=True,
    )
    
    # Confidence score (AI için)
    confidence = models.FloatField(
        _('Güven Skoru'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Transkript Segmenti')
        verbose_name_plural = _('Transkript Segmentleri')
        ordering = ['sequence']
        indexes = [
            models.Index(fields=['transcript', 'start_ts']),
        ]
    
    def __str__(self):
        return f"{self.start_ts:.1f}s: {self.text[:50]}..."


class AIConversation(TenantAwareModel):
    """
    AI tutor konuşması.
    
    Kullanıcı ve AI tutor arasındaki konuşma oturumu.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_conversations',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_conversations',
        verbose_name=_('İçerik'),
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_conversations',
        verbose_name=_('Oturum'),
    )
    
    # Konuşma başlığı
    title = models.CharField(
        _('Başlık'),
        max_length=200,
        blank=True,
    )
    
    # Context (soru sorulduğu andaki video zamanı, not, vs.)
    context = models.JSONField(
        _('Bağlam'),
        default=dict,
        blank=True,
    )
    """
    Context örneği:
    {
        "video_ts": 120,
        "transcript_segment": "...",
        "related_note_id": "uuid",
        "quiz_question_id": "uuid"
    }
    """
    
    # Mesaj sayısı (denormalize)
    message_count = models.PositiveIntegerField(
        _('Mesaj Sayısı'),
        default=0,
    )
    
    # Son aktivite
    last_activity_at = models.DateTimeField(
        _('Son Aktivite'),
        auto_now=True,
    )
    
    class Meta:
        verbose_name = _('AI Konuşması')
        verbose_name_plural = _('AI Konuşmaları')
        ordering = ['-last_activity_at']
        indexes = [
            models.Index(fields=['tenant', 'user', '-last_activity_at']),
            models.Index(fields=['content', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title or 'Conversation'}"


class AIMessage(models.Model):
    """
    AI konuşma mesajı.
    """
    
    class MessageRole(models.TextChoices):
        """Mesaj rolleri."""
        USER = 'user', _('Kullanıcı')
        ASSISTANT = 'assistant', _('Asistan')
        SYSTEM = 'system', _('Sistem')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Konuşma'),
    )
    
    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=MessageRole.choices,
    )
    
    content = models.TextField(
        _('İçerik'),
    )
    
    # Video zamanı (varsa)
    video_ts = models.PositiveIntegerField(
        _('Video Zamanı'),
        null=True,
        blank=True,
    )
    
    # Kaynak bilgisi (RAG için)
    sources = models.JSONField(
        _('Kaynaklar'),
        default=list,
        blank=True,
    )
    """
    Sources örneği:
    [
        {"type": "transcript", "segment_id": "uuid", "relevance": 0.85},
        {"type": "note", "note_id": "uuid", "relevance": 0.75},
        {"type": "course_material", "content_id": 123}
    ]
    """
    
    # Token kullanımı
    tokens_used = models.PositiveIntegerField(
        _('Token Kullanımı'),
        default=0,
    )
    
    # Model bilgisi
    model_used = models.CharField(
        _('Model'),
        max_length=50,
        blank=True,
        null=True,
    )
    
    created_at = models.DateTimeField(
        _('Oluşturulma'),
        auto_now_add=True,
    )
    
    class Meta:
        verbose_name = _('AI Mesajı')
        verbose_name_plural = _('AI Mesajları')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class VideoSummary(TenantAwareModel):
    """
    AI tarafından oluşturulan video özeti.
    """
    
    class SummaryType(models.TextChoices):
        """Özet türleri."""
        BRIEF = 'brief', _('Kısa Özet')
        DETAILED = 'detailed', _('Detaylı Özet')
        BULLET_POINTS = 'bullet_points', _('Madde Madde')
        KEY_TAKEAWAYS = 'key_takeaways', _('Önemli Noktalar')
        CHAPTER = 'chapter', _('Bölüm Özeti')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='summaries',
        verbose_name=_('İçerik'),
    )
    
    summary_type = models.CharField(
        _('Özet Türü'),
        max_length=20,
        choices=SummaryType.choices,
        default=SummaryType.BRIEF,
    )
    
    language = models.CharField(
        _('Dil'),
        max_length=10,
        default='tr',
    )
    
    # Özet içeriği
    summary_text = models.TextField(
        _('Özet'),
    )
    
    # Bölüm özeti için zaman aralığı
    start_ts = models.PositiveIntegerField(
        _('Başlangıç'),
        null=True,
        blank=True,
    )
    
    end_ts = models.PositiveIntegerField(
        _('Bitiş'),
        null=True,
        blank=True,
    )
    
    # Oluşturan model
    model_used = models.CharField(
        _('Model'),
        max_length=50,
        blank=True,
    )
    
    tokens_used = models.PositiveIntegerField(
        _('Token Kullanımı'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('Video Özeti')
        verbose_name_plural = _('Video Özetleri')
        indexes = [
            models.Index(fields=['content', 'summary_type', 'language']),
        ]
    
    def __str__(self):
        return f"{self.content.title} - {self.get_summary_type_display()}"


class AIQuota(TenantAwareModel):
    """
    AI kullanım kotası.
    
    Kullanıcı/tenant bazında AI kullanım limitleri.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_quota',
        verbose_name=_('Kullanıcı'),
    )
    
    # Günlük limitler
    daily_questions_limit = models.PositiveIntegerField(
        _('Günlük Soru Limiti'),
        default=50,
    )
    
    daily_questions_used = models.PositiveIntegerField(
        _('Günlük Kullanılan'),
        default=0,
    )
    
    # Aylık token limiti
    monthly_tokens_limit = models.PositiveIntegerField(
        _('Aylık Token Limiti'),
        default=100000,
    )
    
    monthly_tokens_used = models.PositiveIntegerField(
        _('Aylık Token Kullanımı'),
        default=0,
    )
    
    # Reset tarihleri
    daily_reset_at = models.DateTimeField(
        _('Günlük Reset'),
        null=True,
        blank=True,
    )
    
    monthly_reset_at = models.DateTimeField(
        _('Aylık Reset'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('AI Kotası')
        verbose_name_plural = _('AI Kotaları')
    
    def __str__(self):
        return f"{self.user.email} - AI Quota"
    
    @property
    def can_ask_question(self) -> bool:
        """Kullanıcı soru sorabilir mi?"""
        return self.daily_questions_used < self.daily_questions_limit
    
    @property
    def remaining_questions(self) -> int:
        """Kalan soru hakkı."""
        return max(0, self.daily_questions_limit - self.daily_questions_used)

