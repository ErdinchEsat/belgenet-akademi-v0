"""
Tenant Serializers
==================

Akademi API serializer'ları.
"""

from rest_framework import serializers

from .models import Tenant, TenantSettings


class TenantSerializer(serializers.ModelSerializer):
    """
    Akademi bilgileri serializer.
    Frontend Tenant interface'i ile uyumlu.
    """
    
    color = serializers.CharField(source='primary_color', read_only=True)
    themeConfig = serializers.DictField(source='theme_config', read_only=True)
    modules = serializers.DictField(source='modules_config', read_only=True)
    storageUsedPercent = serializers.FloatField(source='storage_used_percent', read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'logo',
            'color',
            'type',
            'themeConfig',
            'modules',
            'is_active',
            'is_verified',
            # Stats
            'stats_users',
            'stats_courses',
            'storage_limit_gb',
            'storageUsedPercent',
            'user_limit',
            'course_limit',
            # Dates
            'created_at',
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'stats_users',
            'stats_courses',
            'created_at',
        ]


class TenantCreateSerializer(serializers.ModelSerializer):
    """
    Akademi oluşturma serializer.
    Super Admin için.
    """

    class Meta:
        model = Tenant
        fields = [
            'name',
            'slug',
            'description',
            'logo',
            'type',
            'email',
            'phone',
            'website',
            # Limitler
            'storage_limit_gb',
            'user_limit',
            'course_limit',
            # Modüller
            'module_live_class',
            'module_quiz',
            'module_exam',
            'module_assignment',
            'module_certificate',
            'module_forum',
            'module_ai_assistant',
        ]


class TenantUpdateSerializer(serializers.ModelSerializer):
    """
    Akademi güncelleme serializer.
    Tenant Admin için.
    """

    class Meta:
        model = Tenant
        fields = [
            'name',
            'description',
            'logo',
            'favicon',
            'email',
            'phone',
            'website',
            'address',
            # Tema
            'primary_color',
            'sidebar_position',
            'sidebar_color',
            'sidebar_content_color',
            'main_background_color',
            'button_radius',
        ]


class TenantSettingsSerializer(serializers.ModelSerializer):
    """
    Akademi ayarları serializer.
    """

    class Meta:
        model = TenantSettings
        exclude = ['tenant', 'created_at', 'updated_at']


class TenantMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal akademi bilgileri.
    Dropdown ve liste görünümleri için.
    """

    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'logo', 'type']


class TenantStatsSerializer(serializers.Serializer):
    """
    Akademi istatistikleri serializer.
    """
    
    total_users = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_instructors = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    active_courses = serializers.IntegerField()
    storage_used_mb = serializers.IntegerField()
    storage_limit_gb = serializers.IntegerField()
    storage_used_percent = serializers.FloatField()

