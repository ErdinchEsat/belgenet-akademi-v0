"""
Live Session Views
==================

Canlı ders API endpoint'leri.
"""

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO

from django.db.models import Q, Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.courses.models import Enrollment
from .models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionAttendanceSummary,
    LiveSessionRecording,
    LiveSessionArtifact,
    LiveSessionPolicy,
    LiveProviderConfig,
)
from .serializers import (
    LiveSessionListSerializer,
    LiveSessionDetailSerializer,
    LiveSessionCreateSerializer,
    LiveSessionUpdateSerializer,
    JoinResponseSerializer,
    HeartbeatSerializer,
    LiveSessionParticipantSerializer,
    LiveSessionAttendanceSummarySerializer,
    AttendanceReportSerializer,
    LiveSessionRecordingSerializer,
    LiveSessionRecordingPublishSerializer,
    LiveSessionArtifactSerializer,
    LiveProviderConfigSerializer,
    LiveProviderConfigWriteSerializer,
)
from .permissions import (
    IsSessionInstructor,
    CanJoinSession,
    CanViewRecording,
    CanManageSession,
    CanViewAttendance,
    LiveSessionRolePermissions,
)
from .providers import get_provider
from .services.session_service import LiveSessionService
from .services.attendance_service import AttendanceService

logger = logging.getLogger(__name__)


