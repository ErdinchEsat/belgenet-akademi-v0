"""
Notes Admin
===========

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import VideoNote, NoteReply, NoteReaction, NoteExport


@admin.register(VideoNote)
class VideoNoteAdmin(admin.ModelAdmin):
    """VideoNote admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'content_title',
        'note_type_badge',
        'time_display_admin',
        'visibility',
        'reply_count',
        'like_count',
        'created_at',
    ]
    
    list_filter = [
        'note_type',
        'visibility',
        'is_pinned',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
        'content__title',
        'content_text',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'share_token',
        'reply_count',
        'like_count',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def content_title(self, obj):
        return obj.content.title
    content_title.short_description = 'İçerik'
    
    def note_type_badge(self, obj):
        colors = {
            'note': 'blue',
            'question': 'orange',
            'highlight': 'yellow',
            'bookmark': 'green',
        }
        color = colors.get(obj.note_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_note_type_display()
        )
    note_type_badge.short_description = 'Tür'
    
    def time_display_admin(self, obj):
        return obj.time_display or '-'
    time_display_admin.short_description = 'Zaman'


@admin.register(NoteReply)
class NoteReplyAdmin(admin.ModelAdmin):
    """NoteReply admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'note_preview',
        'like_count',
        'created_at',
    ]
    
    list_filter = [
        'tenant',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'content_text',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'like_count',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def note_preview(self, obj):
        return obj.note.content_text[:50] + '...' if len(obj.note.content_text) > 50 else obj.note.content_text
    note_preview.short_description = 'Not'


@admin.register(NoteReaction)
class NoteReactionAdmin(admin.ModelAdmin):
    """NoteReaction admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'reaction_type',
        'target',
        'created_at',
    ]
    
    list_filter = [
        'reaction_type',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def target(self, obj):
        if obj.note:
            return f"Note: {obj.note.id}"
        return f"Reply: {obj.reply.id}"
    target.short_description = 'Hedef'


@admin.register(NoteExport)
class NoteExportAdmin(admin.ModelAdmin):
    """NoteExport admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'format',
        'status_badge',
        'created_at',
        'completed_at',
    ]
    
    list_filter = [
        'format',
        'status',
        'tenant',
    ]
    
    search_fields = [
        'user__email',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'

