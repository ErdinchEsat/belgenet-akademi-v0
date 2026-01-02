"""
Course Models
=============

Kurs yönetimi modelleri.
Frontend TypeScript interface'leri ile uyumlu.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    """
    Kurs modeli.
    
    Frontend Course interface'i ile uyumlu.
    """

    class Status(models.TextChoices):
        """Kurs durumları."""
        DRAFT = 'draft', _('Taslak')
        PENDING_ADMIN_SETUP = 'pending_admin_setup', _('Admin Onayı Bekliyor')
        NEEDS_REVISION = 'needs_revision', _('Düzenleme Gerekli')
        PUBLISHED = 'published', _('Yayında')
        ARCHIVED = 'archived', _('Arşivlenmiş')

    class Level(models.TextChoices):
        """Kurs seviyeleri."""
        BEGINNER = 'Beginner', _('Başlangıç')
        INTERMEDIATE = 'Intermediate', _('Orta')
        ADVANCED = 'Advanced', _('İleri')

    class Visibility(models.TextChoices):
        """Görünürlük ayarları."""
        PUBLIC = 'public', _('Herkese Açık')
        PRIVATE = 'private', _('Özel')
        UNLISTED = 'unlisted', _('Listelenmemiş')

    # Temel bilgiler
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    slug = models.SlugField(
        _('URL Slug'),
        unique=True,
    )
    description = models.TextField(
        _('Açıklama'),
    )
    short_description = models.CharField(
        _('Kısa Açıklama'),
        max_length=300,
        blank=True,
    )
    cover_url = models.URLField(
        _('Kapak Görseli'),
        blank=True,
    )
    
    # Kategorizasyon
    category = models.CharField(
        _('Kategori'),
        max_length=100,
    )
    language = models.CharField(
        _('Dil'),
        max_length=10,
        default='tr',
    )
    level = models.CharField(
        _('Seviye'),
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
    )
    tags = models.JSONField(
        _('Etiketler'),
        default=list,
        blank=True,
    )
    
    # İlişkiler
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name=_('Akademi'),
    )
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_courses',
        verbose_name=_('Eğitmenler'),
    )
    
    # Fiyatlandırma
    is_free = models.BooleanField(
        _('Ücretsiz'),
        default=True,
    )
    price = models.DecimalField(
        _('Fiyat'),
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    currency = models.CharField(
        _('Para Birimi'),
        max_length=3,
        choices=[('TRY', '₺'), ('USD', '$'), ('EUR', '€')],
        default='TRY',
    )
    
    # Yayın ayarları
    visibility = models.CharField(
        _('Görünürlük'),
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    is_published = models.BooleanField(
        _('Yayında'),
        default=False,
    )
    publish_at = models.DateTimeField(
        _('Yayın Tarihi'),
        null=True,
        blank=True,
    )
    
    # Tamamlama ayarları
    certificate_enabled = models.BooleanField(
        _('Sertifika Aktif'),
        default=True,
    )
    completion_percent = models.PositiveIntegerField(
        _('Tamamlama Yüzdesi'),
        default=80,
        help_text=_('Sertifika için gereken minimum tamamlama yüzdesi'),
    )
    
    # Karşılama mesajı
    welcome_message = models.TextField(
        _('Karşılama Mesajı'),
        blank=True,
    )
    
    # Workflow
    status = models.CharField(
        _('Durum'),
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    teacher_submit_note = models.TextField(
        _('Eğitmen Notu'),
        blank=True,
        help_text=_('Eğitmenin admin\'e notu'),
    )
    admin_revision_note = models.TextField(
        _('Admin Düzenleme Notu'),
        blank=True,
        help_text=_('Admin\'in düzenleme talebi'),
    )
    
    # İstatistikler
    enrolled_count = models.PositiveIntegerField(
        _('Kayıtlı Öğrenci'),
        default=0,
    )
    rating = models.DecimalField(
        _('Puan'),
        max_digits=3,
        decimal_places=2,
        default=0,
    )
    rating_count = models.PositiveIntegerField(
        _('Değerlendirme Sayısı'),
        default=0,
    )
    total_duration_minutes = models.PositiveIntegerField(
        _('Toplam Süre (dk)'),
        default=0,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Kurs')
        verbose_name_plural = _('Kurslar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return self.title

    @property
    def cover_url_display(self) -> str:
        """Kapak URL'i veya placeholder."""
        if self.cover_url:
            return self.cover_url
        return 'https://via.placeholder.com/400x225?text=No+Cover'

    @property
    def total_duration(self) -> str:
        """Toplam süre formatı."""
        hours = self.total_duration_minutes // 60
        minutes = self.total_duration_minutes % 60
        if hours > 0:
            return f'{hours}s {minutes}dk'
        return f'{minutes}dk'

    @property
    def stats(self) -> dict:
        """Frontend uyumlu stats objesi."""
        return {
            'enrolled': self.enrolled_count,
            'rating': float(self.rating),
            'totalDuration': self.total_duration,
        }

    @property
    def pricing(self) -> dict:
        """Frontend uyumlu pricing objesi."""
        return {
            'isFree': self.is_free,
            'price': float(self.price),
            'currency': self.currency,
        }

    @property
    def publish(self) -> dict:
        """Frontend uyumlu publish objesi."""
        return {
            'visibility': self.visibility,
            'publishAt': self.publish_at.isoformat() if self.publish_at else None,
            'isPublished': self.is_published,
        }

    @property
    def completion(self) -> dict:
        """Frontend uyumlu completion objesi."""
        return {
            'certificateEnabled': self.certificate_enabled,
            'completionPercent': self.completion_percent,
        }


