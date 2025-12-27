"""
Certificate Views
=================

Sertifika API view'ları.
"""

from django.http import FileResponse
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from .models import Certificate, CertificateTemplate, CertificateDownload
from .serializers import (
    CertificateSerializer,
    CertificateListSerializer,
    CertificateVerifySerializer,
    CertificateCreateSerializer,
    CertificateTemplateSerializer,
)
from .services import CertificateService, QRService


class CertificateViewSet(viewsets.ModelViewSet):
    """
    Sertifika API.
    
    Endpoints:
    - GET /api/v1/certificates/ - Sertifika listesi
    - POST /api/v1/certificates/ - Sertifika oluştur
    - GET /api/v1/certificates/{id}/ - Sertifika detayı
    - GET /api/v1/certificates/{id}/download/ - PDF indir
    - GET /api/v1/certificates/{id}/qr/ - QR kod
    - POST /api/v1/certificates/{id}/regenerate/ - PDF yeniden oluştur
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Kullanıcının sertifikalarını döndür."""
        user = self.request.user
        
        # Admin tüm sertifikaları görebilir
        if user.role in ['ADMIN', 'TENANT_ADMIN', 'SUPER_ADMIN']:
            return Certificate.objects.filter(tenant=user.tenant)
        
        # Instructor kendi kurslarının sertifikalarını görebilir
        if user.role == 'INSTRUCTOR':
            return Certificate.objects.filter(
                course__instructors=user
            )
        
        # Öğrenci sadece kendi sertifikalarını görebilir
        return Certificate.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CertificateCreateSerializer
        if self.action == 'list':
            return CertificateListSerializer
        return CertificateSerializer
    
    def perform_destroy(self, instance):
        """Sertifika silme (iptal etme)."""
        CertificateService.revoke_certificate(
            instance,
            reason='Kullanıcı tarafından silindi',
            revoked_by=self.request.user,
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """PDF indirir."""
        certificate = self.get_object()
        
        if not certificate.pdf_file:
            return Response(
                {'error': 'PDF dosyası bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # İndirme kaydı oluştur
        CertificateDownload.objects.create(
            certificate=certificate,
            downloaded_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        
        # PDF döndür
        response = FileResponse(
            certificate.pdf_file.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{certificate.verification_code}.pdf"'
        return response
    
    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        """QR kod görselini döndürür."""
        certificate = self.get_object()
        
        size = int(request.query_params.get('size', 200))
        size = min(max(size, 100), 500)  # 100-500 arası
        
        qr_bytes = QRService.generate_qr_code(certificate.verify_url, size)
        
        from django.http import HttpResponse
        return HttpResponse(qr_bytes, content_type='image/png')
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """PDF'i yeniden oluşturur."""
        certificate = self.get_object()
        
        CertificateService.regenerate_pdf(certificate)
        
        return Response({
            'message': 'PDF yeniden oluşturuldu',
            'pdf_url': certificate.pdf_file.url if certificate.pdf_file else None,
        })


class CertificateVerifyView(generics.RetrieveAPIView):
    """
    Sertifika doğrulama endpoint'i.
    
    Public erişim - herkes doğrulayabilir.
    
    GET /api/v1/certificates/verify/{verification_code}/
    """
    
    permission_classes = [AllowAny]
    serializer_class = CertificateVerifySerializer
    
    def get(self, request, verification_code):
        result = CertificateService.verify_certificate(verification_code)
        
        if result is None:
            return Response(
                {'error': 'Sertifika bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(result)


class MyCertificatesView(generics.ListAPIView):
    """
    Kullanıcının sertifikaları.
    
    GET /api/v1/certificates/my/
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateListSerializer
    
    def get_queryset(self):
        return Certificate.objects.filter(
            user=self.request.user,
            status=Certificate.Status.ISSUED,
        ).order_by('-issued_at')


class CertificateTemplateViewSet(viewsets.ModelViewSet):
    """
    Sertifika şablonu yönetimi (Admin).
    
    Endpoints:
    - GET /api/v1/certificates/templates/ - Şablon listesi
    - POST /api/v1/certificates/templates/ - Şablon oluştur
    - GET /api/v1/certificates/templates/{id}/ - Şablon detayı
    - PUT /api/v1/certificates/templates/{id}/ - Şablon güncelle
    - DELETE /api/v1/certificates/templates/{id}/ - Şablon sil
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateTemplateSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'SUPER_ADMIN':
            return CertificateTemplate.objects.all()
        
        return CertificateTemplate.objects.filter(
            tenant=user.tenant
        )
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class CheckEligibilityView(generics.GenericAPIView):
    """
    Sertifika almaya uygunluk kontrolü.
    
    GET /api/v1/certificates/check/{enrollment_id}/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, enrollment_id):
        from backend.courses.models import Enrollment
        
        try:
            enrollment = Enrollment.objects.get(id=enrollment_id)
        except Enrollment.DoesNotExist:
            return Response(
                {'error': 'Kayıt bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Yetki kontrolü
        if enrollment.user != request.user and request.user.role not in ['ADMIN', 'TENANT_ADMIN', 'SUPER_ADMIN']:
            return Response(
                {'error': 'Bu kayıt için kontrol yapamazsınız'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        eligible, message = CertificateService.check_eligibility(enrollment)
        
        return Response({
            'eligible': eligible,
            'message': message,
            'enrollment_id': enrollment_id,
            'current_progress': enrollment.progress_percent,
            'required_progress': enrollment.course.completion_percent,
        })

