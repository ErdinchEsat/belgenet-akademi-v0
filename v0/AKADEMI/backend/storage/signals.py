"""
Storage Signals
===============

Dosya yükleme sinyalleri.
"""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import FileUpload

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=FileUpload)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    FileUpload silindiğinde dosyayı da siler.
    """
    if instance.file:
        try:
            instance.file.delete(save=False)
            logger.info(f"Dosya silindi: {instance.original_filename}")
        except Exception as e:
            logger.error(f"Dosya silinirken hata: {e}")


@receiver(post_save, sender=FileUpload)
def create_image_variants(sender, instance, created, **kwargs):
    """
    Görsel yüklendiğinde otomatik varyant oluşturur.
    
    Bu özellik varsayılan olarak kapalıdır.
    Açmak için settings'te AUTO_CREATE_IMAGE_VARIANTS = True ayarlayın.
    """
    from django.conf import settings
    
    if not created:
        return
    
    if not getattr(settings, 'AUTO_CREATE_IMAGE_VARIANTS', False):
        return
    
    if not instance.is_image:
        return
    
    if instance.status != FileUpload.Status.COMPLETED:
        return
    
    # Async olarak varyant oluştur (Celery ile)
    try:
        from .tasks import create_image_variants_task
        create_image_variants_task.delay(str(instance.id))
    except ImportError:
        # Celery yüklü değilse senkron olarak oluştur
        from .services import ImageService
        ImageService.create_variants(instance)

