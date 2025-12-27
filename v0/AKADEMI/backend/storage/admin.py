"""
Storage Admin
=============

Django admin panel yapılandırması.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import FileUpload, ImageVariant, UploadSession


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    """FileUpload admin."""
    
    list_display = [
        'id',
        'original_filename',
        'category',
        'file_size_display',
        'status',
        'uploaded_by',
        'tenant',
        'created_at',
    ]
    list_filter = ['category', 'status', 'is_public', 'tenant', 'created_at']
    search_fields = ['original_filename', 'uploaded_by__email', 'file_hash']
    readonly_fields = [
        'id', 'file_hash', 'file_size', 'mime_type',
        'width', 'height', 'access_count', 'created_at', 'updated_at',
        'file_preview',
    ]
    raw_id_fields = ['uploaded_by', 'tenant']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Dosya Bilgileri', {
            'fields': (
                'id', 'file', 'original_filename', 'file_preview',
                'category', 'status', 'is_public',
            )
        }),
        ('Teknik Bilgiler', {
            'fields': (
                'mime_type', 'file_size', 'file_hash',
                'width', 'height',
            ),
            'classes': ('collapse',),
        }),
        ('İlişkiler', {
            'fields': (
                'uploaded_by', 'tenant',
                'content_type', 'object_id',
            )
        }),
        ('Meta', {
            'fields': ('metadata', 'access_count', 'expires_at'),
            'classes': ('collapse',),
        }),
        ('Tarihler', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    def file_preview(self, obj):
        """Görsel önizleme."""
        if obj.is_image and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.file.url
            )
        return '-'
    file_preview.short_description = 'Önizleme'


@admin.register(ImageVariant)
class ImageVariantAdmin(admin.ModelAdmin):
    """ImageVariant admin."""
    
    list_display = ['original', 'size', 'width', 'height', 'file_size', 'created_at']
    list_filter = ['size', 'created_at']
    raw_id_fields = ['original']


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    """UploadSession admin."""
    
    list_display = [
        'id', 'filename', 'uploaded_by',
        'uploaded_chunks', 'total_chunks',
        'progress_display', 'is_completed', 'created_at',
    ]
    list_filter = ['is_completed', 'category', 'created_at']
    search_fields = ['filename', 'uploaded_by__email']
    readonly_fields = ['id', 'progress_percent', 'created_at']
    raw_id_fields = ['uploaded_by', 'tenant', 'completed_file']
    
    def progress_display(self, obj):
        """İlerleme göstergesi."""
        percent = obj.progress_percent
        color = 'green' if percent == 100 else 'orange' if percent > 50 else 'red'
        return format_html(
            '<span style="color: {};">{} / {} ({}%)</span>',
            color, obj.uploaded_chunks, obj.total_chunks, percent
        )
    progress_display.short_description = 'İlerleme'

