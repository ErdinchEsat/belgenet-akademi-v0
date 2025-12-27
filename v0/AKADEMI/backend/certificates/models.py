"""
Certificate Models
==================

Sertifika modelleri.
"""

import uuid
import hashlib
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from backend.libs.tenant_aware.models import TenantAwareModel


def certificate_upload_path(instance, filename):
    """Sertifika dosya yolu."""
    return f"certificates/{instance.tenant_id}/{instance.verification_code}.pdf"


class CertificateTemplate(TenantAwareModel):
    """
    Sertifika şablonu.
    
    Her tenant kendi sertifika şablonunu tanımlayabilir.
    """

    name = models.CharField(
        _('Şablon Adı'),
        max_length=100,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # Şablon görünümü
    background_image = models.ImageField(
        _('Arka Plan Görseli'),
        upload_to='certificate_templates/',
        blank=True,
        null=True,
        help_text=_('Sertifika arka plan görseli (opsiyonel)'),
    )
    logo = models.ImageField(
        _('Logo'),
        upload_to='certificate_templates/',
        blank=True,
        null=True,
    )
    
    # Stil ayarları (JSON)
    style_config = models.JSONField(
        _('Stil Ayarları'),
        default=dict,
        blank=True,
        help_text=_('CSS ve düzen ayarları'),
    )
    
    # HTML şablonu
    html_template = models.TextField(
        _('HTML Şablonu'),
        blank=True,
        help_text=_('Jinja2 şablon sözdizimi kullanılır'),
    )
    
    # Varsayılan mı?
    is_default = models.BooleanField(
        _('Varsayılan'),
        default=False,
    )
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sertifika Şablonu')
        verbose_name_plural = _('Sertifika Şablonları')
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({'Varsayılan' if self.is_default else 'Özel'})"

    def save(self, *args, **kwargs):
        # Varsayılan yapılırsa diğerlerini kaldır
        if self.is_default:
            CertificateTemplate.objects.filter(
                tenant=self.tenant,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Certificate(TenantAwareModel):
    """
    Sertifika modeli.
    
    Kurs tamamlandığında otomatik veya manuel oluşturulur.
    """

    class Status(models.TextChoices):
        """Sertifika durumları."""
        PENDING = 'pending', _('Beklemede')
        GENERATED = 'generated', _('Oluşturuldu')
        ISSUED = 'issued', _('Verildi')
        REVOKED = 'revoked', _('İptal Edildi')

    # Benzersiz kimlik
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    verification_code = models.CharField(
        _('Doğrulama Kodu'),
        max_length=32,
        unique=True,
        editable=False,
    )
    
    # İlişkiler
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('Kullanıcı'),
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('Kurs'),
    )
    enrollment = models.OneToOneField(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='certificate',
        verbose_name=_('Kayıt'),
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates',
        verbose_name=_('Şablon'),
    )
    
    # Sertifika bilgileri
    title = models.CharField(
        _('Sertifika Başlığı'),
        max_length=200,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # Tamamlama bilgileri
    completion_date = models.DateField(
        _('Tamamlama Tarihi'),
    )
    completion_percent = models.PositiveIntegerField(
        _('Tamamlama Yüzdesi'),
        default=100,
    )
    final_score = models.DecimalField(
        _('Final Notu'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    
    # Beceriler ve kazanımlar
    skills = models.JSONField(
        _('Kazanılan Beceriler'),
        default=list,
        blank=True,
    )
    
    # Süre bilgisi
    total_hours = models.DecimalField(
        _('Toplam Süre (saat)'),
        max_digits=6,
        decimal_places=1,
        default=0,
    )
    
    # PDF dosyası
    pdf_file = models.FileField(
        _('PDF Dosyası'),
        upload_to=certificate_upload_path,
        blank=True,
        null=True,
    )
    
    # Durum
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    
    # İmza bilgileri
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_certificates',
        verbose_name=_('Veren'),
    )
    digital_signature = models.TextField(
        _('Dijital İmza'),
        blank=True,
    )
    
    # Paylaşım
    is_public = models.BooleanField(
        _('Herkese Açık'),
        default=True,
    )
    share_url = models.CharField(
        _('Paylaşım Linki'),
        max_length=255,
        blank=True,
    )
    
    # Meta
    metadata = models.JSONField(
        _('Ek Veri'),
        default=dict,
        blank=True,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    issued_at = models.DateTimeField(
        _('Verilme Tarihi'),
        null=True,
        blank=True,
    )
    revoked_at = models.DateTimeField(
        _('İptal Tarihi'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Sertifika')
        verbose_name_plural = _('Sertifikalar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['verification_code']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['course', 'status']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.course.title}"

    def save(self, *args, **kwargs):
        # Doğrulama kodu oluştur
        if not self.verification_code:
            self.verification_code = self._generate_verification_code()
        
        # Paylaşım linki oluştur
        if not self.share_url:
            self.share_url = f"/certificates/verify/{self.verification_code}"
        
        super().save(*args, **kwargs)

    def _generate_verification_code(self):
        """Benzersiz doğrulama kodu oluşturur."""
        data = f"{self.user_id}-{self.course_id}-{timezone.now().isoformat()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:16].upper()
        return f"CERT-{hash_val}"

    @property
    def verify_url(self) -> str:
        """Tam doğrulama URL'i."""
        from django.conf import settings
        base_url = getattr(settings, 'FRONTEND_URL', '')
        return f"{base_url}/certificates/verify/{self.verification_code}"

    @property
    def qr_data(self) -> str:
        """QR kod için veri."""
        return self.verify_url

    @property
    def is_valid(self) -> bool:
        """Sertifika geçerli mi?"""
        return self.status == self.Status.ISSUED

    def issue(self, issued_by=None):
        """Sertifikayı ver."""
        self.status = self.Status.ISSUED
        self.issued_by = issued_by
        self.issued_at = timezone.now()
        self.save(update_fields=['status', 'issued_by', 'issued_at'])

    def revoke(self, reason=''):
        """Sertifikayı iptal et."""
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.metadata['revoke_reason'] = reason
        self.save(update_fields=['status', 'revoked_at', 'metadata'])


class CertificateDownload(models.Model):
    """
    Sertifika indirme kaydı.
    
    Sertifika her indirildiğinde log tutulur.
    """
    
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='downloads',
    )
    downloaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        _('IP Adresi'),
        null=True,
        blank=True,
    )
    user_agent = models.CharField(
        _('User Agent'),
        max_length=500,
        blank=True,
    )
    
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Sertifika İndirme')
        verbose_name_plural = _('Sertifika İndirmeleri')
        ordering = ['-downloaded_at']

