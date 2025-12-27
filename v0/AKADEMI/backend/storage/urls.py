"""
Storage URLs
============

Dosya yükleme API endpoint'leri.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FileUploadViewSet,
    ChunkUploadViewSet,
    ProfileAvatarView,
    AssignmentFileView,
    CourseMaterialView,
    MyFilesView,
)

app_name = 'storage'

router = DefaultRouter()
router.register(r'files', FileUploadViewSet, basename='files')
router.register(r'chunks', ChunkUploadViewSet, basename='chunks')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Özel endpoints
    path('avatar/', ProfileAvatarView.as_view(), name='avatar'),
    path('assignments/', AssignmentFileView.as_view(), name='assignments'),
    path('materials/', CourseMaterialView.as_view(), name='materials'),
    path('my-files/', MyFilesView.as_view(), name='my-files'),
]

