"""
Certificate Signals
===================

Sertifika otomatik oluşturma sinyalleri.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


@receiver(post_save, sender='courses.Enrollment')
def auto_create_certificate(sender, instance, **kwargs):
    """
    Kurs tamamlandığında otomatik sertifika oluşturur.
    
    Bu özellik varsayılan olarak kapalıdır.
    Açmak için settings'te AUTO_CREATE_CERTIFICATES = True ayarlayın.
    """
    if not getattr(settings, 'AUTO_CREATE_CERTIFICATES', False):
        return
    
    # Sadece tamamlanmış kayıtlar için
    if instance.status != 'completed':
        return
    
    # Kurs sertifika desteklemiyor mu?
    if not instance.course.certificate_enabled:
        return
    
    # Tamamlama yüzdesi yeterli mi?
    if instance.progress_percent < instance.course.completion_percent:
        return
    
    # Zaten sertifika var mı?
    if hasattr(instance, 'certificate') and instance.certificate:
        return
    
    # Sertifika oluştur
    try:
        from .services import CertificateService
        CertificateService.create_certificate(
            enrollment=instance,
            auto_issue=True,
        )
        logger.info(f"Otomatik sertifika oluşturuldu: {instance.user.email} - {instance.course.title}")
    except Exception as e:
        logger.error(f"Otomatik sertifika oluşturma hatası: {e}")

