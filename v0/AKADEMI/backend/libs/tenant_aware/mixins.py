"""
Tenant Aware View Mixins
========================

ViewSet ve APIView'lar için tenant filtreleme mixin'leri.
"""

from rest_framework.exceptions import PermissionDenied


class TenantFilterMixin:
    """
    ViewSet mixin - otomatik tenant filtreleme.
    
    Kullanım:
        class MyViewSet(TenantFilterMixin, ModelViewSet):
            queryset = MyModel.objects.all()
            
    Queryset otomatik olarak request.user.tenant'a göre filtrelenir.
    """
    
    def get_queryset(self):
        """Queryset'i tenant'a göre filtrele."""
        queryset = super().get_queryset()
        
        # User ve tenant kontrolü
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return queryset.none()
        
        tenant = getattr(user, 'tenant', None)
        if not tenant:
            # Super admin tüm verileri görebilir
            if getattr(user, 'is_superuser', False):
                return queryset
            return queryset.none()
        
        # Tenant filtrelemesi
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=tenant)
        
        return queryset
    
    def perform_create(self, serializer):
        """Oluştururken tenant'ı otomatik set et."""
        user = self.request.user
        tenant = getattr(user, 'tenant', None)
        
        if not tenant:
            if not getattr(user, 'is_superuser', False):
                raise PermissionDenied("Tenant is required")
            # Super admin için tenant serializer'dan gelir
            serializer.save()
        else:
            serializer.save(tenant=tenant)


class TenantContentFilterMixin(TenantFilterMixin):
    """
    Course content için genişletilmiş mixin.
    
    URL'deki course_id ve content_id'yi de kontrol eder.
    """
    
    def get_queryset(self):
        """Course ve content filtrelemesi ekle."""
        queryset = super().get_queryset()
        
        # URL parametrelerinden course_id ve content_id al
        course_id = self.kwargs.get('course_id')
        content_id = self.kwargs.get('content_id')
        
        if course_id and hasattr(queryset.model, 'course_id'):
            queryset = queryset.filter(course_id=course_id)
        
        if content_id and hasattr(queryset.model, 'content_id'):
            queryset = queryset.filter(content_id=content_id)
        
        return queryset

