"""
Tenant URLs
===========

Akademi API endpoint'leri.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MyTenantView, TenantViewSet

app_name = 'tenants'

# Router
router = DefaultRouter()
router.register('', TenantViewSet, basename='tenant')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

