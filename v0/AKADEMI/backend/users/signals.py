"""
User Signals
============

Kullanıcı modeliyle ilgili signal'ler.

Signals:
--------
- user_registered: Yeni kullanıcı kaydedildiğinde
- user_profile_updated: Kullanıcı profili güncellendiğinde
- user_logged_in: Kullanıcı giriş yaptığında (audit log)
- user_logged_out: Kullanıcı çıkış yaptığında (audit log)
- user_login_failed: Başarısız giriş denemesi (audit log)
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

logger = logging.getLogger(__name__)
User = get_user_model()


def get_client_ip(request):
    """Request'ten client IP adresini al."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Kullanıcı giriş yaptığında audit log kaydı oluştur."""
    try:
        from logs.audit.models import AuditLog
        
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        
        AuditLog.objects.log_action(
            user=user,
            action=AuditLog.ActionType.LOGIN,
            object_repr=f"Kullanıcı girişi: {user.email}",
            ip_address=ip,
            user_agent=user_agent,
            extra_data={
                'email': user.email,
                'user_id': str(user.id),
            }
        )
        logger.info(f"[AUDIT] Login: {user.email} from {ip}")
    except Exception as e:
        logger.error(f"Error logging user login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Kullanıcı çıkış yaptığında audit log kaydı oluştur."""
    try:
        from logs.audit.models import AuditLog
        
        if user is None:
            return
            
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        
        AuditLog.objects.log_action(
            user=user,
            action=AuditLog.ActionType.LOGOUT,
            object_repr=f"Kullanıcı çıkışı: {user.email}",
            ip_address=ip,
            user_agent=user_agent,
            extra_data={
                'email': user.email,
                'user_id': str(user.id),
            }
        )
        logger.info(f"[AUDIT] Logout: {user.email} from {ip}")
    except Exception as e:
        logger.error(f"Error logging user logout: {e}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Başarısız giriş denemesinde audit log kaydı oluştur."""
    try:
        from logs.audit.models import AuditLog
        
        ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        email = credentials.get('email', credentials.get('username', 'unknown'))
        
        AuditLog.objects.log_action(
            user=None,
            action=AuditLog.ActionType.LOGIN_FAILED,
            object_repr=f"Başarısız giriş denemesi: {email}",
            ip_address=ip,
            user_agent=user_agent,
            extra_data={
                'attempted_email': email,
            }
        )
        logger.warning(f"[AUDIT] Login Failed: {email} from {ip}")
    except Exception as e:
        logger.error(f"Error logging failed login: {e}")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Yeni kullanıcı oluşturulduğunda profil oluştur.
    """
    if created:
        # UserProfile modeli varsa profil oluştur
        try:
            from .models import UserProfile
            UserProfile.objects.get_or_create(user=instance)
        except ImportError:
            pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Kullanıcı kaydedildiğinde profili de kaydet.
    """
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except Exception:
        pass

