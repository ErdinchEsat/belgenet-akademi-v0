"""
Tenant Views
============

Akademi API view'ları.
"""

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.users.permissions import (
    IsAdminOrSuperAdmin,
    IsSuperAdmin,
    IsTenantAdmin,
)

from .models import Tenant, TenantSettings
from .serializers import (
    TenantCreateSerializer,
    TenantMinimalSerializer,
    TenantSerializer,
    TenantSettingsSerializer,
    TenantStatsSerializer,
    TenantUpdateSerializer,
)

User = get_user_model()


class TenantViewSet(viewsets.ModelViewSet):
    """
    Akademi CRUD ViewSet.
    
    GET /api/v1/tenants/           - Liste
    POST /api/v1/tenants/          - Oluştur (Super Admin)
    GET /api/v1/tenants/{id}/      - Detay
    PATCH /api/v1/tenants/{id}/    - Güncelle
    DELETE /api/v1/tenants/{id}/   - Sil (Super Admin)
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        """
        Kullanıcıya göre tenant listesi.
        """
        user = self.request.user
        
        # Anonim kullanıcı kontrolü
        if not user.is_authenticated:
            return Tenant.objects.none()
        
        # Super Admin tüm tenant'ları görür
        if user.role == User.Role.SUPER_ADMIN:
            return Tenant.objects.all()
        
        # Diğerleri sadece kendi tenant'larını görür
        if user.tenant:
            return Tenant.objects.filter(id=user.tenant.id)
        
        # Tenant'sız kullanıcılar aktif tenant'ları görebilir
        return Tenant.objects.filter(is_active=True)

    def get_permissions(self):
        """
        Action bazlı permission.
        """
        if self.action in ['create', 'destroy']:
            return [IsSuperAdmin()]
        if self.action in ['update', 'partial_update']:
            return [IsAdminOrSuperAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """
        Action bazlı serializer.
        """
        if self.action == 'create':
            return TenantCreateSerializer
        if self.action in ['update', 'partial_update']:
            return TenantUpdateSerializer
        if self.action == 'list':
            return TenantMinimalSerializer
        return TenantSerializer

    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """
        Akademi istatistikleri.
        GET /api/v1/tenants/{slug}/stats/
        """
        tenant = self.get_object()
        
        # İstatistikleri hesapla
        users = tenant.users.all()
        stats = {
            'total_users': users.count(),
            'total_students': users.filter(role=User.Role.STUDENT).count(),
            'total_instructors': users.filter(role=User.Role.INSTRUCTOR).count(),
            'total_courses': tenant.stats_courses,
            'total_enrollments': 0,  # Course modeli oluşturulduğunda
            'active_courses': 0,
            'storage_used_mb': tenant.stats_storage_used_mb,
            'storage_limit_gb': tenant.storage_limit_gb,
            'storage_used_percent': tenant.storage_used_percent,
        }
        
        serializer = TenantStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'patch'])
    def settings(self, request, slug=None):
        """
        Akademi ayarları.
        GET/PATCH /api/v1/tenants/{slug}/settings/
        """
        tenant = self.get_object()
        
        # Settings objesi yoksa oluştur
        settings, _ = TenantSettings.objects.get_or_create(tenant=tenant)
        
        if request.method == 'PATCH':
            # Yetki kontrolü
            if request.user.role not in [User.Role.TENANT_ADMIN, User.Role.SUPER_ADMIN]:
                return Response(
                    {'error': 'Bu işlem için yetkiniz yok.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            serializer = TenantSettingsSerializer(
                settings,
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
        serializer = TenantSettingsSerializer(settings)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def users(self, request, slug=None):
        """
        Akademi kullanıcıları.
        GET /api/v1/tenants/{slug}/users/
        """
        tenant = self.get_object()
        
        from backend.users.serializers import UserSerializer
        
        users = tenant.users.all()
        
        # Rol filtresi
        role = request.query_params.get('role')
        if role:
            users = users.filter(role=role)
        
        # Arama
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def activate(self, request, slug=None):
        """
        Akademiyi aktifleştir.
        POST /api/v1/tenants/{slug}/activate/
        """
        tenant = self.get_object()
        tenant.is_active = True
        tenant.save(update_fields=['is_active'])
        
        return Response({'message': 'Akademi aktifleştirildi.'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, slug=None):
        """
        Akademiyi deaktifleştir.
        POST /api/v1/tenants/{slug}/deactivate/
        """
        tenant = self.get_object()
        tenant.is_active = False
        tenant.save(update_fields=['is_active'])
        
        return Response({'message': 'Akademi deaktifleştirildi.'})


class MyTenantView(viewsets.ViewSet):
    """
    Mevcut kullanıcının tenant'ı.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/my-tenant/
        """
        if not request.user.tenant:
            return Response(
                {'error': 'Bir akademiye bağlı değilsiniz.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = TenantSerializer(request.user.tenant)
        return Response(serializer.data)

