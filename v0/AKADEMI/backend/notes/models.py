"""
Notes Models
============

Video üzerinde zamanlı notlar ve threads.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class VideoNote(TenantAwareModel):
    """
    Video üzerinde zamanlı not.
    
    Kullanıcı videoyu izlerken aldığı notlar.
    Video'nun belirli bir anına bağlı olabilir.
    Paylaşılabilir veya özel olabilir.
    """
    
    class NoteVisibility(models.TextChoices):
        """Not görünürlük seçenekleri."""
        PRIVATE = 'private', _('Özel')
        GROUP = 'group', _('Grup')  # Aynı kursta olanlar
        PUBLIC = 'public', _('Herkese Açık')
    
    class NoteType(models.TextChoices):
        """Not türleri."""
        NOTE = 'note', _('Not')
        QUESTION = 'question', _('Soru')
        HIGHLIGHT = 'highlight', _('Önemli')
        BOOKMARK = 'bookmark', _('Yer İşareti')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # İlişkiler
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_notes',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name=_('İçerik'),
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name=_('Oturum'),
    )
    
    # Not içeriği
    note_type = models.CharField(
        _('Not Türü'),
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.NOTE,
    )
    
    content_text = models.TextField(
        _('İçerik'),
        blank=True,
    )
    
    # Video zamanı
    video_ts = models.PositiveIntegerField(
        _('Video Zamanı (sn)'),
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Notun ilişkili olduğu video zamanı'),
    )
    
    video_ts_end = models.PositiveIntegerField(
        _('Bitiş Zamanı (sn)'),
        null=True,
        blank=True,
        help_text=_('Highlight için bitiş zamanı'),
    )
    
    # Görünürlük
    visibility = models.CharField(
        _('Görünürlük'),
        max_length=20,
        choices=NoteVisibility.choices,
        default=NoteVisibility.PRIVATE,
    )
    
    # Paylaşım linki
    share_token = models.CharField(
        _('Paylaşım Tokeni'),
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )
    
    # Metadata
    color = models.CharField(
        _('Renk'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Highlight/not rengi (hex)'),
    )
    
    tags = models.JSONField(
        _('Etiketler'),
        default=list,
        blank=True,
    )
    
    # Pinned
    is_pinned = models.BooleanField(
        _('Sabitlenmiş'),
        default=False,
    )
    
    # Sayaçlar (denormalize)
    reply_count = models.PositiveIntegerField(
        _('Cevap Sayısı'),
        default=0,
    )
    
    like_count = models.PositiveIntegerField(
        _('Beğeni Sayısı'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('Video Notu')
        verbose_name_plural = _('Video Notları')
        ordering = ['video_ts', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'content']),
            models.Index(fields=['content', 'visibility', 'video_ts']),
            models.Index(fields=['tenant', 'course', 'visibility']),
        ]
    
    def __str__(self):
        ts = f"@{self.video_ts}s" if self.video_ts else ""
        return f"{self.user.email} - {self.content.title} {ts}"
    
    @property
    def time_display(self) -> str:
        """Video zamanını okunabilir formata çevir."""
        if self.video_ts is None:
            return ""
        mins, secs = divmod(self.video_ts, 60)
        return f"{mins}:{secs:02d}"


class NoteReply(TenantAwareModel):
    """
    Not altındaki thread cevabı.
    
    Bir nota verilen yanıtlar zinciri.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    note = models.ForeignKey(
        VideoNote,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name=_('Not'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_replies',
        verbose_name=_('Kullanıcı'),
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Üst Cevap'),
    )
    
    content_text = models.TextField(
        _('İçerik'),
    )
    
    # Sayaçlar
    like_count = models.PositiveIntegerField(
        _('Beğeni Sayısı'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('Not Cevabı')
        verbose_name_plural = _('Not Cevapları')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['note', 'created_at']),
        ]
    
    def __str__(self):
        return f"Reply by {self.user.email} on {self.note.id}"


class NoteReaction(TenantAwareModel):
    """
    Not veya cevap reaksiyonu.
    
    Like, bookmark gibi etkileşimler.
    """
    
    class ReactionType(models.TextChoices):
        """Reaksiyon türleri."""
        LIKE = 'like', _('Beğeni')
        BOOKMARK = 'bookmark', _('Yer İşareti')
        HELPFUL = 'helpful', _('Yardımcı')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_reactions',
        verbose_name=_('Kullanıcı'),
    )
    
    # Note veya Reply'a reaksiyon
    note = models.ForeignKey(
        VideoNote,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reactions',
        verbose_name=_('Not'),
    )
    
    reply = models.ForeignKey(
        NoteReply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reactions',
        verbose_name=_('Cevap'),
    )
    
    reaction_type = models.CharField(
        _('Reaksiyon'),
        max_length=20,
        choices=ReactionType.choices,
    )
    
    class Meta:
        verbose_name = _('Not Reaksiyonu')
        verbose_name_plural = _('Not Reaksiyonları')
        constraints = [
            # Bir kullanıcı aynı note'a aynı reaksiyonu bir kez verebilir
            models.UniqueConstraint(
                fields=['user', 'note', 'reaction_type'],
                name='unique_note_reaction',
                condition=models.Q(note__isnull=False),
            ),
            # Bir kullanıcı aynı reply'a aynı reaksiyonu bir kez verebilir
            models.UniqueConstraint(
                fields=['user', 'reply', 'reaction_type'],
                name='unique_reply_reaction',
                condition=models.Q(reply__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'note']),
            models.Index(fields=['user', 'reply']),
        ]
    
    def __str__(self):
        target = self.note or self.reply
        return f"{self.user.email} - {self.reaction_type} on {target}"


class NoteExport(TenantAwareModel):
    """
    Not dışa aktarma talebi.
    
    Kullanıcı notlarını PDF/MD olarak dışa aktarabilir.
    """
    
    class ExportFormat(models.TextChoices):
        """Dışa aktarma formatları."""
        PDF = 'pdf', _('PDF')
        MARKDOWN = 'markdown', _('Markdown')
        HTML = 'html', _('HTML')
    
    class ExportStatus(models.TextChoices):
        """Dışa aktarma durumları."""
        PENDING = 'pending', _('Beklemede')
        PROCESSING = 'processing', _('İşleniyor')
        COMPLETED = 'completed', _('Tamamlandı')
        FAILED = 'failed', _('Başarısız')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_exports',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='note_exports',
        verbose_name=_('Kurs'),
    )
    
    format = models.CharField(
        _('Format'),
        max_length=20,
        choices=ExportFormat.choices,
        default=ExportFormat.PDF,
    )
    
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
    )
    
    file_url = models.URLField(
        _('Dosya URL'),
        blank=True,
        null=True,
    )
    
    error_message = models.TextField(
        _('Hata Mesajı'),
        blank=True,
        null=True,
    )
    
    completed_at = models.DateTimeField(
        _('Tamamlanma Zamanı'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Not Dışa Aktarma')
        verbose_name_plural = _('Not Dışa Aktarmaları')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.format} export ({self.status})"

