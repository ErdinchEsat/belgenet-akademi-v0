"""
User Admin
==========

Django Admin konfigürasyonu.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """UserProfile inline."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil Detayları'
    fk_name = 'user'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin."""
    
    list_display = [
        'email',
        'full_name',
        'role',
        'tenant',
        'is_active',
        'date_joined',
    ]
    list_filter = [
        'role',
        'is_active',
        'is_staff',
        'tenant',
        'date_joined',
    ]
    search_fields = [
        'email',
        'first_name',
        'last_name',
    ]
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Kişisel Bilgiler'), {
            'fields': (
                'first_name',
                'last_name',
                'avatar',
                'title',
                'bio',
                'phone',
            )
        }),
        (_('Rol & Kurum'), {
            'fields': ('role', 'tenant')
        }),
        (_('Gamification'), {
            'fields': ('points', 'streak'),
            'classes': ('collapse',),
        }),
        (_('Tercihler'), {
            'fields': ('language', 'timezone', 'notify_email', 'notify_push'),
            'classes': ('collapse',),
        }),
        (_('İzinler'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Önemli Tarihler'), {
            'fields': ('last_login', 'date_joined', 'email_verified_at'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'role',
                'tenant',
            ),
        }),
    )
    
    inlines = [UserProfileInline]
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = _('Ad Soyad')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """UserProfile Admin."""
    
    list_display = ['user', 'student_id', 'department', 'created_at']
    search_fields = ['user__email', 'student_id']
    raw_id_fields = ['user']

