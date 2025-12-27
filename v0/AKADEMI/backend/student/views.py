"""
Student Views
=============

Öğrenci modülü API view'ları.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Assignment,
    AssignmentSubmission,
    ClassEnrollment,
    ClassGroup,
    LiveSession,
    Message,
    Notification,
    SupportTicket,
)
from .serializers import (
    AssignmentDetailSerializer,
    AssignmentListSerializer,
    AssignmentSubmitSerializer,
    ClassGroupDetailSerializer,
    ClassGroupListSerializer,
    LiveSessionListSerializer,
    MessageSerializer,
    NotificationSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
)

User = get_user_model()


class StudentClassViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Öğrenci sınıfları.
    
    GET /api/v1/student/classes/        - Sınıf listesi
    GET /api/v1/student/classes/{id}/   - Sınıf detayı
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ClassGroup.objects.filter(
            class_enrollments__user=user,
            class_enrollments__status='ACTIVE',
        ).prefetch_related('instructors', 'course', 'live_sessions', 'assignments')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClassGroupDetailSerializer
        return ClassGroupListSerializer


class StudentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Öğrenci ödevleri.
    
    GET /api/v1/student/assignments/            - Ödev listesi
    GET /api/v1/student/assignments/{id}/       - Ödev detayı
    POST /api/v1/student/assignments/{id}/submit/  - Ödev teslimi
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Öğrencinin kayıtlı olduğu sınıflardaki ödevler
        enrolled_classes = ClassGroup.objects.filter(
            class_enrollments__user=user,
            class_enrollments__status='ACTIVE',
        )
        return Assignment.objects.filter(
            class_group__in=enrolled_classes,
            status='PUBLISHED',
        ).select_related('class_group')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AssignmentDetailSerializer
        return AssignmentListSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Ödev teslimi."""
        assignment = self.get_object()
        user = request.user
        
        serializer = AssignmentSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Mevcut teslim var mı?
        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=user,
            defaults={
                'content': serializer.validated_data.get('content', ''),
                'attachments': serializer.validated_data.get('attachments', []),
                'status': 'SUBMITTED',
                'submitted_at': timezone.now(),
            }
        )
        
        if not created:
            # Güncelle
            submission.content = serializer.validated_data.get('content', '')
            submission.attachments = serializer.validated_data.get('attachments', [])
            submission.submitted_at = timezone.now()
            
            # Geç teslim kontrolü
            if assignment.due_date < timezone.now():
                submission.status = 'LATE'
            else:
                submission.status = 'SUBMITTED'
            submission.save()
        
        return Response({
            'message': 'Ödev teslim edildi.',
            'submission': {
                'id': submission.id,
                'status': submission.status,
                'submitted_at': submission.submitted_at,
            }
        })


class StudentLiveSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Öğrenci canlı dersleri.
    
    GET /api/v1/student/live-sessions/          - Canlı ders listesi
    GET /api/v1/student/live-sessions/{id}/     - Canlı ders detayı
    POST /api/v1/student/live-sessions/{id}/join/  - Derse katıl
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LiveSessionListSerializer
    
    def get_queryset(self):
        user = self.request.user
        enrolled_classes = ClassGroup.objects.filter(
            class_enrollments__user=user,
            class_enrollments__status='ACTIVE',
        )
        
        queryset = LiveSession.objects.filter(
            class_group__in=enrolled_classes,
        ).select_related('class_group', 'instructor')
        
        # Status filtresi
        status_filter = self.request.query_params.get('status')
        if status_filter:
            if status_filter == 'upcoming':
                queryset = queryset.filter(
                    status__in=['SCHEDULED', 'LIVE'],
                    scheduled_at__gte=timezone.now(),
                )
            elif status_filter == 'live':
                queryset = queryset.filter(status='LIVE')
            elif status_filter == 'completed':
                queryset = queryset.filter(status='COMPLETED')
        
        return queryset.order_by('scheduled_at')
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Canlı derse katıl."""
        session = self.get_object()
        
        if session.status != 'LIVE':
            return Response(
                {'error': 'Bu ders şu an canlı değil.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Katılımcı sayısını artır
        session.participant_count += 1
        session.save(update_fields=['participant_count'])
        
        return Response({
            'message': 'Derse katıldınız.',
            'meeting_url': session.meeting_url,
        })


class StudentNotificationViewSet(viewsets.ModelViewSet):
    """
    Öğrenci bildirimleri.
    
    GET /api/v1/student/notifications/          - Bildirim listesi
    POST /api/v1/student/notifications/{id}/read/  - Okundu işaretle
    POST /api/v1/student/notifications/read-all/   - Tümünü okundu işaretle
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Bildirimi okundu olarak işaretle."""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        
        return Response({'message': 'Bildirim okundu olarak işaretlendi.'})
    
    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        """Tüm bildirimleri okundu olarak işaretle."""
        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'message': 'Tüm bildirimler okundu olarak işaretlendi.'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Okunmamış bildirim sayısı."""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
        
        return Response({'count': count})


class StudentMessageViewSet(viewsets.ModelViewSet):
    """
    Öğrenci mesajları.
    
    GET /api/v1/student/messages/          - Mesaj listesi
    POST /api/v1/student/messages/         - Mesaj gönder
    POST /api/v1/student/messages/{id}/read/  - Okundu işaretle
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        return Message.objects.filter(
            recipient=self.request.user
        ).select_related('sender')
    
    def create(self, request, *args, **kwargs):
        """Mesaj gönder."""
        recipient_id = request.data.get('recipient_id')
        subject = request.data.get('subject', '')
        content = request.data.get('content', '')
        
        if not recipient_id:
            return Response(
                {'error': 'Alıcı gerekli.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Alıcı bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            subject=subject,
            content=content,
        )
        
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mesajı okundu olarak işaretle."""
        message = self.get_object()
        message.is_read = True
        message.read_at = timezone.now()
        message.save(update_fields=['is_read', 'read_at'])
        
        return Response({'message': 'Mesaj okundu olarak işaretlendi.'})


class StudentSupportViewSet(viewsets.ModelViewSet):
    """
    Öğrenci destek talepleri.
    
    GET /api/v1/student/support/           - Talep listesi
    POST /api/v1/student/support/          - Yeni talep
    GET /api/v1/student/support/{id}/      - Talep detayı
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

