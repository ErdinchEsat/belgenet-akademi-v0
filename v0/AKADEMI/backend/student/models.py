"""
Student Models
==============

Öğrenci modülü modelleri:
- ClassGroup: Sınıf/Grup
- Assignment: Ödev
- AssignmentSubmission: Ödev teslimi
- LiveSession: Canlı ders
- Notification: Bildirim
- Message: Mesaj
- SupportTicket: Destek talebi
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClassGroup(models.Model):
    """
    Sınıf/Grup modeli.
    Öğrencilerin kayıtlı olduğu sınıflar.
    """

    class Type(models.TextChoices):
        ACADEMIC = 'ACADEMIC', _('Akademik')
        VOCATIONAL = 'VOCATIONAL', _('Mesleki')

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Aktif')
        COMPLETED = 'COMPLETED', _('Tamamlandı')
        ARCHIVED = 'ARCHIVED', _('Arşivlendi')

    name = models.CharField(_('Sınıf Adı'), max_length=100)
    code = models.CharField(_('Sınıf Kodu'), max_length=20, blank=True)
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=Type.choices,
        default=Type.ACADEMIC,
    )
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    description = models.TextField(_('Açıklama'), blank=True)
    term = models.CharField(_('Dönem'), max_length=50, blank=True)
    
    # İlişkiler
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='class_groups',
        verbose_name=_('Akademi'),
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='class_groups',
        verbose_name=_('Kurs'),
    )
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_classes',
        verbose_name=_('Eğitmenler'),
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ClassEnrollment',
        related_name='enrolled_classes',
        verbose_name=_('Öğrenciler'),
    )
    
    # Kapasite
    capacity = models.PositiveIntegerField(_('Kapasite'), default=50)
    
    # Tarihler
    start_date = models.DateField(_('Başlangıç'), null=True, blank=True)
    end_date = models.DateField(_('Bitiş'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sınıf')
        verbose_name_plural = _('Sınıflar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status'], name='classgroup_tenant_status_idx'),
            models.Index(fields=['course', 'status'], name='classgroup_course_status_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def student_count(self):
        return self.class_enrollments.filter(status='ACTIVE').count()

    @property
    def passive_student_count(self):
        return self.class_enrollments.filter(status='PASSIVE').count()


class ClassEnrollment(models.Model):
    """Sınıf kaydı - Öğrenci-Sınıf ilişkisi."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Aktif')
        PASSIVE = 'PASSIVE', _('Pasif')
        COMPLETED = 'COMPLETED', _('Tamamladı')
        DROPPED = 'DROPPED', _('Bıraktı')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_enrollments',
    )
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='class_enrollments',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'class_group']
        verbose_name = _('Sınıf Kaydı')
        verbose_name_plural = _('Sınıf Kayıtları')


class Assignment(models.Model):
    """Ödev modeli."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Taslak')
        PUBLISHED = 'PUBLISHED', _('Yayında')
        CLOSED = 'CLOSED', _('Kapalı')

    title = models.CharField(_('Başlık'), max_length=200)
    description = models.TextField(_('Açıklama'))
    
    # İlişkiler
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('Sınıf'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assignments',
    )
    
    # Tarihler
    due_date = models.DateTimeField(_('Teslim Tarihi'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    max_score = models.PositiveIntegerField(_('Maksimum Puan'), default=100)
    
    # Dosyalar
    attachments = models.JSONField(_('Ekler'), default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Ödev')
        verbose_name_plural = _('Ödevler')
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['class_group', 'status'], name='assignment_class_status_idx'),
            models.Index(fields=['due_date'], name='assignment_due_idx'),
        ]

    def __str__(self):
        return self.title


class AssignmentSubmission(models.Model):
    """Ödev teslimi."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Beklemede')
        SUBMITTED = 'SUBMITTED', _('Teslim Edildi')
        LATE = 'LATE', _('Geç Teslim')
        GRADED = 'GRADED', _('Notlandırıldı')

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    content = models.TextField(_('İçerik'), blank=True)
    attachments = models.JSONField(_('Dosyalar'), default=list, blank=True)
    
    # Notlandırma
    score = models.PositiveIntegerField(_('Puan'), null=True, blank=True)
    feedback = models.TextField(_('Geri Bildirim'), blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['assignment', 'student']
        verbose_name = _('Ödev Teslimi')
        verbose_name_plural = _('Ödev Teslimleri')


class LiveSession(models.Model):
    """Canlı ders."""

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Planlandı')
        LIVE = 'LIVE', _('Canlı')
        COMPLETED = 'COMPLETED', _('Tamamlandı')
        CANCELLED = 'CANCELLED', _('İptal')

    title = models.CharField(_('Başlık'), max_length=200)
    description = models.TextField(_('Açıklama'), blank=True)
    
    # İlişkiler
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='live_sessions',
        verbose_name=_('Sınıf'),
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='live_sessions',
    )
    
    # Zamanlama
    scheduled_at = models.DateTimeField(_('Planlanan Zaman'))
    duration_minutes = models.PositiveIntegerField(_('Süre (dk)'), default=60)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    
    # Canlı ders bilgileri
    meeting_url = models.URLField(_('Ders URL'), blank=True)
    recording_url = models.URLField(_('Kayıt URL'), blank=True)
    max_participants = models.PositiveIntegerField(_('Maks Katılımcı'), default=100)
    participant_count = models.PositiveIntegerField(_('Katılımcı Sayısı'), default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Canlı Ders')
        verbose_name_plural = _('Canlı Dersler')
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['instructor', 'status'], name='livesession_instr_status_idx'),
            models.Index(fields=['scheduled_at'], name='livesession_scheduled_idx'),
        ]

    def __str__(self):
        return f"{self.title} - {self.scheduled_at}"


class Notification(models.Model):
    """Bildirim."""

    class Type(models.TextChoices):
        SYSTEM = 'SYSTEM', _('Sistem')
        ASSIGNMENT = 'ASSIGNMENT', _('Ödev')
        LIVE = 'LIVE', _('Canlı Ders')
        GRADE = 'GRADE', _('Not')
        MESSAGE = 'MESSAGE', _('Mesaj')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Duyuru')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(_('Başlık'), max_length=200)
    message = models.TextField(_('Mesaj'), blank=True)
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
    )
    source = models.CharField(_('Kaynak'), max_length=100, blank=True)
    
    # Link
    action_url = models.CharField(_('Link'), max_length=500, blank=True)
    
    is_read = models.BooleanField(_('Okundu'), default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Bildirim')
        verbose_name_plural = _('Bildirimler')
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Message(models.Model):
    """Mesaj."""

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
    )
    subject = models.CharField(_('Konu'), max_length=200, blank=True)
    content = models.TextField(_('İçerik'))
    
    is_read = models.BooleanField(_('Okundu'), default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Thread
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mesaj')
        verbose_name_plural = _('Mesajlar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.subject}"


class SupportTicket(models.Model):
    """Destek talebi."""

    class Category(models.TextChoices):
        TECHNICAL = 'TECHNICAL', _('Teknik')
        ACADEMIC = 'ACADEMIC', _('Akademik')
        BILLING = 'BILLING', _('Ödeme')
        OTHER = 'OTHER', _('Diğer')

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Açık')
        ANSWERED = 'ANSWERED', _('Cevaplandı')
        CLOSED = 'CLOSED', _('Kapatıldı')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    subject = models.CharField(_('Konu'), max_length=200)
    description = models.TextField(_('Açıklama'))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    
    # Cevap
    response = models.TextField(_('Cevap'), blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_tickets',
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Destek Talebi')
        verbose_name_plural = _('Destek Talepleri')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"

