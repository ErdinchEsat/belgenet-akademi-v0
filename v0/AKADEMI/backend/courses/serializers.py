"""
Course Serializers
==================

Kurs API serializer'ları.
"""

from rest_framework import serializers

from backend.users.serializers import UserMinimalSerializer

from .models import (
    ContentProgress,
    Course,
    CourseContent,
    CourseModule,
    Enrollment,
)


class CourseContentSerializer(serializers.ModelSerializer):
    """İçerik serializer."""
    
    duration = serializers.CharField(read_only=True)

    class Meta:
        model = CourseContent
        fields = [
            'id',
            'title',
            'type',
            'description',
            'duration',
            'order',
            'is_locked',
            'is_ready',
            'is_free_preview',
        ]


class CourseContentDetailSerializer(CourseContentSerializer):
    """İçerik detay serializer (data dahil)."""

    class Meta(CourseContentSerializer.Meta):
        fields = CourseContentSerializer.Meta.fields + ['data']


class CourseModuleSerializer(serializers.ModelSerializer):
    """Modül serializer."""
    
    contents = CourseContentSerializer(many=True, read_only=True)
    lessons = serializers.SerializerMethodField()

    class Meta:
        model = CourseModule
        fields = [
            'id',
            'title',
            'description',
            'order',
            'is_published',
            'contents',
            'lessons',  # Frontend uyumluluğu
        ]

    def get_lessons(self, obj):
        """Frontend CourseModule.lessons uyumu."""
        contents = obj.contents.all()
        return [
            {
                'id': str(c.id),
                'title': c.title,
                'type': c.type.lower(),
                'duration': c.duration,
                'isReady': c.is_ready,
            }
            for c in contents
        ]


class CourseSerializer(serializers.ModelSerializer):
    """Kurs serializer."""
    
    instructors = UserMinimalSerializer(many=True, read_only=True)
    coverUrl = serializers.CharField(source='cover_url_display', read_only=True)
    stats = serializers.DictField(read_only=True)
    pricing = serializers.DictField(read_only=True)
    publish = serializers.DictField(read_only=True)
    completion = serializers.DictField(read_only=True)
    curriculum = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'short_description',
            'coverUrl',
            'category',
            'language',
            'level',
            'tags',
            'instructors',
            'stats',
            'pricing',
            'publish',
            'completion',
            'curriculum',
            'status',
            'welcome_message',
            'updated_at',
        ]

    def get_curriculum(self, obj):
        """Frontend Course.curriculum uyumu."""
        modules = obj.modules.all().prefetch_related('contents')
        return {
            'modules': CourseModuleSerializer(modules, many=True).data
        }


class CourseListSerializer(serializers.ModelSerializer):
    """Kurs liste serializer (özet)."""
    
    instructors = UserMinimalSerializer(many=True, read_only=True)
    coverUrl = serializers.CharField(source='cover_url_display', read_only=True)
    stats = serializers.DictField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'slug',
            'short_description',
            'coverUrl',
            'category',
            'level',
            'instructors',
            'stats',
            'is_free',
            'price',
            'currency',
            'status',
        ]


class CourseCreateSerializer(serializers.ModelSerializer):
    """Kurs oluşturma serializer."""

    class Meta:
        model = Course
        fields = [
            'title',
            'slug',
            'description',
            'short_description',
            'cover_url',
            'category',
            'language',
            'level',
            'tags',
            'is_free',
            'price',
            'currency',
            'visibility',
            'certificate_enabled',
            'completion_percent',
            'welcome_message',
        ]


class CourseUpdateSerializer(serializers.ModelSerializer):
    """Kurs güncelleme serializer."""

    class Meta:
        model = Course
        fields = [
            'title',
            'description',
            'short_description',
            'cover_url',
            'category',
            'language',
            'level',
            'tags',
            'is_free',
            'price',
            'currency',
            'visibility',
            'certificate_enabled',
            'completion_percent',
            'welcome_message',
            'teacher_submit_note',
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    """Kayıt serializer."""
    
    course = CourseListSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'user',
            'course',
            'status',
            'progress_percent',
            'enrolled_at',
            'completed_at',
            'last_accessed_at',
        ]


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    """Kayıt oluşturma serializer."""

    class Meta:
        model = Enrollment
        fields = ['course']


class ContentProgressSerializer(serializers.ModelSerializer):
    """İçerik ilerleme serializer."""
    
    content = CourseContentSerializer(read_only=True)

    class Meta:
        model = ContentProgress
        fields = [
            'id',
            'content',
            'is_completed',
            'progress_percent',
            'watched_seconds',
            'last_position_seconds',
            'score',
            'attempts',
            'started_at',
            'completed_at',
        ]


class ContentProgressUpdateSerializer(serializers.ModelSerializer):
    """İçerik ilerleme güncelleme serializer."""

    class Meta:
        model = ContentProgress
        fields = [
            'progress_percent',
            'watched_seconds',
            'last_position_seconds',
            'is_completed',
        ]


class CourseMinimalSerializer(serializers.ModelSerializer):
    """Minimal kurs serializer."""

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'cover_url']

