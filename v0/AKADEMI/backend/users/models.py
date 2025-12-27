"""
Custom User Model
=================

Akademi İstanbul için özelleştirilmiş kullanıcı modeli.
Multi-tenant yapıyı destekler ve rol bazlı yetkilendirme sağlar.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom User Manager.
    Email ile kullanıcı oluşturmayı destekler.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Normal kullanıcı oluşturur.
        """
        if not email:
            raise ValueError(_('Email adresi zorunludur'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Superuser oluşturur.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser is_staff=True olmalı'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser is_superuser=True olmalı'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User Model.
    
    Frontend'deki TypeScript User interface'i ile uyumlu:
    - id, name, email, role, avatar, tenantId, title, points, streak
    """

    class Role(models.TextChoices):
        """Kullanıcı rolleri."""
        GUEST = 'GUEST', _('Misafir')
        STUDENT = 'STUDENT', _('Öğrenci')
        INSTRUCTOR = 'INSTRUCTOR', _('Eğitmen')
        ADMIN = 'ADMIN', _('Yönetici')
        TENANT_ADMIN = 'TENANT_ADMIN', _('Kurum Yöneticisi')
        SUPER_ADMIN = 'SUPER_ADMIN', _('Süper Admin')

    # Username yerine email kullan
    username = None
    email = models.EmailField(_('E-posta'), unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # Temel bilgiler
    first_name = models.CharField(_('Ad'), max_length=150)
    last_name = models.CharField(_('Soyad'), max_length=150)
    
    # Rol ve yetki
    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Role.choices,
        default=Role.GUEST,
        db_index=True,
    )
    
    # Profil bilgileri
    avatar = models.URLField(
        _('Profil Fotoğrafı'),
        blank=True,
        null=True,
        help_text=_('Profil fotoğrafı URL\'i'),
    )
    title = models.CharField(
        _('Ünvan'),
        max_length=100,
        blank=True,
        help_text=_('Örn: Kıdemli Yazılım Mühendisi'),
    )
    bio = models.TextField(
        _('Hakkında'),
        blank=True,
        help_text=_('Kısa biyografi'),
    )
    phone = models.CharField(
        _('Telefon'),
        max_length=20,
        blank=True,
    )
    
    # Tenant (Akademi) ilişkisi
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Akademi'),
    )
    
    # Gamification
    points = models.PositiveIntegerField(
        _('Puan'),
        default=0,
        help_text=_('Toplanan XP puanı'),
    )
    streak = models.PositiveIntegerField(
        _('Seri'),
        default=0,
        help_text=_('Ardışık gün sayısı'),
    )
    
    # Tercihler
    language = models.CharField(
        _('Dil'),
        max_length=5,
        choices=[('tr', 'Türkçe'), ('en', 'English')],
        default='tr',
    )
    timezone = models.CharField(
        _('Saat Dilimi'),
        max_length=50,
        default='Europe/Istanbul',
    )
    
    # Bildirim tercihleri
    notify_email = models.BooleanField(
        _('E-posta Bildirimleri'),
        default=True,
    )
    notify_push = models.BooleanField(
        _('Push Bildirimleri'),
        default=True,
    )
    
    # Tarihler
    last_login_ip = models.GenericIPAddressField(
        _('Son Giriş IP'),
        null=True,
        blank=True,
    )
    email_verified_at = models.DateTimeField(
        _('E-posta Doğrulama Tarihi'),
        null=True,
        blank=True,
    )
    
    # Manager
    objects = UserManager()

    class Meta:
        verbose_name = _('Kullanıcı')
        verbose_name_plural = _('Kullanıcılar')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['tenant']),
        ]

    def __str__(self):
        return self.full_name or self.email

    @property
    def full_name(self) -> str:
        """Tam ad."""
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def name(self) -> str:
        """Frontend uyumluluğu için alias."""
        return self.full_name

    @property
    def tenant_id(self) -> str | None:
        """Frontend uyumluluğu için tenant ID."""
        return str(self.tenant.id) if self.tenant else None

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self) -> bool:
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_tenant_admin(self) -> bool:
        return self.role == self.Role.TENANT_ADMIN

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN

    def get_avatar_url(self) -> str:
        """Avatar URL'i döndürür, yoksa default avatar."""
        if self.avatar:
            return self.avatar
        # UI Avatars ile default avatar
        name = self.full_name.replace(' ', '+') or self.email.split('@')[0]
        return f'https://ui-avatars.com/api/?name={name}&background=random'


class UserProfile(models.Model):
    """
    Kullanıcı profil genişletmesi.
    Role-specific ek bilgiler için kullanılır.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    
    # Öğrenci bilgileri
    student_id = models.CharField(
        _('Öğrenci No'),
        max_length=50,
        blank=True,
    )
    department = models.CharField(
        _('Bölüm'),
        max_length=100,
        blank=True,
    )
    
    # Eğitmen bilgileri
    expertise_areas = models.JSONField(
        _('Uzmanlık Alanları'),
        default=list,
        blank=True,
    )
    certificates = models.JSONField(
        _('Sertifikalar'),
        default=list,
        blank=True,
    )
    
    # Sosyal medya
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Kullanıcı Profili')
        verbose_name_plural = _('Kullanıcı Profilleri')

    def __str__(self):
        return f'{self.user.email} profili'

