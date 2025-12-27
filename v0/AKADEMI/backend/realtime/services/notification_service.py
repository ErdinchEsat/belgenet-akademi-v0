"""
Notification Service
====================

Bildirim oluşturma ve gönderme servisi.
"""

import logging
from typing import List, Optional

from django.utils import timezone
from django.conf import settings

from backend.student.models import Notification
from ..models import NotificationPreference

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Bildirim servisi.
    
    Bildirim oluşturma, gönderme ve yönetim işlemlerini yönetir.
    """
    
    @classmethod
    def create_notification(
        cls,
        user,
        title: str,
        message: str = '',
        notification_type: str = 'SYSTEM',
        source: str = '',
        action_url: str = '',
        send_realtime: bool = True,
        send_email: bool = False,
        send_push: bool = False,
    ) -> Notification:
        """
        Bildirim oluşturur.
        
        Args:
            user: Bildirim alacak kullanıcı
            title: Bildirim başlığı
            message: Bildirim mesajı
            notification_type: Bildirim türü
            source: Kaynak
            action_url: Tıklandığında gidilecek URL
            send_realtime: WebSocket ile gönder
            send_email: E-posta gönder
            send_push: Push notification gönder
            
        Returns:
            Notification: Oluşturulan bildirim
        """
        # Tercihleri kontrol et
        prefs = cls._get_preferences(user)
        
        if not prefs.should_notify(notification_type):
            logger.debug(f"Kullanıcı {user.id} bu tür bildirimleri kapatmış: {notification_type}")
            return None
        
        # Sessiz saatleri kontrol et
        if cls._is_quiet_hours(prefs):
            send_realtime = False
            send_push = False
        
        # Bildirim oluştur
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=notification_type,
            source=source,
            action_url=action_url,
        )
        
        logger.info(f"Bildirim oluşturuldu: {notification.id} - {title}")
        
        # Gerçek zamanlı gönder
        if send_realtime:
            cls._send_realtime(user.id, notification)
        
        # E-posta gönder
        if send_email and prefs.email_enabled:
            cls._send_email(user, notification)
        
        # Push notification gönder
        if send_push and prefs.push_enabled:
            cls._send_push(user, notification)
        
        return notification
    
    @classmethod
    def create_bulk_notifications(
        cls,
        users: List,
        title: str,
        message: str = '',
        notification_type: str = 'ANNOUNCEMENT',
        source: str = '',
        action_url: str = '',
    ) -> int:
        """
        Toplu bildirim oluşturur.
        
        Args:
            users: Kullanıcı listesi
            title, message, etc.: Bildirim parametreleri
            
        Returns:
            int: Oluşturulan bildirim sayısı
        """
        count = 0
        
        for user in users:
            notification = cls.create_notification(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                source=source,
                action_url=action_url,
                send_email=False,  # Toplu e-posta için ayrı job kullan
            )
            if notification:
                count += 1
        
        logger.info(f"Toplu bildirim gönderildi: {count}/{len(users)} kullanıcı")
        return count
    
    @classmethod
    def notify_class_group(
        cls,
        class_group,
        title: str,
        message: str = '',
        notification_type: str = 'ANNOUNCEMENT',
        exclude_user=None,
    ) -> int:
        """
        Sınıftaki tüm öğrencilere bildirim gönderir.
        """
        from backend.student.models import ClassEnrollment
        
        students = ClassEnrollment.objects.filter(
            class_group=class_group,
            status='ACTIVE',
        ).values_list('user', flat=True)
        
        if exclude_user:
            students = students.exclude(user=exclude_user)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=students)
        
        return cls.create_bulk_notifications(
            users=users,
            title=title,
            message=message,
            notification_type=notification_type,
            source=f"Sınıf: {class_group.name}",
        )
    
    @classmethod
    def notify_course_enrollees(
        cls,
        course,
        title: str,
        message: str = '',
        notification_type: str = 'ANNOUNCEMENT',
    ) -> int:
        """
        Kursa kayıtlı tüm öğrencilere bildirim gönderir.
        """
        from backend.courses.models import Enrollment
        
        enrollees = Enrollment.objects.filter(
            course=course,
            status='active',
        ).values_list('user', flat=True)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=enrollees)
        
        return cls.create_bulk_notifications(
            users=users,
            title=title,
            message=message,
            notification_type=notification_type,
            source=f"Kurs: {course.title}",
        )
    
    # =========================================================================
    # SHORTCUT METHODS
    # =========================================================================
    
    @classmethod
    def notify_assignment(cls, user, assignment, action='created'):
        """Ödev bildirimi."""
        actions = {
            'created': 'Yeni ödev eklendi',
            'updated': 'Ödev güncellendi',
            'deadline': 'Ödev teslim tarihi yaklaşıyor',
        }
        
        return cls.create_notification(
            user=user,
            title=actions.get(action, 'Ödev bildirimi'),
            message=assignment.title,
            notification_type='ASSIGNMENT',
            action_url=f'/student/assignments/{assignment.id}',
        )
    
    @classmethod
    def notify_grade(cls, user, submission):
        """Not bildirimi."""
        return cls.create_notification(
            user=user,
            title='Ödeviniz notlandırıldı',
            message=f'{submission.assignment.title}: {submission.score} puan',
            notification_type='GRADE',
            action_url=f'/student/assignments/{submission.assignment.id}',
        )
    
    @classmethod
    def notify_live_session(cls, user, session, action='reminder'):
        """Canlı ders bildirimi."""
        actions = {
            'created': 'Yeni canlı ders planlandı',
            'reminder': 'Canlı ders 15 dakika içinde başlayacak',
            'started': 'Canlı ders başladı',
            'cancelled': 'Canlı ders iptal edildi',
        }
        
        return cls.create_notification(
            user=user,
            title=actions.get(action, 'Canlı ders bildirimi'),
            message=session.title,
            notification_type='LIVE',
            action_url=f'/student/live-sessions/{session.id}',
            send_push=True,
        )
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    @classmethod
    def _get_preferences(cls, user) -> NotificationPreference:
        """Kullanıcının bildirim tercihlerini döndürür."""
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs
    
    @classmethod
    def _is_quiet_hours(cls, prefs: NotificationPreference) -> bool:
        """Sessiz saatler aktif mi?"""
        if not prefs.quiet_hours_enabled:
            return False
        
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end
        
        if start <= end:
            return start <= now <= end
        else:
            # Gece yarısını geçen aralık (örn: 22:00 - 07:00)
            return now >= start or now <= end
    
    @classmethod
    def _send_realtime(cls, user_id: int, notification: Notification):
        """WebSocket üzerinden bildirim gönderir."""
        try:
            from ..consumers.notification_consumer import send_notification_to_user_sync
            
            send_notification_to_user_sync(
                user_id,
                {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.type,
                    'action_url': notification.action_url,
                    'created_at': notification.created_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Realtime bildirim hatası: {e}")
    
    @classmethod
    def _send_email(cls, user, notification: Notification):
        """E-posta bildirimi gönderir."""
        try:
            from django.core.mail import send_mail
            
            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            logger.debug(f"E-posta gönderildi: {user.email}")
        except Exception as e:
            logger.error(f"E-posta gönderme hatası: {e}")
    
    @classmethod
    def _send_push(cls, user, notification: Notification):
        """Push notification gönderir."""
        # TODO: Firebase Cloud Messaging veya benzeri entegrasyonu
        logger.debug(f"Push notification gönderilecek: {user.id}")
        pass

