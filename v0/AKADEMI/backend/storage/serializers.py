"""
Storage Serializers
===================

Dosya yükleme API serializer'ları.
"""

from rest_framework import serializers

from .models import FileUpload, ImageVariant, UploadSession
from .validators import validate_file, FILE_SIZE_LIMITS


class FileUploadSerializer(serializers.ModelSerializer):
    """FileUpload model serializer."""
    
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()
    is_document = serializers.ReadOnlyField()
    extension = serializers.ReadOnlyField()
    uploaded_by_name = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id',
            'original_filename',
            'category',
            'mime_type',
            'file_size',
            'file_size_display',
            'file_url',
            'status',
            'is_public',
            'is_image',
            'is_video',
            'is_document',
            'extension',
            'width',
            'height',
            'uploaded_by',
            'uploaded_by_name',
            'content_type',
            'object_id',
            'metadata',
            'access_count',
            'variants',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'mime_type', 'file_size', 'file_hash',
            'status', 'width', 'height', 'uploaded_by',
            'access_count', 'created_at', 'updated_at',
        ]
    
    def get_file_url(self, obj):
        from .services import StorageService
        return StorageService.get_file_url(obj)
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.full_name or obj.uploaded_by.email
        return None
    
    def get_variants(self, obj):
        if not obj.is_image:
            return {}
        variants = obj.variants.all()
        return {v.size: v.url for v in variants}