class LiveSessionViewSet(viewsets.ModelViewSet):
    """
    Canlı ders CRUD ve işlem endpoint'leri.
    
    Endpoints:
        GET    /api/v1/live-sessions/           - Liste
        POST   /api/v1/live-sessions/           - Oluştur
        GET    /api/v1/live-sessions/{id}/      - Detay
        PUT    /api/v1/live-sessions/{id}/      - Güncelle
        DELETE /api/v1/live-sessions/{id}/      - Sil
        
        POST   /api/v1/live-sessions/{id}/start/     - Başlat
        POST   /api/v1/live-sessions/{id}/join/      - Katıl
        POST   /api/v1/live-sessions/{id}/end/       - Bitir
        POST   /api/v1/live-sessions/{id}/cancel/    - İptal
        POST   /api/v1/live-sessions/{id}/heartbeat/ - Heartbeat
        
        GET    /api/v1/live-sessions/{id}/attendance/   - Yoklama
        GET    /api/v1/live-sessions/{id}/participants/ - Katılımcılar
        GET    /api/v1/live-sessions/{id}/recordings/   - Kayıtlar
        GET    /api/v1/live-sessions/{id}/artifacts/    - Çıktılar
        GET    /api/v1/live-sessions/{id}/calendar/     - ICS
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Tenant-scoped queryset."""
        user = self.request.user
        queryset = LiveSession.objects.filter(tenant=user.tenant)
        
        # Öğrenci sadece kayıtlı olduğu kursların derslerini görür
        if user.role == 'STUDENT':
            enrolled_courses = Enrollment.objects.filter(
                user=user,
                status=Enrollment.Status.ACTIVE
            ).values_list('course_id', flat=True)
            queryset = queryset.filter(course_id__in=enrolled_courses)
        
        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Course filter
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        # Upcoming filter
        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            queryset = queryset.filter(
                scheduled_start__gte=timezone.now(),
                status__in=[LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]
            )
        
        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(scheduled_start__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_start__date__lte=end_date)
        
        return queryset.select_related('course', 'created_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LiveSessionListSerializer
        elif self.action in ['create']:
            return LiveSessionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LiveSessionUpdateSerializer
        return LiveSessionDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSessionInstructor()]
        elif self.action in ['start', 'end', 'cancel']:
            return [IsAuthenticated(), CanManageSession()]
        elif self.action == 'join':
            return [IsAuthenticated(), CanJoinSession()]
        elif self.action in ['attendance', 'participants']:
            return [IsAuthenticated(), CanViewAttendance()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Session oluştur ve provider'da oda aç."""
        user = self.request.user
        tenant = user.tenant
        
        # Provider config al
        config = LiveProviderConfig.objects.filter(
            tenant=tenant,
            is_active=True,
            is_default=True
        ).first()
        
        if not config:
            raise ValueError("Aktif canlı ders sağlayıcısı bulunamadı")
        
        session = serializer.save(
            tenant=tenant,
            created_by=user,
            provider=config.provider,
            status=LiveSession.Status.SCHEDULED,
        )
        
        # Provider'da oda oluştur
        try:
            provider = get_provider(tenant)
            room_info = provider.create_room(session)
            session.room_url = room_info.room_url
            session.room_password = room_info.password or ''
            session.save(update_fields=['room_url', 'room_password'])
        except Exception as e:
            logger.error(f"Provider room creation failed: {e}")
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Oturumu başlat.
        
        Status: scheduled/draft -> live
        """
        session = self.get_object()
        
        if session.status not in [LiveSession.Status.SCHEDULED, LiveSession.Status.DRAFT]:
            return Response(
                {'error': _('Bu oturum başlatılamaz.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Provider'da başlat
            provider = get_provider(session.tenant)
            provider.start_session(session)
            
            # Status güncelle
            session.start()
            
            # Auto recording
            if session.auto_recording:
                try:
                    recording_id = provider.start_recording(session)
                    logger.info(f"Auto recording started: {recording_id}")
                except Exception as e:
                    logger.error(f"Auto recording failed: {e}")
            
            return Response({'status': 'started', 'actual_start': session.actual_start})
        except Exception as e:
            logger.error(f"Session start failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Oturuma katıl.
        
        Join URL ve token döner.
        """
        session = self.get_object()
        user = request.user
        
        # Status kontrolü
        if session.status != LiveSession.Status.LIVE:
            # Eğitmen beklemede katılabilir
            role = LiveSessionRolePermissions.get_role_for_user(session, user)
            if role not in ['host', 'moderator']:
                return Response(
                    {'error': _('Oturum henüz başlamadı.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Kapasite kontrolü
        if not session.can_join:
            return Response(
                {'error': _('Oturum kapasitesi dolu.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Rol belirle
            role = LiveSessionRolePermissions.get_role_for_user(session, user)
            
            # Join URL oluştur
            provider = get_provider(session.tenant)
            join_info = provider.generate_join_url(session, user, role)
            
            # Participant kaydı oluştur
            participant = LiveSessionParticipant.objects.create(
                session=session,
                user=user,
                role=role,
                joined_at=timezone.now(),
                device_type=request.META.get('HTTP_X_DEVICE_TYPE', 'unknown'),
                browser=request.META.get('HTTP_USER_AGENT', '')[:100],
                ip_hash=AttendanceService.hash_ip(request.META.get('REMOTE_ADDR', '')),
            )
            
            # Katılımcı sayısını güncelle
            session.participant_count = session.participants.count()
            session.peak_participants = max(session.peak_participants, session.participant_count)
            session.save(update_fields=['participant_count', 'peak_participants'])
            
            serializer = JoinResponseSerializer({
                'join_url': join_info.join_url,
                'token': join_info.token,
                'expires_at': join_info.expires_at,
                'role': role,
                'session_id': session.id,
                'room_id': session.room_id,
                'provider': session.provider,
            })
            
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Join failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """
        Oturumu sonlandır.
        
        Status: live -> ended
        """
        session = self.get_object()
        
        if session.status != LiveSession.Status.LIVE:
            return Response(
                {'error': _('Sadece aktif oturumlar sonlandırılabilir.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Provider'da sonlandır
            provider = get_provider(session.tenant)
            provider.end_session(session)
            
            # Status güncelle
            session.end()
            
            # Tüm aktif katılımcıları çıkar
            LiveSessionParticipant.objects.filter(
                session=session,
                is_active=True
            ).update(
                is_active=False,
                left_at=timezone.now()
            )
            
            # Attendance hesaplama task'ı tetikle
            from .tasks import calculate_attendance_task
            calculate_attendance_task.delay(str(session.id))
            
            return Response({
                'status': 'ended',
                'actual_end': session.actual_end,
                'total_duration_minutes': session.total_duration_minutes
            })
        except Exception as e:
            logger.error(f"Session end failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Oturumu iptal et.
        """
        session = self.get_object()
        reason = request.data.get('reason', '')
        
        if session.status == LiveSession.Status.ENDED:
            return Response(
                {'error': _('Bitmiş oturum iptal edilemez.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session.cancel(reason)
            
            # İptal bildirimi gönder
            from .tasks import notify_session_cancelled
            notify_session_cancelled.delay(str(session.id), reason)
            
            return Response({'status': 'cancelled'})
        except Exception as e:
            logger.error(f"Session cancel failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """
        Katılımcı heartbeat.
        
        Aktif katılımın devam ettiğini bildirir.
        """
        session = self.get_object()
        user = request.user
        
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Aktif participant bul
        participant = LiveSessionParticipant.objects.filter(
            session=session,
            user=user,
            is_active=True
        ).order_by('-joined_at').first()
        
        if not participant:
            return Response(
                {'error': _('Aktif katılım bulunamadı.')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Heartbeat güncelle
        participant.last_heartbeat = timezone.now()
        
        # Arka plan süresi
        if serializer.validated_data.get('is_background'):
            # Son heartbeat'ten bu yana geçen süreyi arka plana ekle
            if participant.last_heartbeat:
                delta = (timezone.now() - participant.last_heartbeat).total_seconds()
                participant.background_duration_seconds += int(delta)
        
        participant.save(update_fields=['last_heartbeat', 'background_duration_seconds'])
        
        return Response({'status': 'ok'})
    
    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        """
        Yoklama raporu.
        """
        session = self.get_object()
        
        summaries = LiveSessionAttendanceSummary.objects.filter(
            session=session
        ).select_related('user')
        
        # Export CSV
        if request.query_params.get('format') == 'csv':
            return self._export_attendance_csv(session, summaries)
        
        # Enrolled count
        total_enrolled = Enrollment.objects.filter(
            course=session.course,
            status=Enrollment.Status.ACTIVE
        ).count()
        
        total_attended = summaries.filter(attended=True).count()
        attendance_rate = (total_attended / total_enrolled * 100) if total_enrolled > 0 else 0
        
        serializer = AttendanceReportSerializer({
            'session': session,
            'total_enrolled': total_enrolled,
            'total_attended': total_attended,
            'attendance_rate': round(attendance_rate, 2),
            'summaries': summaries,
        })
        
        return Response(serializer.data)
    
    def _export_attendance_csv(self, session, summaries):
        """Yoklama CSV export."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Ad Soyad', 'E-posta', 'Katıldı', 'Toplam Süre (dk)',
            'Katılım Yüzdesi', 'İlk Katılım', 'Son Ayrılış',
            'Geç Katılım', 'Erken Ayrılış'
        ])
        
        # Data
        for summary in summaries:
            writer.writerow([
                summary.user.full_name,
                summary.user.email,
                'Evet' if summary.attended else 'Hayır',
                summary.total_duration_minutes,
                f'{summary.attendance_percent}%',
                summary.first_join.strftime('%Y-%m-%d %H:%M') if summary.first_join else '',
                summary.last_leave.strftime('%Y-%m-%d %H:%M') if summary.last_leave else '',
                'Evet' if summary.late_join else 'Hayır',
                'Evet' if summary.early_leave else 'Hayır',
            ])
        
        output.seek(0)
        response = HttpResponse(output, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="yoklama-{session.room_id}.csv"'
        return response
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """
        Aktif ve geçmiş katılımcılar.
        """
        session = self.get_object()
        
        active_only = request.query_params.get('active') == 'true'
        
        if active_only:
            participants = session.participants.filter(is_active=True)
        else:
            participants = session.participants.all()
        
        serializer = LiveSessionParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def recordings(self, request, pk=None):
        """
        Oturum kayıtları.
        """
        session = self.get_object()
        user = request.user
        
        recordings = session.recordings.all()
        
        # Öğrenci sadece yayınlanmış kayıtları görür
        role = LiveSessionRolePermissions.get_role_for_user(session, user)
        if role == 'participant':
            recordings = recordings.filter(status='published')
        
        serializer = LiveSessionRecordingSerializer(recordings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def artifacts(self, request, pk=None):
        """
        Oturum çıktıları (whiteboard, chat, vb.).
        """
        session = self.get_object()
        artifacts = session.artifacts.all()
        serializer = LiveSessionArtifactSerializer(artifacts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def calendar(self, request, pk=None):
        """
        ICS takvim dosyası.
        """
        session = self.get_object()
        
        from .services.calendar_service import CalendarService
        ics_content = CalendarService.generate_ics(session)
        
        response = HttpResponse(ics_content, content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="ders-{session.room_id}.ics"'
        return response


class RecordingViewSet(viewsets.ModelViewSet):
    """
    Kayıt yönetimi endpoint'leri.
    """
    
    serializer_class = LiveSessionRecordingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = LiveSessionRecording.objects.filter(
            session__tenant=user.tenant
        ).select_related('session')
        
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Kaydı yayınla.
        """
        recording = self.get_object()
        
        serializer = LiveSessionRecordingPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if recording.status != LiveSessionRecording.Status.READY:
            return Response(
                {'error': _('Sadece hazır kayıtlar yayınlanabilir.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if serializer.validated_data.get('title'):
            recording.title = serializer.validated_data['title']
        
        recording.is_public = serializer.validated_data.get('is_public', False)
        recording.publish()
        
        # Bildirim gönder
        from .tasks import notify_recording_published
        notify_recording_published.delay(str(recording.id))
        
        return Response({'status': 'published'})
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """
        Yayından kaldır.
        """
        recording = self.get_object()
        recording.unpublish()
        return Response({'status': 'unpublished'})


class WebhookView(views.APIView):
    """
    Provider webhook handler.
    
    POST /api/v1/live-sessions/webhooks/jitsi/
    POST /api/v1/live-sessions/webhooks/bbb/
    """
    
    permission_classes = []  # Webhook'lar auth gerektirmez
    
    def post(self, request, provider):
        """Webhook event'i işle."""
        from .services.webhook_service import WebhookService
        
        try:
            result = WebhookService.handle_webhook(provider, request.data, request.headers)
            return Response({'status': 'processed', 'event': result.get('event_type')})
        except ValueError as e:
            logger.warning(f"Webhook validation failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return Response({'error': 'Processing failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LiveProviderConfigView(views.APIView):
    """
    Tenant bazlı provider konfigürasyonu.
    
    GET/PUT /api/v1/tenants/{tenant_id}/live-config/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, tenant_id):
        """Provider config al."""
        user = request.user
        
        # Yetki kontrolü
        if not user.is_superuser and user.role != 'TENANT_ADMIN':
            if str(user.tenant_id) != str(tenant_id):
                return Response(
                    {'error': _('Bu tenant\'a erişim yetkiniz yok.')},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        configs = LiveProviderConfig.objects.filter(tenant_id=tenant_id)
        serializer = LiveProviderConfigSerializer(configs, many=True)
        return Response(serializer.data)
    
    def put(self, request, tenant_id):
        """Provider config güncelle."""
        user = request.user
        
        # Yetki kontrolü
        if not user.is_superuser and user.role != 'TENANT_ADMIN':
            return Response(
                {'error': _('Bu işlem için admin yetkisi gerekli.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LiveProviderConfigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider = serializer.validated_data.get('provider', 'jitsi')
        
        config, created = LiveProviderConfig.objects.update_or_create(
            tenant_id=tenant_id,
            provider=provider,
            defaults=serializer.validated_data
        )
        
        return Response(LiveProviderConfigSerializer(config).data)


class LiveOpsView(views.APIView):
    """
    Admin Live Ops dashboard.
    
    GET /api/v1/admin/live-ops/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Operasyon dashboard verisi."""
        user = request.user
        
        if user.role not in ['SUPER_ADMIN', 'TENANT_ADMIN', 'ADMIN']:
            return Response(
                {'error': _('Admin yetkisi gerekli.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Tenant filtresi
        if user.role == 'SUPER_ADMIN':
            sessions_qs = LiveSession.objects.all()
        else:
            sessions_qs = LiveSession.objects.filter(tenant=user.tenant)
        
        # Aktif oturumlar
        active_sessions = sessions_qs.filter(status=LiveSession.Status.LIVE)
        
        # İstatistikler
        total_active = active_sessions.count()
        total_participants = sum(s.participant_count for s in active_sessions)
        
        # Bugünün oturumları
        today = timezone.now().date()
        today_sessions = sessions_qs.filter(scheduled_start__date=today)
        today_completed = today_sessions.filter(status=LiveSession.Status.ENDED).count()
        today_scheduled = today_sessions.filter(status=LiveSession.Status.SCHEDULED).count()
        
        # Son hatalar (basit versiyon)
        recent_errors = []  # Log'dan alınabilir
        
        return Response({
            'active_sessions': total_active,
            'total_participants': total_participants,
            'today': {
                'total': today_sessions.count(),
                'completed': today_completed,
                'scheduled': today_scheduled,
                'live': active_sessions.filter(scheduled_start__date=today).count(),
            },
            'sessions': LiveSessionListSerializer(active_sessions[:10], many=True).data,
            'recent_errors': recent_errors,
        })

