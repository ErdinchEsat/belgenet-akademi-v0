"""
Certificate Admin
=================

Django admin panel yapılandırması.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Certificate, CertificateTemplate, CertificateDownload


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    """CertificateTemplate admin."""
    
    list_display = ['name', 'tenant', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active', 'tenant']
    search_fields = ['name', 'description']
    raw_id_fields = ['tenant']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Certificate admin."""
    
    list_display = [
        'verification_code',
        'user_display',
        'course_display',
        'completion_date',
        'status',
        'issued_at',
    ]
    list_filter = ['status', 'tenant', 'completion_date']
    search_fields = ['verification_code', 'user__email', 'user__first_name', 'course__title']
    readonly_fields = [
        'id', 'verification_code', 'share_url',
        'created_at', 'updated_at', 'pdf_preview',
    ]
    raw_id_fields = ['user', 'course', 'enrollment', 'template', 'issued_by', 'tenant']
    date_hierarchy = 'completion_date'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': (
                'id', 'verification_code', 'title', 'description',
            )
        }),
        ('İlişkiler', {
            'fields': (
                'user', 'course', 'enrollment', 'tenant', 'template',
            )
        }),
        ('Tamamlama Bilgileri', {
            'fields': (
                'completion_date', 'completion_percent',
                'final_score', 'total_hours', 'skills',
            )
        }),
        ('Durum', {
            'fields': (
                'status', 'is_public', 'share_url',
                'issued_by', 'issued_at', 'revoked_at',
            )
        }),
        ('Dosyalar', {
            'fields': ('pdf_file', 'pdf_preview'),
        }),
        ('Meta', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['issue_certificates', 'revoke_certificates', 'regenerate_pdfs']
    
    def user_display(self, obj):
        return obj.user.full_name
    user_display.short_description = 'Kullanıcı'
    
    def course_display(self, obj):
        return obj.course.title
    course_display.short_description = 'Kurs'
    
    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">PDF İndir</a>',
                obj.pdf_file.url
            )
        return '-'
    pdf_preview.short_description = 'PDF'
    
    @admin.action(description='Seçili sertifikaları ver')
    def issue_certificates(self, request, queryset):
        count = 0
        for cert in queryset.filter(status='pending'):
            cert.issue(request.user)
            count += 1
        self.message_user(request, f'{count} sertifika verildi.')
    
    @admin.action(description='Seçili sertifikaları iptal et')
    def revoke_certificates(self, request, queryset):
        count = queryset.filter(status='issued').update(status='revoked')
        self.message_user(request, f'{count} sertifika iptal edildi.')
    
    @admin.action(description='PDF\'leri yeniden oluştur')
    def regenerate_pdfs(self, request, queryset):
        from .services import CertificateService
        count = 0
        for cert in queryset:
            try:
                CertificateService.regenerate_pdf(cert)
                count += 1
            except Exception as e:
                self.message_user(request, f'{cert.verification_code} için hata: {e}', level='error')
        self.message_user(request, f'{count} PDF yeniden oluşturuldu.')


@admin.register(CertificateDownload)
class CertificateDownloadAdmin(admin.ModelAdmin):
    """CertificateDownload admin."""
    
    list_display = ['certificate', 'downloaded_by', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['certificate__verification_code', 'downloaded_by__email']
    raw_id_fields = ['certificate', 'downloaded_by']
    date_hierarchy = 'downloaded_at'

