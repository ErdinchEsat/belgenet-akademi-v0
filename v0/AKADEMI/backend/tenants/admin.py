"""
Tenant Admin
============

Django Admin konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Tenant, TenantSettings


class TenantSettingsInline(admin.StackedInline):
    """TenantSettings inline."""
    model = TenantSettings
    can_delete = False
    verbose_name_plural = 'Ayarlar'
    fk_name = 'tenant'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Tenant Admin."""
    
    list_display = [
        'name',
        'slug',
        'type',
        'colored_status',
        'stats_users',
        'stats_courses',
        'storage_info',
        'created_at',
    ]
    list_filter = [
        'type',
        'is_active',
        'is_verified',
        'module_live_class',
        'module_quiz',
        'created_at',
    ]
    search_fields = ['name', 'slug', 'email']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'type')
        }),
        (_('Görsel'), {
            'fields': ('logo', 'favicon'),
            'classes': ('collapse',),
        }),
        (_('İletişim'), {
            'fields': ('email', 'phone', 'website', 'address'),
            'classes': ('collapse',),
        }),
        (_('Tema'), {
            'fields': (
                'primary_color',
                'sidebar_position',
                'sidebar_color',
                'sidebar_content_color',
                'main_background_color',
                'button_radius',
            ),
            'classes': ('collapse',),
        }),
        (_('Limitler'), {
            'fields': ('storage_limit_gb', 'user_limit', 'course_limit'),
        }),
        (_('Modüller'), {
            'fields': (
                'module_live_class',
                'module_quiz',
                'module_exam',
                'module_assignment',
                'module_certificate',
                'module_forum',
                'module_ai_assistant',
            ),
        }),
        (_('Durum'), {
            'fields': ('is_active', 'is_verified', 'trial_ends_at'),
        }),
        (_('İstatistikler'), {
            'fields': ('stats_users', 'stats_courses', 'stats_storage_used_mb'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['stats_users', 'stats_courses', 'stats_storage_used_mb']
    inlines = [TenantSettingsInline]

    def colored_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Aktif</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Pasif</span>'
        )
    colored_status.short_description = _('Durum')

    def storage_info(self, obj):
        used = obj.stats_storage_used_mb / 1024
        limit = obj.storage_limit_gb
        percent = obj.storage_used_percent
        
        color = 'green'
        if percent > 80:
            color = 'red'
        elif percent > 60:
            color = 'orange'
        
        return format_html(
            '<span style="color: {};">{:.1f} / {} GB ({:.0f}%)</span>',
            color, used, limit, percent
        )
    storage_info.short_description = _('Depolama')


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    """TenantSettings Admin."""
    
    list_display = ['tenant', 'allow_self_registration', 'require_course_approval']
    list_filter = ['allow_self_registration', 'require_course_approval']
    raw_id_fields = ['tenant']

