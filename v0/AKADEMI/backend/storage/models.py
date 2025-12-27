"""
Storage Models
==============

Dosya yükleme ve depolama modelleri.
"""

import os
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

from backend.libs.tenant_aware.models import TenantAwareModel


def upload_to_path(instance, filename):
    """
    Dosya yükleme yolu oluşturur.
    Format: {tenant_id}/{category}/{year}/{month}/{uuid}_{filename}
    """
    ext = os.path.splitext(filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex[:12]}_{filename}"
    
    # Tenant bazlı dizin
    tenant_id = instance.tenant_id if hasattr(instance, 'tenant_id') else 'global'
    
    # Tarih bazlı alt dizin
    from django.utils import timezone
    now = timezone.now()
    date_path = f"{now.year}/{now.month:02d}"
    
    # Kategori bazlı dizin
    category = getattr(instance, 'category', 'general')
    
    return f"uploads/{tenant_id}/{category}/{date_path}/{unique_filename}"


class FileUpload(TenantAwareModel):
    """
    Ana dosya yükleme modeli.
    
    Tüm dosya yüklemeleri için merkezi model.
    Tenant-aware yapıdadır.
    """

    class Category(models.TextChoices):
        """Dosya kategorileri."""
        PROFILE = 'profile', _('Profil Resmi')
        ASSIGNMENT = 'assignment', _('Ödev Dosyası')
        SUBMISSION = 'submission', _('Ödev Teslimi')
        MATERIAL = 'material', _('Kurs Materyali')
        CERTIFICATE = 'certificate', _('Sertifika')
        DOCUMENT = 'document', _('Döküman')
        ATTACHMENT = 'attachment', _('Ek Dosya')
        OTHER = 'other', _('Diğer')

    class Status(models.TextChoices):
        """Dosya durumları."""
        PENDING = 'pending', _('Beklemede')
        PROCESSING = 'processing', _('İşleniyor')
        COMPLETED = 'completed', _('Tamamlandı')
        FAILED = 'failed', _('Başarısız')
        DELETED = 'deleted', _('Silindi')

    # Dosya bilgileri
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    file = models.FileField(
        _('Dosya'),
        upload_to=upload_to_path,
        max_length=500,
    )
    original_filename = models.CharField(
        _('Orijinal Dosya Adı'),
        max_length=255,
    )
    
    # Metadata
    category = models.CharField(
        _('Kategori'),
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    mime_type = models.CharField(
        _('MIME Tipi'),
        max_length=100,
        blank=True,
    )
    file_size = models.PositiveBigIntegerField(
        _('Dosya Boyutu (byte)'),
        default=0,
    )
    file_hash = models.CharField(
        _('Dosya Hash'),
        max_length=64,
        blank=True,
        help_text=_('SHA-256 hash değeri'),
    )
    
    # Durum
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message = models.TextField(
        _('Hata Mesajı'),
        blank=True,
    )
    
    # İlişkiler
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files',
        verbose_name=_('Yükleyen'),
    )
    
    # Generic relation için
    content_type = models.CharField(
        _('İçerik Tipi'),
        max_length=100,
        blank=True,
        help_text=_('İlişkili model tipi (örn: courses.Course)'),
    )
    object_id = models.CharField(
        _('Nesne ID'),
        max_length=50,
        blank=True,
        help_text=_('İlişkili nesne ID'),
    )
    
    # Görsel için ek bilgiler
    width = models.PositiveIntegerField(
        _('Genişlik'),
        null=True,
        blank=True,
    )
    height = models.PositiveIntegerField(
        _('Yükseklik'),
        null=True,
        blank=True,
    )
    
    # Erişim kontrolü
    is_public = models.BooleanField(
        _('Herkese Açık'),
        default=False,
    )
    access_count = models.PositiveIntegerField(
        _('Erişim Sayısı'),
        default=0,
    )
    
    # Ek veri
    metadata = models.JSONField(
        _('Ek Veri'),
        default=dict,
        blank=True,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        _('Son Kullanma Tarihi'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Dosya')
        verbose_name_plural = _('Dosyalar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'status']),
            models.Index(fields=['uploaded_by', 'category']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['file_hash']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.get_category_display()})"

    @property
    def file_url(self) -> str:
        """Dosya URL'i."""
        if self.file:
            return self.file.url
        return ''

    @property
    def file_size_display(self) -> str:
        """İnsan okunabilir dosya boyutu."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def is_image(self) -> bool:
        """Görsel dosya mı?"""
        return self.mime_type.startswith('image/')

    @property
    def is_video(self) -> bool:
        """Video dosya mı?"""
        return self.mime_type.startswith('video/')

    @property
    def is_document(self) -> bool:
        """Döküman dosya mı?"""
        doc_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument',
            'text/',
        ]
        return any(self.mime_type.startswith(t) for t in doc_types)

    @property
    def extension(self) -> str:
        """Dosya uzantısı."""
        return os.path.splitext(self.original_filename)[1].lower()

    def increment_access_count(self):
        """Erişim sayısını artır."""
        self.access_count += 1
        self.save(update_fields=['access_count'])

    def mark_deleted(self):
        """Dosyayı silinmiş olarak işaretle."""
        self.status = self.Status.DELETED
        self.save(update_fields=['status'])

    def delete_file(self, save=True):
        """Fiziksel dosyayı sil."""
        if self.file:
            self.file.delete(save=False)
        if save:
            self.mark_deleted()


class ImageVariant(models.Model):
    """
    Görsel varyantları.
    
    Ana görselin farklı boyutlarda versiyonları.
    Örn: thumbnail, medium, large
    """

    class Size(models.TextChoices):
        """Varyant boyutları."""
        THUMBNAIL = 'thumbnail', _('Küçük (150x150)')
        SMALL = 'small', _('Küçük (300x300)')
        MEDIUM = 'medium', _('Orta (600x600)')
        LARGE = 'large', _('Büyük (1200x1200)')
        ORIGINAL = 'original', _('Orijinal')

    original = models.ForeignKey(
        FileUpload,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name=_('Orijinal'),
    )
    size = models.CharField(
        _('Boyut'),
        max_length=20,
        choices=Size.choices,
    )
    file = models.ImageField(
        _('Dosya'),
        upload_to='variants/',
        max_length=500,
    )
    width = models.PositiveIntegerField(_('Genişlik'))
    height = models.PositiveIntegerField(_('Yükseklik'))
    file_size = models.PositiveIntegerField(_('Dosya Boyutu'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Görsel Varyantı')
        verbose_name_plural = _('Görsel Varyantları')
        unique_together = ['original', 'size']

    def __str__(self):
        return f"{self.original.original_filename} - {self.get_size_display()}"

    @property
    def url(self) -> str:
        return self.file.url if self.file else ''


class UploadSession(models.Model):
    """
    Büyük dosya yüklemeleri için oturum.
    
    Chunk bazlı yükleme için kullanılır.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # Dosya bilgileri
    filename = models.CharField(_('Dosya Adı'), max_length=255)
    file_size = models.PositiveBigIntegerField(_('Toplam Boyut'))
    chunk_size = models.PositiveIntegerField(_('Parça Boyutu'), default=5242880)  # 5MB
    total_chunks = models.PositiveIntegerField(_('Toplam Parça'))
    uploaded_chunks = models.PositiveIntegerField(_('Yüklenen Parça'), default=0)
    
    # Durum
    is_completed = models.BooleanField(_('Tamamlandı'), default=False)
    completed_file = models.ForeignKey(
        FileUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='upload_sessions',
    )
    
    # İlişki
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='upload_sessions',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='upload_sessions',
    )
    
    # Metadata
    category = models.CharField(
        max_length=20,
        choices=FileUpload.Category.choices,
        default=FileUpload.Category.OTHER,
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = _('Yükleme Oturumu')
        verbose_name_plural = _('Yükleme Oturumları')

    def __str__(self):
        return f"{self.filename} ({self.uploaded_chunks}/{self.total_chunks})"

    @property
    def progress_percent(self) -> int:
        if self.total_chunks == 0:
            return 0
        return int((self.uploaded_chunks / self.total_chunks) * 100)

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() > self.expires_at

