"""
Recommendations Models
======================

Kişiselleştirilmiş öneri sistemi modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class UserContentInterest(TenantAwareModel):
    """
    Kullanıcı içerik ilgi profili.
    
    Kullanıcının hangi konu/kategori/eğitmene ilgi duyduğunu izler.
    ML modeli için feature store görevi görür.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_interests',
        verbose_name=_('Kullanıcı'),
    )
    
    # İlgi alanları (kategori/tag bazlı)
    category_scores = models.JSONField(
        _('Kategori Skorları'),
        default=dict,
        help_text=_('{"kategori_id": skor, ...}'),
    )
    
    tag_scores = models.JSONField(
        _('Etiket Skorları'),
        default=dict,
        help_text=_('{"tag": skor, ...}'),
    )
    
    instructor_scores = models.JSONField(
        _('Eğitmen Skorları'),
        default=dict,
        help_text=_('{"instructor_id": skor, ...}'),
    )
    
    # Tercih edilen içerik özellikleri
    preferred_duration = models.CharField(
        _('Tercih Edilen Süre'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('short (<10dk), medium (10-30dk), long (>30dk)'),
    )
    
    preferred_difficulty = models.CharField(
        _('Tercih Edilen Zorluk'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('beginner, intermediate, advanced'),
    )
    
    # Aktif öğrenme saatleri
    active_hours = models.JSONField(
        _('Aktif Saatler'),
        default=dict,
        help_text=_('{"saat": kullanım_sayısı, ...}'),
    )
    
    # İstatistikler
    total_watch_time = models.PositiveIntegerField(
        _('Toplam İzleme Süresi (dk)'),
        default=0,
    )
    
    total_completions = models.PositiveIntegerField(
        _('Toplam Tamamlama'),
        default=0,
    )
    
    avg_completion_rate = models.FloatField(
        _('Ortalama Tamamlama Oranı'),
        default=0.0,
    )
    
    last_activity_at = models.DateTimeField(
        _('Son Aktivite'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Kullanıcı İlgi Profili')
        verbose_name_plural = _('Kullanıcı İlgi Profilleri')
        unique_together = ['tenant', 'user']
        indexes = [
            models.Index(fields=['tenant', 'user']),
            models.Index(fields=['last_activity_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - İlgi Profili"


class ContentSimilarity(models.Model):
    """
    İçerik benzerlik matrisi.
    
    İçerikler arası benzerlik skorlarını saklar.
    Pre-computed olarak ML pipeline tarafından güncellenir.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    content_a = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='similarities_as_a',
        verbose_name=_('İçerik A'),
    )
    
    content_b = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='similarities_as_b',
        verbose_name=_('İçerik B'),
    )
    
    # Benzerlik skoru (0-1 arası)
    similarity_score = models.FloatField(
        _('Benzerlik Skoru'),
        db_index=True,
    )
    
    # Benzerlik tipi
    similarity_type = models.CharField(
        _('Benzerlik Tipi'),
        max_length=50,
        default='content_based',
        help_text=_('content_based, collaborative, hybrid'),
    )
    
    # Son hesaplama zamanı
    computed_at = models.DateTimeField(
        _('Hesaplama Zamanı'),
        auto_now=True,
    )
    
    class Meta:
        verbose_name = _('İçerik Benzerliği')
        verbose_name_plural = _('İçerik Benzerlikleri')
        unique_together = ['content_a', 'content_b', 'similarity_type']
        indexes = [
            models.Index(fields=['content_a', 'similarity_score']),
            models.Index(fields=['content_b', 'similarity_score']),
        ]
    
    def __str__(self):
        return f"{self.content_a.title} ↔ {self.content_b.title}: {self.similarity_score:.2f}"


class Recommendation(TenantAwareModel):
    """
    Kullanıcıya yapılan öneri.
    
    Öneri geçmişi ve performans takibi için kullanılır.
    """
    
    class RecommendationType(models.TextChoices):
        """Öneri türleri."""
        PERSONALIZED = 'personalized', _('Kişiselleştirilmiş')
        SIMILAR = 'similar', _('Benzer İçerik')
        TRENDING = 'trending', _('Trend')
        NEXT = 'next', _('Sonraki Önerilen')
        CONTINUE = 'continue', _('Devam Et')
        NEW = 'new', _('Yeni İçerik')
    
    class RecommendationStatus(models.TextChoices):
        """Öneri durumları."""
        SHOWN = 'shown', _('Gösterildi')
        CLICKED = 'clicked', _('Tıklandı')
        STARTED = 'started', _('Başlandı')
        COMPLETED = 'completed', _('Tamamlandı')
        DISMISSED = 'dismissed', _('Reddedildi')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name=_('Kullanıcı'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name=_('İçerik'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name=_('Kurs'),
    )
    
    # Öneri bilgileri
    recommendation_type = models.CharField(
        _('Öneri Türü'),
        max_length=20,
        choices=RecommendationType.choices,
    )
    
    score = models.FloatField(
        _('Öneri Skoru'),
        help_text=_('Model tarafından hesaplanan skor'),
    )
    
    rank = models.PositiveIntegerField(
        _('Sıra'),
        help_text=_('Öneri listesindeki sıra'),
    )
    
    reason = models.TextField(
        _('Öneri Nedeni'),
        blank=True,
        help_text=_('Kullanıcıya gösterilebilir açıklama'),
    )
    
    # Model bilgisi
    model_version = models.CharField(
        _('Model Versiyonu'),
        max_length=50,
        blank=True,
    )
    
    # Context (önerinin yapıldığı bağlam)
    context = models.JSONField(
        _('Bağlam'),
        default=dict,
        blank=True,
    )
    """
    Context örneği:
    {
        "source_content_id": 123,  # Benzer öneri için kaynak
        "session_id": "uuid",
        "page": "course_detail",
        "position": "sidebar"
    }
    """
    
    # Durum
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=RecommendationStatus.choices,
        default=RecommendationStatus.SHOWN,
    )
    
    # Zaman bilgileri
    shown_at = models.DateTimeField(
        _('Gösterilme Zamanı'),
        auto_now_add=True,
    )
    
    clicked_at = models.DateTimeField(
        _('Tıklanma Zamanı'),
        null=True,
        blank=True,
    )
    
    completed_at = models.DateTimeField(
        _('Tamamlanma Zamanı'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Öneri')
        verbose_name_plural = _('Öneriler')
        ordering = ['-shown_at']
        indexes = [
            models.Index(fields=['tenant', 'user', '-shown_at']),
            models.Index(fields=['tenant', 'user', 'recommendation_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.content.title} ({self.recommendation_type})"


class RecommendationFeedback(TenantAwareModel):
    """
    Öneri geri bildirimi.
    
    Kullanıcının öneriye verdiği açık geri bildirim.
    Model iyileştirmesi için kullanılır.
    """
    
    class FeedbackType(models.TextChoices):
        """Geri bildirim türleri."""
        HELPFUL = 'helpful', _('Faydalı')
        NOT_HELPFUL = 'not_helpful', _('Faydalı Değil')
        NOT_INTERESTED = 'not_interested', _('İlgilenmiyorum')
        ALREADY_KNOW = 'already_know', _('Zaten Biliyorum')
        TOO_EASY = 'too_easy', _('Çok Kolay')
        TOO_HARD = 'too_hard', _('Çok Zor')
        WRONG_TOPIC = 'wrong_topic', _('Yanlış Konu')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        verbose_name=_('Öneri'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_feedbacks',
        verbose_name=_('Kullanıcı'),
    )
    
    feedback_type = models.CharField(
        _('Geri Bildirim Türü'),
        max_length=20,
        choices=FeedbackType.choices,
    )
    
    comment = models.TextField(
        _('Yorum'),
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Öneri Geri Bildirimi')
        verbose_name_plural = _('Öneri Geri Bildirimleri')
        unique_together = ['recommendation', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.feedback_type}"


class TrendingContent(TenantAwareModel):
    """
    Trend içerikler.
    
    Periyodik olarak hesaplanan popüler içerikler.
    """
    
    class TrendPeriod(models.TextChoices):
        """Trend periyotları."""
        DAILY = 'daily', _('Günlük')
        WEEKLY = 'weekly', _('Haftalık')
        MONTHLY = 'monthly', _('Aylık')
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='trending_entries',
        verbose_name=_('İçerik'),
    )
    
    period = models.CharField(
        _('Periyot'),
        max_length=20,
        choices=TrendPeriod.choices,
    )
    
    rank = models.PositiveIntegerField(
        _('Sıra'),
    )
    
    score = models.FloatField(
        _('Trend Skoru'),
    )
    
    # Metrikler
    view_count = models.PositiveIntegerField(
        _('Görüntülenme'),
        default=0,
    )
    
    completion_count = models.PositiveIntegerField(
        _('Tamamlama'),
        default=0,
    )
    
    engagement_score = models.FloatField(
        _('Etkileşim Skoru'),
        default=0.0,
    )
    
    computed_at = models.DateTimeField(
        _('Hesaplama Zamanı'),
        auto_now=True,
    )
    
    class Meta:
        verbose_name = _('Trend İçerik')
        verbose_name_plural = _('Trend İçerikler')
        unique_together = ['tenant', 'content', 'period']
        ordering = ['period', 'rank']
        indexes = [
            models.Index(fields=['tenant', 'period', 'rank']),
        ]
    
    def __str__(self):
        return f"#{self.rank} {self.content.title} ({self.period})"

