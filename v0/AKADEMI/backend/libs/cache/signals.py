"""
Cache Invalidation Signals
==========================

Model değişikliklerinde cache'i otomatik invalidate eder.

Kullanım:
--------
# apps.py'da import edin
from backend.libs.cache import signals  # noqa: F401
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

logger = logging.getLogger(__name__)


def invalidate_pattern(pattern: str) -> int:
    """
    Pattern ile eşleşen cache key'lerini sil.
    
    Args:
        pattern: Glob-style pattern (örn: "akademi:courses:*")
    
    Returns:
        Silinen key sayısı (tahmini).
    """
    try:
        # django-redis için delete_pattern kullan
        deleted = cache.delete_pattern(pattern)
        logger.debug(f"Cache invalidated: {pattern} ({deleted} keys)")
        return deleted or 0
    except AttributeError:
        # LocMemCache için pattern delete yok
        logger.debug(f"Cache pattern delete not supported for: {pattern}")
        return 0


# =============================================================================
# COURSE SIGNALS
# =============================================================================

try:
    from backend.courses.models import Course, Enrollment
    
    @receiver([post_save, post_delete], sender=Course)
    def invalidate_course_cache(sender, instance, **kwargs):
        """Course değiştiğinde ilgili cache'leri temizle."""
        patterns = [
            f"akademi:courses:*",  # Course listesi
            f"akademi:model:courses:course:{instance.pk}",  # Tek course
        ]
        
        # Tenant bazlı cache
        if hasattr(instance, 'tenant_id') and instance.tenant_id:
            patterns.append(f"akademi:*:t{instance.tenant_id}:*")
        
        for pattern in patterns:
            invalidate_pattern(pattern)
    
    @receiver([post_save, post_delete], sender=Enrollment)
    def invalidate_enrollment_cache(sender, instance, **kwargs):
        """Enrollment değiştiğinde ilgili cache'leri temizle."""
        patterns = [
            f"akademi:enrollments:*",  # Enrollment listesi
            f"akademi:model:courses:enrollment:{instance.pk}",
        ]
        
        # Kullanıcı bazlı cache
        if hasattr(instance, 'user_id') and instance.user_id:
            patterns.append(f"akademi:*:u{instance.user_id}:*")
        
        # Dashboard cache
        patterns.append("akademi:instructor_dashboard:*")
        patterns.append("akademi:student_dashboard:*")
        
        for pattern in patterns:
            invalidate_pattern(pattern)

except ImportError:
    logger.debug("Course models not available for cache signals")


# =============================================================================
# STUDENT SIGNALS
# =============================================================================

try:
    from backend.student.models import ClassGroup, ClassEnrollment, Assignment
    
    @receiver([post_save, post_delete], sender=ClassGroup)
    def invalidate_class_cache(sender, instance, **kwargs):
        """ClassGroup değiştiğinde cache temizle."""
        patterns = [
            "akademi:classes:*",
            "akademi:instructor_classes:*",
            "akademi:student_classes:*",
        ]
        for pattern in patterns:
            invalidate_pattern(pattern)
    
    @receiver([post_save, post_delete], sender=ClassEnrollment)
    def invalidate_class_enrollment_cache(sender, instance, **kwargs):
        """ClassEnrollment değiştiğinde cache temizle."""
        patterns = [
            "akademi:instructor_dashboard:*",
            "akademi:instructor_students:*",
            "akademi:student_classes:*",
        ]
        for pattern in patterns:
            invalidate_pattern(pattern)
    
    @receiver([post_save, post_delete], sender=Assignment)
    def invalidate_assignment_cache(sender, instance, **kwargs):
        """Assignment değiştiğinde cache temizle."""
        patterns = [
            "akademi:assignments:*",
            "akademi:instructor_dashboard:*",
        ]
        for pattern in patterns:
            invalidate_pattern(pattern)

except ImportError:
    logger.debug("Student models not available for cache signals")


# =============================================================================
# USER SIGNALS
# =============================================================================

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    @receiver([post_save], sender=User)
    def invalidate_user_cache(sender, instance, **kwargs):
        """User değiştiğinde cache temizle."""
        patterns = [
            f"akademi:model:users:user:{instance.pk}",
            f"akademi:*:u{instance.pk}:*",
        ]
        for pattern in patterns:
            invalidate_pattern(pattern)

except Exception:
    logger.debug("User model not available for cache signals")
