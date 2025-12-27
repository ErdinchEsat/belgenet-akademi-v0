"""
Sequencing Models
=================

İçerik kilitleme ve sıralı öğrenme modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class ContentLockPolicy(TenantAwareModel):
    """
    İçerik kilit politikası.
    
    Her içerik için birden fazla policy tanımlanabilir.
    Tüm policy'ler AND mantığıyla değerlendirilir.
    
    Policy Types:
    - min_watch_ratio: Minimum izleme oranı (örn: %80)
    - requires_prev_completed: Önceki içerik tamamlanmalı
    - requires_quiz_pass: Quiz geçilmeli
    - requires_checkpoint: Checkpoint'ler tamamlanmalı
    """
    
    class PolicyType(models.TextChoices):
        """Policy türleri."""
        MIN_WATCH_RATIO = 'min_watch_ratio', _('Minimum İzleme')
        REQUIRES_PREV_COMPLETED = 'requires_prev_completed', _('Önceki Tamamlanmalı')
        REQUIRES_QUIZ_PASS = 'requires_quiz_pass', _('Quiz Geçilmeli')
        REQUIRES_CHECKPOINT = 'requires_checkpoint', _('Checkpoint Tamamlanmalı')
        TIME_LOCKED = 'time_locked', _('Zamana Bağlı')
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='lock_policies',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='lock_policies',
        verbose_name=_('İçerik'),
    )
    
    policy_type = models.CharField(
        _('Policy Türü'),
        max_length=30,
        choices=PolicyType.choices,
        db_index=True,
    )
    
    policy_config = models.JSONField(
        _('Policy Ayarları'),
        default=dict,
        help_text=_('Policy türüne göre değişen ayarlar'),
    )
    """
    Örnek config'ler:
    - min_watch_ratio: {"min_ratio": 0.8}
    - requires_prev_completed: {"prev_content_id": 123}
    - requires_quiz_pass: {"quiz_id": "uuid", "min_score": 70}
    - time_locked: {"unlock_after": "2025-01-01T00:00:00Z"}
    """
    
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    
    priority = models.PositiveIntegerField(
        _('Öncelik'),
        default=0,
        help_text=_('Yüksek öncelik önce değerlendirilir'),
    )
    
    class Meta:
        verbose_name = _('Kilit Politikası')
        verbose_name_plural = _('Kilit Politikaları')
        ordering = ['-priority', 'policy_type']
        indexes = [
            models.Index(fields=['tenant', 'course', 'content']),
            models.Index(fields=['tenant', 'content', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.content.title} - {self.get_policy_type_display()}"


class ContentUnlockState(TenantAwareModel):
    """
    Kullanıcı bazında içerik kilit durumu.
    
    Her (tenant, user, content) için tek kayıt.
    Policy değerlendirmesi sonucu güncellenir.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='unlock_states',
        verbose_name=_('Kullanıcı'),
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='unlock_states',
        verbose_name=_('Kurs'),
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='unlock_states',
        verbose_name=_('İçerik'),
    )
    
    is_unlocked = models.BooleanField(
        _('Açık'),
        default=False,
        db_index=True,
    )
    
    unlocked_at = models.DateTimeField(
        _('Açılma Zamanı'),
        null=True,
        blank=True,
    )
    
    unlock_reason = models.CharField(
        _('Açılma Nedeni'),
        max_length=100,
        blank=True,
        null=True,
    )
    
    # Değerlendirme durumu
    evaluation_state = models.JSONField(
        _('Değerlendirme Durumu'),
        default=dict,
        help_text=_('Her policy için değerlendirme sonucu'),
    )
    """
    Örnek:
    {
        "min_watch_ratio": {"passed": true, "current": 0.85, "required": 0.80},
        "requires_prev_completed": {"passed": true, "prev_content_id": 123},
        "requires_quiz_pass": {"passed": false, "quiz_id": "uuid", "score": 65, "required": 70}
    }
    """
    
    last_evaluated_at = models.DateTimeField(
        _('Son Değerlendirme'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Kilit Durumu')
        verbose_name_plural = _('Kilit Durumları')
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user', 'content'],
                name='unique_user_content_unlock'
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'user', 'course']),
            models.Index(fields=['tenant', 'content', 'is_unlocked']),
            models.Index(fields=['user', 'is_unlocked']),
        ]
    
    def __str__(self):
        status = "🔓" if self.is_unlocked else "🔒"
        return f"{status} {self.user.email} - {self.content.title}"
    
    def unlock(self, reason: str = None):
        """İçeriği aç."""
        self.is_unlocked = True
        self.unlocked_at = timezone.now()
        self.unlock_reason = reason
        self.save(update_fields=['is_unlocked', 'unlocked_at', 'unlock_reason', 'updated_at'])

