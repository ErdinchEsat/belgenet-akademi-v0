"""
User Permissions
================

Rol bazlı izin sınıfları.
"""

from rest_framework.permissions import BasePermission

from .models import User


class IsStudent(BasePermission):
    """Öğrenci rolü kontrolü."""
    
    message = 'Bu işlem için öğrenci olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == User.Role.STUDENT
        )


class IsInstructor(BasePermission):
    """Eğitmen rolü kontrolü."""
    
    message = 'Bu işlem için eğitmen olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == User.Role.INSTRUCTOR
        )


class IsTenantAdmin(BasePermission):
    """Kurum yöneticisi rolü kontrolü."""
    
    message = 'Bu işlem için kurum yöneticisi olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == User.Role.TENANT_ADMIN
        )


class IsSuperAdmin(BasePermission):
    """Süper admin rolü kontrolü."""
    
    message = 'Bu işlem için süper admin olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == User.Role.SUPER_ADMIN
        )


class IsAdminOrSuperAdmin(BasePermission):
    """Admin veya Süper Admin rolü kontrolü."""
    
    message = 'Bu işlem için yönetici olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [User.Role.TENANT_ADMIN, User.Role.SUPER_ADMIN]
        )


class IsInstructorOrAdmin(BasePermission):
    """Eğitmen veya yönetici rolü kontrolü."""
    
    message = 'Bu işlem için eğitmen veya yönetici olmanız gerekiyor.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [
                User.Role.INSTRUCTOR,
                User.Role.TENANT_ADMIN,
                User.Role.SUPER_ADMIN,
            ]
        )


class IsSameTenant(BasePermission):
    """Aynı tenant'a ait olma kontrolü."""
    
    message = 'Bu kaynağa erişim yetkiniz yok.'

    def has_object_permission(self, request, view, obj):
        # Super admin her şeye erişebilir
        if request.user.role == User.Role.SUPER_ADMIN:
            return True
        
        # Objenin tenant'ı varsa kontrol et
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.user.tenant
        
        # User objesi ise
        if isinstance(obj, User):
            return obj.tenant == request.user.tenant
        
        return True


class IsOwnerOrAdmin(BasePermission):
    """Kaynak sahibi veya admin kontrolü."""
    
    message = 'Bu kaynağa erişim yetkiniz yok.'

    def has_object_permission(self, request, view, obj):
        # Super admin her şeye erişebilir
        if request.user.role == User.Role.SUPER_ADMIN:
            return True
        
        # Tenant admin kendi tenant'ındaki kaynaklara erişebilir
        if request.user.role == User.Role.TENANT_ADMIN:
            if hasattr(obj, 'tenant'):
                return obj.tenant == request.user.tenant
        
        # Course için instructors kontrolü (ManyToMany)
        if hasattr(obj, 'instructors'):
            return obj.instructors.filter(id=request.user.id).exists()
        
        # Kaynak sahibi
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # User objesi ise
        if isinstance(obj, User):
            return obj == request.user
        
        return False