class CourseModule(models.Model):
    """
    Kurs modülü (Hafta/Bölüm).
    """
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules',
        verbose_name=_('Kurs'),
    )
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    order = models.PositiveIntegerField(
        _('Sıra'),
        default=0,
    )
    is_published = models.BooleanField(
        _('Yayında'),
        default=True,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Modül')
        verbose_name_plural = _('Modüller')
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class CourseContent(models.Model):
    """
    Kurs içeriği (Video, Döküman, Quiz, vb.).
    """

    class ContentType(models.TextChoices):
        """İçerik türleri."""
        VIDEO = 'VIDEO', _('Video')
        DOCUMENT = 'DOCUMENT', _('Döküman')
        QUIZ = 'QUIZ', _('Quiz')
        ASSIGNMENT = 'ASSIGNMENT', _('Ödev')
        EXAM = 'EXAM', _('Sınav')
        LIVE = 'LIVE', _('Canlı Ders')
        TEXT = 'TEXT', _('Metin')
        LINK = 'LINK', _('Link')

    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name='contents',
        verbose_name=_('Modül'),
    )
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=ContentType.choices,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # İçerik verisi (tip'e göre değişir)
    data = models.JSONField(
        _('İçerik Verisi'),
        default=dict,
        help_text=_('Video URL, döküman path, quiz soruları vb.'),
    )
    
    # Süre (video için)
    duration_minutes = models.PositiveIntegerField(
        _('Süre (dk)'),
        default=0,
    )
    
    # Sıra ve durum
    order = models.PositiveIntegerField(
        _('Sıra'),
        default=0,
    )
    is_locked = models.BooleanField(
        _('Kilitli'),
        default=False,
        help_text=_('Önceki içerikler tamamlanmadan erişilemez'),
    )
    is_ready = models.BooleanField(
        _('Hazır'),
        default=False,
        help_text=_('İçerik tamamlandı mı?'),
    )
    is_free_preview = models.BooleanField(
        _('Ücretsiz Önizleme'),
        default=False,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('İçerik')
        verbose_name_plural = _('İçerikler')
        ordering = ['order']

    def __str__(self):
        return f'{self.module.title} - {self.title}'

    @property
    def duration(self) -> str:
        """Süre formatı."""
        if self.duration_minutes == 0:
            return None
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours > 0:
            return f'{hours}:{minutes:02d}'
        return f'{minutes}dk'


class Enrollment(models.Model):
    """
    Kurs kaydı.
    Öğrenci-Kurs ilişkisi.
    """

    class Status(models.TextChoices):
        """Kayıt durumları."""
        ACTIVE = 'active', _('Aktif')
        COMPLETED = 'completed', _('Tamamlandı')
        EXPIRED = 'expired', _('Süresi Doldu')
        CANCELLED = 'cancelled', _('İptal Edildi')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('Öğrenci'),
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('Kurs'),
    )
    
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    
    # İlerleme
    progress_percent = models.PositiveIntegerField(
        _('İlerleme %'),
        default=0,
    )
    completed_contents = models.JSONField(
        _('Tamamlanan İçerikler'),
        default=list,
        help_text=_('Tamamlanan içerik ID listesi'),
    )
    
    # Notlar
    last_accessed_content = models.ForeignKey(
        CourseContent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Son Erişilen İçerik'),
    )
    
    # Tarihler
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Kayıt')
        verbose_name_plural = _('Kayıtlar')
        unique_together = ['user', 'course']
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['user', 'status'], name='enrollment_user_status_idx'),
            models.Index(fields=['course', 'status'], name='enrollment_course_status_idx'),
            models.Index(fields=['enrolled_at'], name='enrollment_date_idx'),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.course.title}'

    def update_progress(self):
        """İlerlemeyi güncelle."""
        total_contents = self.course.modules.aggregate(
            total=models.Count('contents')
        )['total'] or 0
        
        if total_contents > 0:
            completed = len(self.completed_contents)
            self.progress_percent = int((completed / total_contents) * 100)
            self.save(update_fields=['progress_percent'])

    def mark_content_complete(self, content_id: int):
        """İçeriği tamamlandı olarak işaretle."""
        if content_id not in self.completed_contents:
            self.completed_contents.append(content_id)
            self.save(update_fields=['completed_contents'])
            self.update_progress()


class ContentProgress(models.Model):
    """
    İçerik ilerleme kaydı.
    Video izleme süresi, quiz cevapları vb.
    """
    
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='content_progress',
    )
    content = models.ForeignKey(
        CourseContent,
        on_delete=models.CASCADE,
        related_name='progress_records',
    )
    
    # İlerleme
    is_completed = models.BooleanField(default=False)
    progress_percent = models.PositiveIntegerField(default=0)
    
    # Video için
    watched_seconds = models.PositiveIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0)
    
    # Quiz/Sınav için
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)
    
    # Tarihler
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('İçerik İlerlemesi')
        verbose_name_plural = _('İçerik İlerlemeleri')
        unique_together = ['enrollment', 'content']

    def __str__(self):
        return f'{self.enrollment.user.email} - {self.content.title}'

