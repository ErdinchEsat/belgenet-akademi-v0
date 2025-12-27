"""
Storage Views
=============

Dosya yükleme API view'ları.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import FileUpload, UploadSession
from .serializers import (
    FileUploadSerializer,
    FileUploadCreateSerializer,
    FileUploadListSerializer,
    UploadSessionSerializer,
    UploadSessionCreateSerializer,
    ChunkUploadSerializer,
    ProfileAvatarSerializer,
    AssignmentFileSerializer,
    CourseMaterialSerializer,
)
from .services import StorageService, ImageService


class FileUploadViewSet(viewsets.ModelViewSet):
    """
    Dosya yükleme API.
    
    Endpoints:
    - GET /api/v1/storage/files/ - Dosya listesi
    - POST /api/v1/storage/files/ - Dosya yükle
    - GET /api/v1/storage/files/{id}/ - Dosya detayı
    - DELETE /api/v1/storage/files/{id}/ - Dosya sil
    - GET /api/v1/storage/files/{id}/download/ - İndirme URL'i
    - POST /api/v1/storage/files/{id}/create_variants/ - Varyant oluştur
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Kullanıcının tenant'ına ait dosyaları döndür."""
        user = self.request.user
        queryset = FileUpload.objects.filter(
            tenant=user.tenant,
            status__in=[FileUpload.Status.COMPLETED, FileUpload.Status.PROCESSING],
        )
        
        # Kategori filtresi
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # İlişkili nesne filtresi
        content_type = self.request.query_params.get('content_type')
        object_id = self.request.query_params.get('object_id')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        
        # Sadece kendi dosyaları
        my_files = self.request.query_params.get('my_files')
        if my_files == 'true':
            queryset = queryset.filter(uploaded_by=user)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FileUploadCreateSerializer
        if self.action == 'list':
            return FileUploadListSerializer
        return FileUploadSerializer
    
    def perform_destroy(self, instance):
        """Soft delete."""
        StorageService.delete_file(instance, hard_delete=False)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """İndirme URL'i döndürür."""
        file_upload = self.get_object()
        file_upload.increment_access_count()
        
        url = StorageService.get_download_url(file_upload)
        return Response({'download_url': url})
    
    @action(detail=True, methods=['post'])
    def create_variants(self, request, pk=None):
        """Görsel varyantları oluşturur."""
        file_upload = self.get_object()
        
        if not file_upload.is_image:
            return Response(
                {'error': 'Bu dosya bir görsel değil'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sizes = request.data.get('sizes', None)
        variants = ImageService.create_variants(file_upload, sizes)
        
        return Response({
            'message': f'{len(variants)} varyant oluşturuldu',
            'variants': {v.size: v.url for v in variants}
        })
    
    @action(detail=True, methods=['get'])
    def variant(self, request, pk=None):
        """Belirli boyuttaki varyantı döndürür."""
        file_upload = self.get_object()
        size = request.query_params.get('size', 'medium')
        
        url = ImageService.get_variant_url(file_upload, size)
        return Response({'url': url, 'size': size})


class ChunkUploadViewSet(viewsets.ViewSet):
    """
    Büyük dosya yükleme API (Chunk-based).
    
    Endpoints:
    - POST /api/v1/storage/chunks/start/ - Yükleme başlat
    - POST /api/v1/storage/chunks/{session_id}/upload/ - Chunk yükle
    - POST /api/v1/storage/chunks/{session_id}/complete/ - Yükleme tamamla
    - GET /api/v1/storage/chunks/{session_id}/ - Oturum durumu
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Yükleme oturumu başlatır."""
        serializer = UploadSessionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        
        return Response(
            UploadSessionSerializer(session).data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, pk=None):
        """Oturum durumunu döndürür."""
        session = get_object_or_404(
            UploadSession,
            id=pk,
            uploaded_by=request.user
        )
        return Response(UploadSessionSerializer(session).data)
    
    @action(detail=True, methods=['post'], url_path='upload')
    def upload_chunk(self, request, pk=None):
        """Chunk yükler."""
        session = get_object_or_404(
            UploadSession,
            id=pk,
            uploaded_by=request.user
        )
        
        serializer = ChunkUploadSerializer(
            data=request.data,
            context={'request': request, 'session': session}
        )
        serializer.is_valid(raise_exception=True)
        
        chunk = serializer.validated_data['chunk']
        chunk_number = serializer.validated_data['chunk_number']
        
        session = StorageService.upload_chunk(
            session_id=session.id,
            chunk_number=chunk_number,
            chunk_data=chunk.read(),
        )
        
        return Response(UploadSessionSerializer(session).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Yükleme oturumunu tamamlar."""
        session = get_object_or_404(
            UploadSession,
            id=pk,
            uploaded_by=request.user
        )
        
        file_upload = StorageService.complete_upload_session(session.id)
        
        return Response(
            FileUploadSerializer(file_upload).data,
            status=status.HTTP_201_CREATED
        )


class ProfileAvatarView(generics.CreateAPIView):
    """
    Profil resmi yükleme.
    
    POST /api/v1/storage/avatar/
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProfileAvatarSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_upload = serializer.save()
        
        return Response({
            'message': 'Profil resmi güncellendi',
            'avatar_url': request.user.avatar,
            'file': FileUploadSerializer(file_upload).data,
        }, status=status.HTTP_201_CREATED)


class AssignmentFileView(generics.CreateAPIView):
    """
    Ödev dosyası yükleme.
    
    POST /api/v1/storage/assignments/
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = AssignmentFileSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_upload = serializer.save()
        
        return Response(
            FileUploadSerializer(file_upload).data,
            status=status.HTTP_201_CREATED
        )


class CourseMaterialView(generics.CreateAPIView):
    """
    Kurs materyali yükleme.
    
    POST /api/v1/storage/materials/
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = CourseMaterialSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_upload = serializer.save()
        
        return Response(
            FileUploadSerializer(file_upload).data,
            status=status.HTTP_201_CREATED
        )


class MyFilesView(generics.ListAPIView):
    """
    Kullanıcının yüklediği dosyalar.
    
    GET /api/v1/storage/my-files/
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = FileUploadListSerializer
    
    def get_queryset(self):
        return FileUpload.objects.filter(
            uploaded_by=self.request.user,
            status=FileUpload.Status.COMPLETED,
        ).order_by('-created_at')

