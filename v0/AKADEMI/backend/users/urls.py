"""
User URLs
=========

Kullanıcı CRUD API endpoint'leri.
Auth endpoint'leri auth_urls.py'de ayrı tutulur.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

app_name = 'users'

# Router
router = DefaultRouter()
router.register('', UserViewSet, basename='user')

# URL patterns - sadece User CRUD
urlpatterns = [
    path('', include(router.urls)),
]

