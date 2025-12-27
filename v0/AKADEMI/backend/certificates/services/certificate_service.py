"""
Certificate Service
===================

Sertifika oluşturma ve yönetim servisi.
"""

import logging
from datetime import date
from typing import Optional

from django.db import transaction
from django.utils import timezone

from backend.courses.models import Course, Enrollment
from ..models import Certificate, CertificateTemplate

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Sertifika servisi.
    
    Sertifika oluşturma, verme ve doğrulama işlemlerini yönetir.
    """
    
    @classmethod
    def check_eligibility(cls, enrollment: Enrollment) -> tuple[bool, str]:
        """
        Sertifika almaya uygunluğu kontrol eder.
        
        Args:
            enrollment: Kurs kaydı
            
        Returns:
            tuple: (uygun_mu, mesaj)
        """
        course = enrollment.course
        
        # Kurs sertifika destekliyor mu?
        if not course.certificate_enabled:
            return False, "Bu kurs için sertifika verilmiyor"
        
        # Tamamlama yüzdesi yeterli mi?
        if enrollment.progress_percent < course.completion_percent:
            return False, f"Kurs en az %{course.completion_percent} tamamlanmalı"
        
        # Zaten sertifika var mı?
        if hasattr(enrollment, 'certificate') and enrollment.certificate:
            if enrollment.certificate.status != Certificate.Status.REVOKED:
                return False, "Bu kurs için zaten sertifika alınmış"
        
        return True, "Sertifika almaya uygun"
    
    @classmethod
    @transaction.atomic
    def create_certificate(
        cls,
        enrollment: Enrollment,
        auto_issue: bool = True,
        issued_by=None,
    ) -> Certificate:
        """
        Sertifika oluşturur.
        
        Args:
            enrollment: Kurs kaydı
            auto_issue: Otomatik olarak ver
            issued_by: Veren kullanıcı
            
        Returns:
            Certificate: Oluşturulan sertifika
        """
        # Uygunluk kontrolü
        eligible, message = cls.check_eligibility(enrollment)
        if not eligible:
            raise ValueError(message)
        
        course = enrollment.course
        user = enrollment.user
        tenant = course.tenant
        
        # Şablon seç
        template = cls._get_template(tenant, course)
        
        # Toplam süre hesapla (dakikadan saate)
        total_hours = round(course.total_duration_minutes / 60, 1)
        
        # Becerileri al (course tags'den)
        skills = course.tags if course.tags else []
        
        # Final notunu hesapla (quiz ortalaması)
        final_score = cls._calculate_final_score(enrollment)
        
        # Sertifika oluştur
        certificate = Certificate.objects.create(
            tenant=tenant,
            user=user,
            course=course,
            enrollment=enrollment,
            template=template,
            title=f"{course.title} Tamamlama Sertifikası",
            description=f"{user.full_name}, {course.title} kursunu başarıyla tamamlamıştır.",
            completion_date=timezone.now().date(),
            completion_percent=enrollment.progress_percent,
            final_score=final_score,
            skills=skills,
            total_hours=total_hours,
            status=Certificate.Status.PENDING,
        )
        
        logger.info(f"Sertifika oluşturuldu: {certificate.id}")
        
        # PDF oluştur
        cls._generate_pdf(certificate)
        
        # Otomatik ver
        if auto_issue:
            certificate.issue(issued_by)
        
        return certificate
    
    @classmethod
    def verify_certificate(cls, verification_code: str) -> Optional[dict]:
        """
        Sertifikayı doğrular.
        
        Args:
            verification_code: Doğrulama kodu
            
        Returns:
            dict or None: Sertifika bilgileri veya None
        """
        try:
            certificate = Certificate.objects.select_related(
                'user', 'course', 'tenant'
            ).get(verification_code=verification_code.upper())
            
            return {
                'valid': certificate.is_valid,
                'status': certificate.status,
                'verification_code': certificate.verification_code,
                'holder': {
                    'name': certificate.user.full_name,
                    'email': certificate.user.email,
                },
                'course': {
                    'title': certificate.course.title,
                    'category': certificate.course.category,
                },
                'institution': {
                    'name': certificate.tenant.name if certificate.tenant else 'Akademi',
                },
                'completion_date': certificate.completion_date.isoformat(),
                'completion_percent': certificate.completion_percent,
                'final_score': float(certificate.final_score) if certificate.final_score else None,
                'skills': certificate.skills,
                'total_hours': float(certificate.total_hours),
                'issued_at': certificate.issued_at.isoformat() if certificate.issued_at else None,
            }
            
        except Certificate.DoesNotExist:
            return None
    
    @classmethod
    def revoke_certificate(
        cls,
        certificate: Certificate,
        reason: str,
        revoked_by=None,
    ):
        """
        Sertifikayı iptal eder.
        
        Args:
            certificate: Sertifika
            reason: İptal sebebi
            revoked_by: İptal eden kullanıcı
        """
        certificate.revoke(reason)
        
        logger.warning(
            f"Sertifika iptal edildi: {certificate.id} - "
            f"Sebep: {reason} - "
            f"İptal eden: {revoked_by}"
        )
    
    @classmethod
    def regenerate_pdf(cls, certificate: Certificate):
        """PDF'i yeniden oluşturur."""
        cls._generate_pdf(certificate)
    
    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    
    @classmethod
    def _get_template(cls, tenant, course) -> Optional[CertificateTemplate]:
        """Uygun şablonu seçer."""
        # Önce tenant'ın varsayılan şablonunu ara
        template = CertificateTemplate.objects.filter(
            tenant=tenant,
            is_default=True,
            is_active=True,
        ).first()
        
        if not template:
            # Tenant şablonu yoksa, global varsayılanı ara
            template = CertificateTemplate.objects.filter(
                tenant__isnull=True,
                is_default=True,
                is_active=True,
            ).first()
        
        return template
    
    @classmethod
    def _calculate_final_score(cls, enrollment: Enrollment) -> Optional[float]:
        """Final notunu hesaplar (quiz ortalaması)."""
        from backend.progress.models import ContentProgress
        
        # Quiz içeriklerinin skorlarını al
        quiz_scores = ContentProgress.objects.filter(
            enrollment=enrollment,
            content__type='QUIZ',
            is_completed=True,
            score__isnull=False,
        ).values_list('score', flat=True)
        
        if not quiz_scores:
            return None
        
        return sum(quiz_scores) / len(quiz_scores)
    
    @classmethod
    def _generate_pdf(cls, certificate: Certificate):
        """PDF oluşturur."""
        from .pdf_service import PDFService
        
        try:
            pdf_content = PDFService.generate_certificate_pdf(certificate)
            
            # Dosyayı kaydet
            from django.core.files.base import ContentFile
            filename = f"{certificate.verification_code}.pdf"
            certificate.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            
            # Durumu güncelle
            if certificate.status == Certificate.Status.PENDING:
                certificate.status = Certificate.Status.GENERATED
                certificate.save(update_fields=['status'])
            
            logger.info(f"Sertifika PDF oluşturuldu: {certificate.id}")
            
        except Exception as e:
            logger.error(f"PDF oluşturma hatası: {e}")
            raise

