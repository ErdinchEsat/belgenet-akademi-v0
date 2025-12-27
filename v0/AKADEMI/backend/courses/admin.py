"""
Course Admin
============

Django Admin konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    ContentProgress,
    Course,
    CourseContent,
    CourseModule,
    Enrollment,
)


class CourseModuleInline(admin.TabularInline):
    """Modül inline."""
    model = CourseModule
    extra = 0
    show_change_link = True


class CourseContentInline(admin.TabularInline):
    """İçerik inline."""
    model = CourseContent
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Course Admin."""
    
    list_display = [
        'title',
        'tenant',
        'category',
        'level',
        'status_badge',
        'enrolled_count',
        'rating_display',
        'created_at',
    ]
    list_filter = [
        'status',
        'level',
        'category',
        'is_free',
        'tenant',
        'created_at',
    ]
    search_fields = ['title', 'description', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['instructors']
    inlines = [CourseModuleInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'short_description')
        }),
        (_('Görsel & Kategori'), {
            'fields': ('cover_url', 'category', 'language', 'level', 'tags'),
        }),
        (_('İlişkiler'), {
            'fields': ('tenant', 'instructors'),
        }),
        (_('Fiyatlandırma'), {
            'fields': ('is_free', 'price', 'currency'),
        }),
        (_('Yayın'), {
            'fields': ('visibility', 'is_published', 'publish_at'),
        }),
        (_('Tamamlama'), {
            'fields': ('certificate_enabled', 'completion_percent', 'welcome_message'),
        }),
        (_('Workflow'), {
            'fields': ('status', 'teacher_submit_note', 'admin_revision_note'),
        }),
        (_('İstatistikler'), {
            'fields': ('enrolled_count', 'rating', 'rating_count', 'total_duration_minutes'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'pending_admin_setup': 'orange',
            'needs_revision': 'red',
            'published': 'green',
            'archived': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _('Durum')

    def rating_display(self, obj):
        if obj.rating_count == 0:
            return '-'
        return f'⭐ {obj.rating} ({obj.rating_count})'
    rating_display.short_description = _('Puan')


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    """CourseModule Admin."""
    
    list_display = ['title', 'course', 'order', 'is_published', 'content_count']
    list_filter = ['is_published', 'course__tenant']
    search_fields = ['title', 'course__title']
    ordering = ['course', 'order']
    inlines = [CourseContentInline]

    def content_count(self, obj):
        return obj.contents.count()
    content_count.short_description = _('İçerik Sayısı')


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    """CourseContent Admin."""
    
    list_display = ['title', 'module', 'type', 'order', 'duration_minutes', 'is_ready']
    list_filter = ['type', 'is_ready', 'is_locked', 'module__course__tenant']
    search_fields = ['title', 'module__title', 'module__course__title']
    ordering = ['module', 'order']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Enrollment Admin."""
    
    list_display = [
        'user',
        'course',
        'status',
        'progress_percent',
        'enrolled_at',
        'completed_at',
    ]
    list_filter = ['status', 'course__tenant', 'enrolled_at']
    search_fields = ['user__email', 'course__title']
    raw_id_fields = ['user', 'course']
    date_hierarchy = 'enrolled_at'


@admin.register(ContentProgress)
class ContentProgressAdmin(admin.ModelAdmin):
    """ContentProgress Admin."""
    
    list_display = [
        'get_user',
        'content',
        'is_completed',
        'progress_percent',
        'score',
        'attempts',
    ]
    list_filter = ['is_completed', 'content__type']
    raw_id_fields = ['enrollment', 'content']

    def get_user(self, obj):
        return obj.enrollment.user.email
    get_user.short_description = _('Kullanıcı')

