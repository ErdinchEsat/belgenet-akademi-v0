"""
Course Views
============

Kurs API view'ları.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.users.permissions import (
    IsAdminOrSuperAdmin,
    IsInstructorOrAdmin,
    IsOwnerOrAdmin,
)

from .models import (
    ContentProgress,
    Course,
    CourseContent,
    CourseModule,
    Enrollment,
)
from .serializers import (
    ContentProgressSerializer,
    ContentProgressUpdateSerializer,
    CourseContentDetailSerializer,
    CourseContentSerializer,
    CourseCreateSerializer,
    CourseListSerializer,
    CourseModuleSerializer,
    CourseSerializer,
    CourseUpdateSerializer,
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
)

User = get_user_model()


class CourseViewSet(viewsets.ModelViewSet):
    """
    Kurs CRUD ViewSet.
    
    GET /api/v1/courses/              - Liste
    POST /api/v1/courses/             - Oluştur (Instructor+)
    GET /api/v1/courses/{slug}/       - Detay
    PATCH /api/v1/courses/{slug}/     - Güncelle
    DELETE /api/v1/courses/{slug}/    - Sil
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        """Kullanıcı ve filtrelere göre kurs listesi."""
        user = self.request.user
        
        # Anonim kullanıcı kontrolü
        if not user.is_authenticated:
            return Course.objects.none()
        
        queryset = Course.objects.all()
        
        # Super Admin tüm kursları görür
        if user.role == User.Role.SUPER_ADMIN:
            pass
        # Tenant Admin kendi tenant'ındaki kursları görür
        elif user.role == User.Role.TENANT_ADMIN:
            queryset = queryset.filter(tenant=user.tenant)
        # Eğitmen kendi kurslarını ve yayındaki kursları görür
        elif user.role == User.Role.INSTRUCTOR:
            queryset = queryset.filter(
                Q(instructors=user) | 
                Q(status=Course.Status.PUBLISHED, tenant=user.tenant)
            ).distinct()
        # Öğrenci sadece yayındaki kursları görür
        else:
            queryset = queryset.filter(
                status=Course.Status.PUBLISHED,
                tenant=user.tenant,
            )
        
        # Filtreler
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.prefetch_related('instructors', 'modules__contents')

    def get_permissions(self):
        """Action bazlı permission."""
        if self.action == 'create':
            return [IsInstructorOrAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Action bazlı serializer."""
        if self.action == 'list':
            return CourseListSerializer
        if self.action == 'create':
            return CourseCreateSerializer
        if self.action in ['update', 'partial_update']:
            return CourseUpdateSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        """Kurs oluştururken tenant ve eğitmen ata."""
        course = serializer.save(tenant=self.request.user.tenant)
        course.instructors.add(self.request.user)

    @action(detail=True, methods=['post'])
    def enroll(self, request, slug=None):
        """
        Kursa kayıt ol.
        POST /api/v1/courses/{slug}/enroll/
        """
        course = self.get_object()
        user = request.user
        
        # Zaten kayıtlı mı?
        if Enrollment.objects.filter(user=user, course=course).exists():
            return Response(
                {'error': 'Bu kursa zaten kayıtlısınız.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Kayıt oluştur
        enrollment = Enrollment.objects.create(
            user=user,
            course=course,
        )
        
        # Kurs istatistiklerini güncelle
        course.enrolled_count += 1
        course.save(update_fields=['enrolled_count'])
        
        return Response(
            EnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, slug=None):
        """
        Kursu onaya gönder.
        POST /api/v1/courses/{slug}/submit_for_review/
        """
        course = self.get_object()
        
        if course.status != Course.Status.DRAFT:
            return Response(
                {'error': 'Sadece taslak kurslar onaya gönderilebilir.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        course.status = Course.Status.PENDING_ADMIN_SETUP
        course.teacher_submit_note = request.data.get('note', '')
        course.save(update_fields=['status', 'teacher_submit_note'])
        
        return Response({'message': 'Kurs onaya gönderildi.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def approve(self, request, slug=None):
        """
        Kursu onayla ve yayınla.
        POST /api/v1/courses/{slug}/approve/
        """
        course = self.get_object()
        
        course.status = Course.Status.PUBLISHED
        course.is_published = True
        course.publish_at = timezone.now()
        course.save(update_fields=['status', 'is_published', 'publish_at'])
        
        return Response({'message': 'Kurs yayınlandı.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperAdmin])
    def request_revision(self, request, slug=None):
        """
        Düzenleme talep et.
        POST /api/v1/courses/{slug}/request_revision/
        """
        course = self.get_object()
        
        course.status = Course.Status.NEEDS_REVISION
        course.admin_revision_note = request.data.get('note', '')
        course.save(update_fields=['status', 'admin_revision_note'])
        
        return Response({'message': 'Düzenleme talebi gönderildi.'})


class CourseModuleViewSet(viewsets.ModelViewSet):
    """Modül CRUD ViewSet."""
    
    serializer_class = CourseModuleSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        course_slug = self.kwargs.get('course_slug')
        return CourseModule.objects.filter(course__slug=course_slug)

    def perform_create(self, serializer):
        course_slug = self.kwargs.get('course_slug')
        course = Course.objects.get(slug=course_slug)
        serializer.save(course=course)


class CourseContentViewSet(viewsets.ModelViewSet):
    """İçerik CRUD ViewSet."""
    
    serializer_class = CourseContentSerializer
    permission_classes = [IsInstructorOrAdmin]

    def get_queryset(self):
        module_id = self.kwargs.get('module_pk')
        return CourseContent.objects.filter(module_id=module_id)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseContentDetailSerializer
        return CourseContentSerializer

    def perform_create(self, serializer):
        module_id = self.kwargs.get('module_pk')
        module = CourseModule.objects.get(id=module_id)
        serializer.save(module=module)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """Kayıt ViewSet."""
    
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Anonim kullanıcı kontrolü
        if not user.is_authenticated:
            return Enrollment.objects.none()
        
        # Super/Tenant Admin tüm kayıtları görebilir
        if user.role in [User.Role.SUPER_ADMIN, User.Role.TENANT_ADMIN]:
            if user.role == User.Role.TENANT_ADMIN:
                return Enrollment.objects.filter(course__tenant=user.tenant)
            return Enrollment.objects.all()
        
        # Eğitmen kendi kurslarındaki kayıtları görebilir
        if user.role == User.Role.INSTRUCTOR:
            return Enrollment.objects.filter(course__instructors=user)
        
        # Öğrenci sadece kendi kayıtlarını görebilir
        return Enrollment.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return EnrollmentCreateSerializer
        return EnrollmentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete_content(self, request, pk=None):
        """
        İçeriği tamamla.
        POST /api/v1/enrollments/{id}/complete_content/
        """
        enrollment = self.get_object()
        content_id = request.data.get('content_id')
        
        if not content_id:
            return Response(
                {'error': 'content_id gerekli.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Progress kaydı oluştur veya güncelle
        progress, created = ContentProgress.objects.get_or_create(
            enrollment=enrollment,
            content_id=content_id,
            defaults={'is_completed': True, 'completed_at': timezone.now()},
        )
        
        if not created and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save(update_fields=['is_completed', 'completed_at'])
        
        # Enrollment progress güncelle
        enrollment.mark_content_complete(content_id)
        
        return Response(EnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        İlerleme detayları.
        GET /api/v1/enrollments/{id}/progress/
        """
        enrollment = self.get_object()
        progress = enrollment.content_progress.all()
        
        return Response(ContentProgressSerializer(progress, many=True).data)

