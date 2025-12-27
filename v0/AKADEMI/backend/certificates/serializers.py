"""
Certificate Serializers
=======================

Sertifika API serializer'ları.
"""

from rest_framework import serializers

from .models import Certificate, CertificateTemplate, CertificateDownload


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """CertificateTemplate serializer."""
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'id',
            'name',
            'description',
            'background_image',
            'logo',
            'style_config',
            'is_default',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CertificateSerializer(serializers.ModelSerializer):
    """Certificate serializer."""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_category = serializers.CharField(source='course.category', read_only=True)
    institution_name = serializers.SerializerMethodField()
    verify_url = serializers.ReadOnlyField()
    pdf_url = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = [
            'id',
            'verification_code',
            'title',
            'description',
            'user',
            'user_name',
            'user_email',
            'course',
            'course_title',
            'course_category',
            'institution_name',
            'completion_date',
            'completion_percent',
            'final_score',
            'skills',
            'total_hours',
            'status',
            'is_public',
            'share_url',
            'verify_url',
            'pdf_url',
            'qr_code_url',
            'issued_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'verification_code', 'user', 'course',
            'pdf_file', 'issued_at', 'created_at',
        ]
    
    def get_institution_name(self, obj):
        return obj.tenant.name if obj.tenant else 'Akademi'
    
    def get_pdf_url(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return None
    
    def get_qr_code_url(self, obj):
        from .services import QRService
        return QRService.generate_qr_data_url(obj.verify_url, size=150)


class CertificateListSerializer(serializers.ModelSerializer):
    """Sertifika listesi için basit serializer."""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = [
            'id',
            'verification_code',
            'title',
            'user_name',
            'course_title',
            'completion_date',
            'status',
            'pdf_url',
            'created_at',
        ]
    
    def get_pdf_url(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return None


class CertificateVerifySerializer(serializers.Serializer):
    """Sertifika doğrulama sonucu."""
    
    valid = serializers.BooleanField()
    status = serializers.CharField()
    verification_code = serializers.CharField()
    holder = serializers.DictField()
    course = serializers.DictField()
    institution = serializers.DictField()
    completion_date = serializers.CharField()
    completion_percent = serializers.IntegerField()
    final_score = serializers.FloatField(allow_null=True)
    skills = serializers.ListField()
    total_hours = serializers.FloatField()
    issued_at = serializers.CharField(allow_null=True)


class CertificateCreateSerializer(serializers.Serializer):
    """Sertifika oluşturma."""
    
    enrollment_id = serializers.IntegerField()
    auto_issue = serializers.BooleanField(default=True)
    
    def validate_enrollment_id(self, value):
        from backend.courses.models import Enrollment
        
        try:
            enrollment = Enrollment.objects.get(id=value)
        except Enrollment.DoesNotExist:
            raise serializers.ValidationError("Kayıt bulunamadı")
        
        # Yetki kontrolü
        request = self.context.get('request')
        if request:
            user = request.user
            # Kullanıcı kendi kaydı veya admin/instructor olmalı
            if enrollment.user != user and user.role not in ['ADMIN', 'TENANT_ADMIN', 'SUPER_ADMIN', 'INSTRUCTOR']:
                raise serializers.ValidationError("Bu kayıt için sertifika oluşturamazsınız")
        
        return value
    
    def create(self, validated_data):
        from backend.courses.models import Enrollment
        from .services import CertificateService
        
        enrollment = Enrollment.objects.get(id=validated_data['enrollment_id'])
        request = self.context.get('request')
        
        return CertificateService.create_certificate(
            enrollment=enrollment,
            auto_issue=validated_data.get('auto_issue', True),
            issued_by=request.user if request else None,
        )


class CertificateDownloadSerializer(serializers.ModelSerializer):
    """Sertifika indirme kaydı."""
    
    class Meta:
        model = CertificateDownload
        fields = ['id', 'downloaded_at', 'ip_address']
        read_only_fields = fields

