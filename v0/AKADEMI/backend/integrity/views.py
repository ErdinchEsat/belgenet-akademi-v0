"""
Integrity Views
===============

Integrity API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.player.models import PlaybackSession

from .models import IntegrityCheck, PlaybackAnomaly
from .serializers import (
    IntegrityVerifyRequestSerializer,
    IntegrityCheckResponseSerializer,
    IntegrityStatusResponseSerializer,
    AnomalyReportSerializer,
    AnomalyResponseSerializer,
    UserIntegrityScoreSerializer,
)
from .services import IntegrityService

logger = logging.getLogger(__name__)


class IntegrityVerifyView(APIView):
    """
    Bütünlük Doğrulama API.
    
    Endpoint:
        POST /integrity/verify/  → Playback bütünlüğünü doğrula
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Playback bütünlüğünü doğrula."""
        serializer = IntegrityVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session al
        session = get_object_or_404(
            PlaybackSession.objects.select_related('content'),
            id=data['session_id'],
            user=request.user,
        )
        
        # Doğrulama yap
        check = IntegrityService.verify_playback(
            user=request.user,
            session=session,
            video_position=data['video_position'],
            tab_visibility_ratio=data['tab_visibility_ratio'],
            playback_speed=data['playback_speed'],
            seek_count=data['seek_count'],
            pause_count=data['pause_count'],
            total_pause_duration=data['total_pause_duration'],
            elapsed_seconds=data['elapsed_seconds'],
            device_data=data.get('device_fingerprint'),
        )
        
        response_serializer = IntegrityCheckResponseSerializer(check)
        return Response(response_serializer.data)


class IntegrityStatusView(APIView):
    """
    Bütünlük Durumu API.
    
    Endpoint:
        GET /integrity/status/  → Kullanıcı bütünlük durumu
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Kullanıcı bütünlük durumunu getir."""
        status_data = IntegrityService.get_user_status(request.user)
        return Response(status_data)


class AnomalyReportView(APIView):
    """
    Anomali Raporu API.
    
    Endpoint:
        POST /integrity/report/  → Anomali raporu gönder
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Anomali raporu gönder."""
        serializer = AnomalyReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session al
        session = get_object_or_404(
            PlaybackSession.objects.select_related('content'),
            id=data['session_id'],
            user=request.user,
        )
        
        # Anomali oluştur
        anomaly = PlaybackAnomaly.objects.create(
            tenant=request.user.tenant,
            session=session,
            user=request.user,
            content=session.content,
            anomaly_type=data['anomaly_type'],
            severity=PlaybackAnomaly.AnomalySeverity.LOW,  # Client raporları düşük öncelikli
            description=data['description'],
            details=data.get('details', {}),
            video_ts=data.get('video_ts'),
        )
        
        response_serializer = AnomalyResponseSerializer(anomaly)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class UserIntegrityScoreView(APIView):
    """
    Kullanıcı Bütünlük Skoru API.
    
    Endpoint:
        GET /integrity/score/  → Kullanıcı skoru
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Kullanıcı skorunu getir."""
        user_score = IntegrityService.get_or_create_user_score(request.user)
        serializer = UserIntegrityScoreSerializer(user_score)
        return Response(serializer.data)


class SessionIntegrityHistoryView(APIView):
    """
    Oturum Bütünlük Geçmişi API.
    
    Endpoint:
        GET /integrity/history/?session_id=...
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Oturum bütünlük geçmişini getir."""
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response(
                {'detail': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        checks = IntegrityCheck.objects.filter(
            session_id=session_id,
            user=request.user,
        ).order_by('-created_at')[:20]
        
        serializer = IntegrityCheckResponseSerializer(checks, many=True)
        
        return Response({
            'session_id': session_id,
            'total': len(checks),
            'checks': serializer.data,
        })


class UserAnomaliesView(APIView):
    """
    Kullanıcı Anomalileri API.
    
    Endpoint:
        GET /integrity/anomalies/  → Kullanıcı anomalileri
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Kullanıcı anomalilerini getir."""
        limit = int(request.query_params.get('limit', 20))
        
        anomalies = PlaybackAnomaly.objects.filter(
            user=request.user,
        ).order_by('-created_at')[:limit]
        
        serializer = AnomalyResponseSerializer(anomalies, many=True)
        
        return Response({
            'total': len(anomalies),
            'anomalies': serializer.data,
        })

