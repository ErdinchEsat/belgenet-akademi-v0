"""
Tenant (Akademi) Model
======================

Multi-tenant yapı için Akademi/Kurum modeli.
Her akademi kendi kullanıcıları, kursları ve ayarlarına sahiptir.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """
    Akademi/Kurum modeli.
    
    Frontend'deki TypeScript Tenant interface'i ile uyumlu:
    - id, name, slug, logo, color, type, themeConfig
    """

    class TenantType(models.TextChoices):
        """Akademi türleri."""
        MUNICIPALITY = 'Municipality', _('Belediye')
        CORPORATE = 'Corporate', _('Kurumsal')
        UNIVERSITY = 'University', _('Üniversite')
        GOVERNMENT = 'Government', _('Kamu Kurumu')
        NGO = 'NGO', _('Sivil Toplum Kuruluşu')

    # Temel bilgiler
    name = models.CharField(
        _('Akademi Adı'),
        max_length=200,
    )
    slug = models.SlugField(
        _('URL Slug'),
        unique=True,
        help_text=_('URL yapısında kullanılacak (örn: ibb-tech)'),
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # Görsel
    logo = models.URLField(
        _('Logo URL'),
        blank=True,
        help_text=_('Akademi logosu URL\'i'),
    )
    favicon = models.URLField(
        _('Favicon URL'),
        blank=True,
    )
    
    # Tip
    type = models.CharField(
        _('Akademi Türü'),
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.CORPORATE,
    )
    
    # İletişim
    email = models.EmailField(
        _('E-posta'),
        blank=True,
    )
    phone = models.CharField(
        _('Telefon'),
        max_length=20,
        blank=True,
    )
    website = models.URLField(
        _('Web Sitesi'),
        blank=True,
    )
    address = models.TextField(
        _('Adres'),
        blank=True,
    )
    
    # Tema ayarları
    primary_color = models.CharField(
        _('Ana Renk'),
        max_length=7,
        default='#4F46E5',
        help_text=_('Hex renk kodu (örn: #4F46E5)'),
    )
    sidebar_position = models.CharField(
        _('Sidebar Konumu'),
        max_length=10,
        choices=[('left', 'Sol'), ('right', 'Sağ')],
        default='left',
    )
    sidebar_color = models.CharField(
        _('Sidebar Rengi'),
        max_length=7,
        default='#1E293B',
    )
    sidebar_content_color = models.CharField(
        _('Sidebar İçerik Rengi'),
        max_length=7,
        default='#F8FAFC',
    )
    main_background_color = models.CharField(
        _('Ana Arkaplan Rengi'),
        max_length=7,
        default='#F1F5F9',
    )
    button_radius = models.CharField(
        _('Buton Yuvarlaklığı'),
        max_length=20,
        choices=[
            ('rounded-none', 'Köşeli'),
            ('rounded-md', 'Orta'),
            ('rounded-xl', 'Yuvarlak'),
            ('rounded-full', 'Tam Yuvarlak'),
        ],
        default='rounded-md',
    )
    
    # Limitler
    storage_limit_gb = models.PositiveIntegerField(
        _('Depolama Limiti (GB)'),
        default=10,
    )
    user_limit = models.PositiveIntegerField(
        _('Kullanıcı Limiti'),
        default=100,
        help_text=_('0 = sınırsız'),
    )
    course_limit = models.PositiveIntegerField(
        _('Kurs Limiti'),
        default=50,
        help_text=_('0 = sınırsız'),
    )
    
    # Modül izinleri
    module_live_class = models.BooleanField(
        _('Canlı Ders Modülü'),
        default=True,
    )
    module_quiz = models.BooleanField(
        _('Quiz Modülü'),
        default=True,
    )
    module_exam = models.BooleanField(
        _('Sınav Modülü'),
        default=True,
    )
    module_assignment = models.BooleanField(
        _('Ödev Modülü'),
        default=True,
    )
    module_certificate = models.BooleanField(
        _('Sertifika Modülü'),
        default=True,
    )
    module_forum = models.BooleanField(
        _('Forum Modülü'),
        default=False,
    )
    module_ai_assistant = models.BooleanField(
        _('AI Asistan Modülü'),
        default=False,
    )
    
    # Durum
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    is_verified = models.BooleanField(
        _('Doğrulanmış'),
        default=False,
    )
    
    # İstatistikler (cache)
    stats_users = models.PositiveIntegerField(
        _('Toplam Kullanıcı'),
        default=0,
    )
    stats_courses = models.PositiveIntegerField(
        _('Toplam Kurs'),
        default=0,
    )
    stats_storage_used_mb = models.PositiveIntegerField(
        _('Kullanılan Depolama (MB)'),
        default=0,
    )
    
    # Tarihler
    created_at = models.DateTimeField(
        _('Oluşturulma Tarihi'),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _('Güncellenme Tarihi'),
        auto_now=True,
    )
    trial_ends_at = models.DateTimeField(
        _('Deneme Süresi Bitiş'),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Akademi')
        verbose_name_plural = _('Akademiler')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    @property
    def color(self) -> str:
        """Frontend uyumluluğu için alias."""
        return self.primary_color

    @property
    def theme_config(self) -> dict:
        """
        Frontend uyumlu tema config objesi.
        """
        return {
            'sidebarPosition': self.sidebar_position,
            'sidebarColor': self.sidebar_color,
            'sidebarContentColor': self.sidebar_content_color,
            'mainBackgroundColor': self.main_background_color,
            'buttonRadius': self.button_radius,
        }

    @property
    def modules_config(self) -> dict:
        """
        Aktif modüller.
        """
        return {
            'liveClass': self.module_live_class,
            'quiz': self.module_quiz,
            'exam': self.module_exam,
            'assignment': self.module_assignment,
            'certificate': self.module_certificate,
            'forum': self.module_forum,
            'aiAssistant': self.module_ai_assistant,
        }

    @property
    def storage_used_percent(self) -> float:
        """Depolama kullanım yüzdesi."""
        if self.storage_limit_gb == 0:
            return 0
        used_gb = self.stats_storage_used_mb / 1024
        return round((used_gb / self.storage_limit_gb) * 100, 2)

    def can_add_user(self) -> bool:
        """Yeni kullanıcı eklenebilir mi?"""
        if self.user_limit == 0:
            return True
        return self.stats_users < self.user_limit

    def can_add_course(self) -> bool:
        """Yeni kurs eklenebilir mi?"""
        if self.course_limit == 0:
            return True
        return self.stats_courses < self.course_limit

    def update_stats(self):
        """İstatistikleri güncelle."""
        from backend.users.models import User
        
        self.stats_users = self.users.count()
        # self.stats_courses = self.courses.count()  # Course modeli oluşturulduğunda
        self.save(update_fields=['stats_users', 'stats_courses'])


class TenantSettings(models.Model):
    """
    Akademi ayarları genişletmesi.
    """
    
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='settings',
    )
    
    # E-posta ayarları
    email_from_name = models.CharField(
        _('Gönderen Adı'),
        max_length=100,
        blank=True,
    )
    email_from_address = models.EmailField(
        _('Gönderen E-posta'),
        blank=True,
    )
    
    # Kayıt ayarları
    allow_self_registration = models.BooleanField(
        _('Kendi Kendine Kayıt'),
        default=False,
        help_text=_('Kullanıcılar kendi kendilerine kayıt olabilir mi?'),
    )
    require_email_verification = models.BooleanField(
        _('E-posta Doğrulaması Zorunlu'),
        default=True,
    )
    default_user_role = models.CharField(
        _('Varsayılan Kullanıcı Rolü'),
        max_length=20,
        default='STUDENT',
    )
    
    # Kurs ayarları
    require_course_approval = models.BooleanField(
        _('Kurs Onayı Zorunlu'),
        default=True,
        help_text=_('Eğitmenlerin kursları yayınlamadan önce onay gereksin mi?'),
    )
    default_course_visibility = models.CharField(
        _('Varsayılan Kurs Görünürlüğü'),
        max_length=20,
        choices=[
            ('public', 'Herkese Açık'),
            ('private', 'Özel'),
            ('unlisted', 'Listelenmemiş'),
        ],
        default='private',
    )
    
    # Sertifika ayarları
    certificate_prefix = models.CharField(
        _('Sertifika Ön Eki'),
        max_length=20,
        blank=True,
        help_text=_('Örn: CERT, AKD'),
    )
    certificate_template = models.TextField(
        _('Sertifika Şablonu (HTML)'),
        blank=True,
    )
    
    # Özelleştirme
    custom_css = models.TextField(
        _('Özel CSS'),
        blank=True,
    )
    custom_js = models.TextField(
        _('Özel JavaScript'),
        blank=True,
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Akademi Ayarları')
        verbose_name_plural = _('Akademi Ayarları')

    def __str__(self):
        return f'{self.tenant.name} Ayarları'

