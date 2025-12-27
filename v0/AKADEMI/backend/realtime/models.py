"""
Realtime Models
===============

Mesajlaşma ve bildirim modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class Conversation(TenantAwareModel):
    """
    Mesajlaşma konuşması.
    
    Özel (1-1) veya grup konuşması olabilir.
    """

    class Type(models.TextChoices):
        """Konuşma türleri."""
        PRIVATE = 'private', _('Özel')
        GROUP = 'group', _('Grup')
        CLASS = 'class', _('Sınıf')
        COURSE = 'course', _('Kurs')
        SUPPORT = 'support', _('Destek')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        _('Konuşma Adı'),
        max_length=100,
        blank=True,
        help_text=_('Grup konuşmaları için'),
    )
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=Type.choices,
        default=Type.PRIVATE,
    )
    
    # Katılımcılar
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations',
        verbose_name=_('Katılımcılar'),
    )
    
    # Grup ayarları
    avatar = models.URLField(
        _('Grup Görseli'),
        blank=True,
    )
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # İlişkili nesne (sınıf veya kurs için)
    related_type = models.CharField(
        _('İlişkili Tür'),
        max_length=50,
        blank=True,
    )
    related_id = models.CharField(
        _('İlişkili ID'),
        max_length=50,
        blank=True,
    )
    
    # Ayarlar
    is_muted = models.BooleanField(
        _('Sessiz'),
        default=False,
    )
    is_archived = models.BooleanField(
        _('Arşivlenmiş'),
        default=False,
    )
    
    # Son mesaj bilgisi (performans için)
    last_message_at = models.DateTimeField(
        _('Son Mesaj Zamanı'),
        null=True,
        blank=True,
    )
    last_message_preview = models.CharField(
        _('Son Mesaj Önizleme'),
        max_length=100,
        blank=True,
    )
    message_count = models.PositiveIntegerField(
        _('Mesaj Sayısı'),
        default=0,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Konuşma')
        verbose_name_plural = _('Konuşmalar')
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['type', 'tenant']),
            models.Index(fields=['last_message_at']),
        ]

    def __str__(self):
        return self.name or f"Konuşma {self.id}"

    def get_display_name(self, for_user=None):
        """
        Görüntülenecek isim.
        
        Özel konuşmalarda karşı tarafın adını döndürür.
        """
        if self.name:
            return self.name
        
        if self.type == self.Type.PRIVATE and for_user:
            other = self.participants.exclude(id=for_user.id).first()
            if other:
                return other.full_name
        
        return f"Konuşma"


class ConversationParticipant(models.Model):
    """
    Konuşma katılımcısı.
    
    Kullanıcının konuşmaya katılım bilgileri.
    """

    class Role(models.TextChoices):
        """Katılımcı rolleri."""
        MEMBER = 'member', _('Üye')
        ADMIN = 'admin', _('Yönetici')
        OWNER = 'owner', _('Sahip')

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='conversation_participants',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships',
    )
    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    
    # Bildirim ayarları
    is_muted = models.BooleanField(
        _('Sessiz'),
        default=False,
    )
    muted_until = models.DateTimeField(
        _('Sessiz Bitiş'),
        null=True,
        blank=True,
    )
    
    # Okunma durumu
    last_read_at = models.DateTimeField(
        _('Son Okuma'),
        null=True,
        blank=True,
    )
    unread_count = models.PositiveIntegerField(
        _('Okunmamış'),
        default=0,
    )
    
    # Sabitlenmiş mi?
    is_pinned = models.BooleanField(
        _('Sabitlenmiş'),
        default=False,
    )
    
    # Tarihler
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Konuşma Katılımcısı')
        verbose_name_plural = _('Konuşma Katılımcıları')
        unique_together = ['conversation', 'user']

    def __str__(self):
        return f"{self.user.email} - {self.conversation}"


class ChatMessage(models.Model):
    """
    Sohbet mesajı.
    
    Konuşma içindeki mesajlar.
    """

    class Type(models.TextChoices):
        """Mesaj türleri."""
        TEXT = 'text', _('Metin')
        IMAGE = 'image', _('Görsel')
        FILE = 'file', _('Dosya')
        AUDIO = 'audio', _('Ses')
        VIDEO = 'video', _('Video')
        SYSTEM = 'system', _('Sistem')
        REPLY = 'reply', _('Yanıt')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages',
    )
    
    # Mesaj içeriği
    type = models.CharField(
        _('Tür'),
        max_length=20,
        choices=Type.choices,
        default=Type.TEXT,
    )
    content = models.TextField(
        _('İçerik'),
    )
    
    # Dosya eki
    attachment = models.ForeignKey(
        'storage.FileUpload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    
    # Yanıtlanan mesaj
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
    )
    
    # Metadata
    metadata = models.JSONField(
        _('Ek Veri'),
        default=dict,
        blank=True,
    )
    
    # Düzenleme
    is_edited = models.BooleanField(
        _('Düzenlendi'),
        default=False,
    )
    edited_at = models.DateTimeField(
        _('Düzenleme Zamanı'),
        null=True,
        blank=True,
    )
    
    # Silinme
    is_deleted = models.BooleanField(
        _('Silindi'),
        default=False,
    )
    deleted_at = models.DateTimeField(
        _('Silinme Zamanı'),
        null=True,
        blank=True,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Sohbet Mesajı')
        verbose_name_plural = _('Sohbet Mesajları')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        preview = self.content[:50] if self.content else self.type
        return f"{self.sender}: {preview}"

    @property
    def content_preview(self) -> str:
        """Kısa önizleme."""
        if self.is_deleted:
            return "Bu mesaj silindi"
        if self.type == self.Type.IMAGE:
            return "📷 Fotoğraf"
        if self.type == self.Type.FILE:
            return "📎 Dosya"
        if self.type == self.Type.AUDIO:
            return "🎵 Ses"
        if self.type == self.Type.VIDEO:
            return "🎬 Video"
        return self.content[:100] if self.content else ""


class MessageReadStatus(models.Model):
    """
    Mesaj okunma durumu.
    
    Her kullanıcı için mesaj okunma bilgisi.
    """
    
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='read_statuses',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_read_statuses',
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mesaj Okunma Durumu')
        verbose_name_plural = _('Mesaj Okunma Durumları')
        unique_together = ['message', 'user']


class NotificationPreference(models.Model):
    """
    Bildirim tercihleri.
    
    Kullanıcının bildirim alma tercihleri.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    
    # Kanal tercihleri
    email_enabled = models.BooleanField(
        _('E-posta Bildirimleri'),
        default=True,
    )
    push_enabled = models.BooleanField(
        _('Push Bildirimleri'),
        default=True,
    )
    sms_enabled = models.BooleanField(
        _('SMS Bildirimleri'),
        default=False,
    )
    
    # Tür bazlı tercihler
    notify_assignments = models.BooleanField(
        _('Ödev Bildirimleri'),
        default=True,
    )
    notify_grades = models.BooleanField(
        _('Not Bildirimleri'),
        default=True,
    )
    notify_messages = models.BooleanField(
        _('Mesaj Bildirimleri'),
        default=True,
    )
    notify_live_sessions = models.BooleanField(
        _('Canlı Ders Bildirimleri'),
        default=True,
    )
    notify_announcements = models.BooleanField(
        _('Duyuru Bildirimleri'),
        default=True,
    )
    notify_system = models.BooleanField(
        _('Sistem Bildirimleri'),
        default=True,
    )
    
    # Sessiz saatler
    quiet_hours_enabled = models.BooleanField(
        _('Sessiz Saatler Aktif'),
        default=False,
    )
    quiet_hours_start = models.TimeField(
        _('Sessiz Saat Başlangıç'),
        null=True,
        blank=True,
    )
    quiet_hours_end = models.TimeField(
        _('Sessiz Saat Bitiş'),
        null=True,
        blank=True,
    )
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Bildirim Tercihi')
        verbose_name_plural = _('Bildirim Tercihleri')

    def __str__(self):
        return f"{self.user.email} - Bildirim Tercihleri"

    def should_notify(self, notification_type: str) -> bool:
        """Belirtilen türde bildirim gönderilmeli mi?"""
        type_map = {
            'ASSIGNMENT': self.notify_assignments,
            'GRADE': self.notify_grades,
            'MESSAGE': self.notify_messages,
            'LIVE': self.notify_live_sessions,
            'ANNOUNCEMENT': self.notify_announcements,
            'SYSTEM': self.notify_system,
        }
        return type_map.get(notification_type, True)

