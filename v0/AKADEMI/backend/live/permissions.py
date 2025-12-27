"""
Live Session Permissions
========================

Canlı ders modülü izin kontrolleri.
"""

from rest_framework import permissions
from django.utils.translation import gettext_lazy as _

from backend.courses.models import Enrollment


class IsSessionInstructor(permissions.BasePermission):
    """
    Oturumu oluşturan veya kurs eğitmeni.
    """
    message = _('Bu işlem için eğitmen yetkisi gereklidir.')
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # SuperAdmin her zaman erişebilir
        if user.is_superuser or user.role == 'SUPER_ADMIN':
            return True
        
        # Tenant Admin kendi tenant'ına erişebilir
        if user.role == 'TENANT_ADMIN' and obj.tenant == user.tenant:
            return True
        
        # Oturumu oluşturan
        if obj.created_by == user:
            return True
        
        # Kurs eğitmeni
        if obj.course.instructors.filter(id=user.id).exists():
            return True
        
        return False


class CanJoinSession(permissions.BasePermission):
    """
    Oturuma katılabilir mi kontrolü.
    
    - Kursa kayıtlı öğrenci
    - Kurs eğitmeni
    - Tenant Admin
    """
    message = _('Bu oturuma katılma yetkiniz yok.')
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # SuperAdmin her zaman erişebilir
        if user.is_superuser or user.role == 'SUPER_ADMIN':
            return True
        
        # Tenant Admin kendi tenant'ına erişebilir
        if user.role == 'TENANT_ADMIN' and obj.tenant == user.tenant:
            return True
        
        # Eğitmen
        if user.role == 'INSTRUCTOR' and obj.course.instructors.filter(id=user.id).exists():
            return True
        
        # Oturumu oluşturan
        if obj.created_by == user:
            return True
        
        # Kursa kayıtlı öğrenci
        if Enrollment.objects.filter(
            user=user,
            course=obj.course,
            status=Enrollment.Status.ACTIVE
        ).exists():
            return True
        
        return False


class CanViewRecording(permissions.BasePermission):
    """
    Kayda erişebilir mi kontrolü.
    
    - Yayınlanmış kayıtlar: Kursa kayıtlı herkes
    - Yayınlanmamış: Sadece eğitmen/admin
    """
    message = _('Bu kayda erişim yetkiniz yok.')
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        session = obj.session
        
        # SuperAdmin/TenantAdmin
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'TENANT_ADMIN']:
            return True
        
        # Eğitmen - tüm kayıtlara erişebilir
        if session.course.instructors.filter(id=user.id).exists():
            return True
        
        # Öğrenci - sadece yayınlanmış kayıtlara
        if obj.status == 'published':
            if Enrollment.objects.filter(
                user=user,
                course=session.course,
                status=Enrollment.Status.ACTIVE
            ).exists():
                return True
        
        return False


class CanManageSession(permissions.BasePermission):
    """
    Oturumu yönetebilir mi (start, end, cancel).
    """
    message = _('Bu işlem için oturum yönetim yetkisi gereklidir.')
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # SuperAdmin
        if user.is_superuser or user.role == 'SUPER_ADMIN':
            return True
        
        # Tenant Admin
        if user.role == 'TENANT_ADMIN' and obj.tenant == user.tenant:
            return True
        
        # Oturumu oluşturan
        if obj.created_by == user:
            return True
        
        # Kurs eğitmeni
        if obj.course.instructors.filter(id=user.id).exists():
            return True
        
        return False


class CanViewAttendance(permissions.BasePermission):
    """
    Yoklama raporunu görüntüleyebilir mi.
    
    - Eğitmenler ve adminler
    - Öğrenci sadece kendi kaydını görebilir
    """
    message = _('Yoklama raporuna erişim yetkiniz yok.')
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # SuperAdmin/TenantAdmin
        if user.is_superuser or user.role in ['SUPER_ADMIN', 'TENANT_ADMIN']:
            return True
        
        # Eğitmen
        if obj.course.instructors.filter(id=user.id).exists():
            return True
        
        return False


class LiveSessionRolePermissions:
    """
    Rol bazlı yetki matrisi.
    
    Bu class, session içindeki işlemler için izin kontrolü yapar.
    """
    
    # Yetki matrisi
    PERMISSIONS = {
        'host': {
            'start_session': True,
            'end_session': True,
            'join_session': True,
            'share_screen': True,
            'mute_others': True,
            'kick_participant': True,
            'start_recording': True,
            'stop_recording': True,
            'use_whiteboard': True,
            'send_chat': True,
            'manage_breakout': True,
            'view_attendance': True,
        },
        'moderator': {
            'start_session': True,
            'end_session': True,
            'join_session': True,
            'share_screen': True,
            'mute_others': True,
            'kick_participant': True,
            'start_recording': True,
            'stop_recording': True,
            'use_whiteboard': True,
            'send_chat': True,
            'manage_breakout': True,
            'view_attendance': True,
        },
        'participant': {
            'start_session': False,
            'end_session': False,
            'join_session': True,
            'share_screen': False,  # Policy'ye bağlı
            'mute_others': False,
            'kick_participant': False,
            'start_recording': False,
            'stop_recording': False,
            'use_whiteboard': False,  # Policy'ye bağlı
            'send_chat': True,
            'manage_breakout': False,
            'view_attendance': False,
        },
    }
    
    @classmethod
    def can(cls, role: str, action: str, policy=None) -> bool:
        """
        Rol için işlem izni kontrolü.
        
        Args:
            role: host, moderator, participant
            action: İşlem adı
            policy: LiveSessionPolicy instance (opsiyonel)
            
        Returns:
            bool: İzin varsa True
        """
        perms = cls.PERMISSIONS.get(role, cls.PERMISSIONS['participant'])
        has_permission = perms.get(action, False)
        
        # Policy override kontrolü
        if policy and role == 'participant':
            if action == 'share_screen':
                has_permission = policy.students_can_share_screen
            elif action == 'use_whiteboard':
                has_permission = policy.students_can_use_whiteboard
        
        return has_permission
    
    @classmethod
    def get_role_for_user(cls, session, user) -> str:
        """
        Kullanıcının session'daki rolünü belirle.
        
        Args:
            session: LiveSession instance
            user: User instance
            
        Returns:
            str: host, moderator, participant
        """
        # Oturumu oluşturan
        if session.created_by == user:
            return 'host'
        
        # Kurs eğitmeni
        if session.course.instructors.filter(id=user.id).exists():
            return 'host'
        
        # Tenant Admin
        if user.role in ['TENANT_ADMIN', 'SUPER_ADMIN']:
            return 'moderator'
        
        # Admin rolü
        if user.role == 'ADMIN':
            return 'moderator'
        
        # Diğer herkes participant
        return 'participant'

