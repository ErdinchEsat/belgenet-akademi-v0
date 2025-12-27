"""
Sequencing Admin
================

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ContentLockPolicy, ContentUnlockState


@admin.register(ContentLockPolicy)
class ContentLockPolicyAdmin(admin.ModelAdmin):
    """ContentLockPolicy admin konfigürasyonu."""
    
    list_display = [
        'id',
        'content_title',
        'policy_type',
        'priority',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'policy_type',
        'is_active',
        'tenant',
    ]
    
    search_fields = [
        'content__title',
        'course__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-priority', 'policy_type']
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'


@admin.register(ContentUnlockState)
class ContentUnlockStateAdmin(admin.ModelAdmin):
    """ContentUnlockState admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'lock_status',
        'unlocked_at',
        'last_evaluated_at',
    ]
    
    list_filter = [
        'is_unlocked',
        'tenant',
        'unlocked_at',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'user',
        'course',
        'content',
        'is_unlocked',
        'unlocked_at',
        'unlock_reason',
        'evaluation_state',
        'last_evaluated_at',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-updated_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def lock_status(self, obj):
        if obj.is_unlocked:
            return format_html(
                '<span style="color: green; font-weight: bold;">🔓 Açık</span>'
            )
        return format_html(
            '<span style="color: red;">🔒 Kilitli</span>'
        )
    lock_status.short_description = 'Durum'