class FileUploadCreateSerializer(serializers.Serializer):
    """Dosya yükleme serializer."""
    
    file = serializers.FileField()
    category = serializers.ChoiceField(
        choices=FileUpload.Category.choices,
        default=FileUpload.Category.OTHER,
    )
    content_type = serializers.CharField(required=False, allow_blank=True)
    object_id = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(default=False)
    metadata = serializers.JSONField(required=False, default=dict)
    create_variants = serializers.BooleanField(
        default=True,
        help_text='Görsel ise varyantlar oluşturulsun mu?'
    )
    
    def validate_file(self, value):
        """Dosya validasyonu."""
        category = self.initial_data.get('category', 'other')
        validate_file(value, category)
        return value
    
    def validate(self, attrs):
        """Genel validasyon."""
        category = attrs.get('category', 'other')
        file = attrs.get('file')
        
        # Dosya boyutu kontrolü (kategori bazlı)
        max_size = FILE_SIZE_LIMITS.get(category, FILE_SIZE_LIMITS['default'])
        if file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError({
                'file': f'Dosya boyutu çok büyük. Maksimum: {max_mb} MB'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Dosya yükle."""
        from .services import StorageService, ImageService
        
        file = validated_data.pop('file')
        create_variants = validated_data.pop('create_variants', True)
        
        user = self.context['request'].user
        tenant = user.tenant
        
        file_upload = StorageService.upload_file(
            file=file,
            user=user,
            tenant=tenant,
            **validated_data
        )
        
        # Görsel ise varyantlar oluştur
        if create_variants and file_upload.is_image:
            ImageService.create_variants(file_upload)
        
        return file_upload


class FileUploadListSerializer(serializers.ModelSerializer):
    """Dosya listesi için basit serializer."""
    
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.ReadOnlyField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id',
            'original_filename',
            'category',
            'mime_type',
            'file_size_display',
            'file_url',
            'status',
            'is_public',
            'created_at',
        ]
    
    def get_file_url(self, obj):
        from .services import StorageService
        return StorageService.get_file_url(obj)


class ImageVariantSerializer(serializers.ModelSerializer):
    """ImageVariant serializer."""
    
    url = serializers.ReadOnlyField()
    
    class Meta:
        model = ImageVariant
        fields = ['size', 'width', 'height', 'file_size', 'url']


class UploadSessionSerializer(serializers.ModelSerializer):
    """UploadSession serializer."""
    
    progress_percent = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = UploadSession
        fields = [
            'id',
            'filename',
            'file_size',
            'chunk_size',
            'total_chunks',
            'uploaded_chunks',
            'progress_percent',
            'is_completed',
            'is_expired',
            'category',
            'expires_at',
            'created_at',
        ]


class UploadSessionCreateSerializer(serializers.Serializer):
    """Chunk upload oturumu oluşturma."""
    
    filename = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(
        choices=FileUpload.Category.choices,
        default=FileUpload.Category.OTHER,
    )
    chunk_size = serializers.IntegerField(
        default=5 * 1024 * 1024,  # 5MB
        min_value=1024 * 1024,    # 1MB min
        max_value=50 * 1024 * 1024,  # 50MB max
    )
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_file_size(self, value):
        """Dosya boyutu kontrolü."""
        category = self.initial_data.get('category', 'other')
        max_size = FILE_SIZE_LIMITS.get(category, FILE_SIZE_LIMITS['default'])
        
        # Chunk upload için daha yüksek limit
        max_chunk_upload_size = 1024 * 1024 * 1024 * 5  # 5GB
        
        if value > max_chunk_upload_size:
            raise serializers.ValidationError(
                f'Dosya boyutu çok büyük. Maksimum: 5 GB'
            )
        
        return value
    
    def create(self, validated_data):
        from .services import StorageService
        
        user = self.context['request'].user
        tenant = user.tenant
        
        return StorageService.create_upload_session(
            user=user,
            tenant=tenant,
            **validated_data
        )


class ChunkUploadSerializer(serializers.Serializer):
    """Chunk yükleme."""
    
    chunk = serializers.FileField()
    chunk_number = serializers.IntegerField(min_value=0)
    
    def validate_chunk_number(self, value):
        session = self.context.get('session')
        if session and value >= session.total_chunks:
            raise serializers.ValidationError(
                f'Geçersiz chunk numarası. Maksimum: {session.total_chunks - 1}'
            )
        return value


class ProfileAvatarSerializer(serializers.Serializer):
    """Profil resmi yükleme."""
    
    file = serializers.ImageField()
    
    def validate_file(self, value):
        # Sadece görsel izinli
        validate_file(value, 'profile')
        return value
    
    def create(self, validated_data):
        from .services import StorageService, ImageService
        
        user = self.context['request'].user
        file = validated_data['file']
        
        # Mevcut avatarı sil
        old_avatar = FileUpload.objects.filter(
            uploaded_by=user,
            category=FileUpload.Category.PROFILE,
            status=FileUpload.Status.COMPLETED,
        ).first()
        
        if old_avatar:
            StorageService.delete_file(old_avatar)
        
        # Yeni avatar yükle
        file_upload = StorageService.upload_file(
            file=file,
            category=FileUpload.Category.PROFILE,
            user=user,
            tenant=user.tenant,
            is_public=True,
        )
        
        # Varyantlar oluştur
        ImageService.create_variants(file_upload, ['thumbnail', 'small', 'medium'])
        
        # Kullanıcı avatar URL'ini güncelle
        from .services import StorageService as SS
        user.avatar = SS.get_file_url(file_upload)
        user.save(update_fields=['avatar'])
        
        return file_upload


class AssignmentFileSerializer(serializers.Serializer):
    """Ödev dosyası yükleme."""
    
    file = serializers.FileField()
    assignment_id = serializers.IntegerField()
    
    def validate_file(self, value):
        validate_file(value, 'submission')
        return value
    
    def create(self, validated_data):
        from .services import StorageService
        
        user = self.context['request'].user
        file = validated_data['file']
        assignment_id = validated_data['assignment_id']
        
        file_upload = StorageService.upload_file(
            file=file,
            category=FileUpload.Category.SUBMISSION,
            user=user,
            tenant=user.tenant,
            content_type='student.AssignmentSubmission',
            object_id=str(assignment_id),
        )
        
        return file_upload


class CourseMaterialSerializer(serializers.Serializer):
    """Kurs materyali yükleme."""
    
    file = serializers.FileField()
    course_id = serializers.IntegerField()
    module_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_file(self, value):
        validate_file(value, 'material')
        return value
    
    def create(self, validated_data):
        from .services import StorageService
        
        user = self.context['request'].user
        file = validated_data['file']
        course_id = validated_data['course_id']
        module_id = validated_data.get('module_id')
        
        metadata = {
            'title': validated_data.get('title', file.name),
            'description': validated_data.get('description', ''),
        }
        
        if module_id:
            metadata['module_id'] = module_id
        
        file_upload = StorageService.upload_file(
            file=file,
            category=FileUpload.Category.MATERIAL,
            user=user,
            tenant=user.tenant,
            content_type='courses.Course',
            object_id=str(course_id),
            metadata=metadata,
        )
        
        return file_upload

